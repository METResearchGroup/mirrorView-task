"""Run GEPA on the balanced cohort and score the locked prompts.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step2_optimize/main.py --run-id study2-gepa-balanced-2026-10-02-pilot --max-metric-calls 1000
"""

from __future__ import annotations

import json
from pathlib import Path

import dspy
import pandas as pd

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.artifacts import (
    parquet_bytes,
    read_run_json,
    run_object_exists,
    upload_run_bytes,
)
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.config import (
    COST_LIMIT_USD,
    DEVELOPMENT_SPLIT,
    PILOT_METRIC_CALLS,
    S3_BUCKET,
    S3_PREFIX,
    TEST_SPLIT,
)
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.examples import (
    ExampleBatch,
    balanced_validation_examples,
    load_examples,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    BEDROCK_MODEL_ID,
    INPUT_PRICE_PER_MILLION,
    INSTRUCTION_LENGTH_LIMIT_RATIO,
    OUTPUT_PRICE_PER_MILLION,
    RANDOM_SEED,
    TASK_CONCURRENCY,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.evaluation import metrics_frame, score_examples
from experiments.dspy_gepa_optimization_2026_09_30.shared.metric import (
    BalancedReflectionSampler,
    CandidateRecord,
    gepa_metric,
    rejection_reasons,
    select_candidate,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    KeepRemoveProgram,
    build_reflection_model,
    build_seed_program,
    configure_task_model,
    dspy_demonstrations,
    seed_instruction,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import apply_lab_aws_credentials

SELECTION_KEY = "selection/selected_program.json"
DEVELOPMENT_KEY = "evaluation/development_metrics.json"
TEST_KEY = "evaluation/test_metrics.json"


class _Pause:
    """Stop when spend passes the cap or one rejection reason repeats."""

    def __init__(self, cost_limit_usd: float) -> None:
        self.cost_limit_usd = cost_limit_usd
        self.paused = False
        self.reason = ""
        self._last_reason = ""
        self._same_reason_count = 0

    def record_rejection(self, reason: str) -> None:
        if reason == self._last_reason:
            self._same_reason_count += 1
        else:
            self._last_reason = reason
            self._same_reason_count = 1
        if self._same_reason_count >= 5:
            self.paused = True
            self.reason = f"five consecutive rejections for {reason}"

    def record_success(self) -> None:
        self._same_reason_count = 0
        self._last_reason = ""

    def __call__(self, gepa_state: object) -> bool:
        del gepa_state
        if self.paused:
            return True
        if _history_cost_usd() > self.cost_limit_usd:
            self.paused = True
            self.reason = f"projected cost exceeded ${self.cost_limit_usd:.2f}"
            return True
        return False


class _GuardedProposer:
    """Propose an instruction that stays inside the existing proposal guards."""

    def __init__(self, post_texts: list[str], rejections: list[dict[str, object]], pause: _Pause) -> None:
        self._predict = dspy.Predict("current_instruction, feedback -> improved_instruction")
        self._post_texts = post_texts
        self._rejections = rejections
        self._pause = pause

    def __call__(self, candidate: dict[str, str], reflective_dataset: object, components_to_update: list[str]) -> dict[str, str]:
        updated = {}
        length_limit = int(len(seed_instruction()) * INSTRUCTION_LENGTH_LIMIT_RATIO)
        feedback = (
            f"The improved instruction must be at most {length_limit} characters, "
            "must keep the line 'Allow Or Remove?', and must not quote post text.\n\n"
            + str(reflective_dataset)[:3000]
        )
        for name in components_to_update:
            current = candidate[name]
            proposed = str(self._predict(current_instruction=current, feedback=feedback).improved_instruction)
            reasons = rejection_reasons(proposed, self._post_texts)
            if reasons or proposed == current:
                if reasons:
                    self._rejections.append({"component": name, "reasons": reasons})
                    self._pause.record_rejection(reasons[0])
                continue
            self._pause.record_success()
            updated[name] = proposed
        return updated


def run_pilot(run_id: str, max_metric_calls: int) -> None:
    """Optimize the instruction and lock one candidate."""
    if max_metric_calls != PILOT_METRIC_CALLS:
        raise SystemExit(f"pilot requires --max-metric-calls {PILOT_METRIC_CALLS}")
    apply_lab_aws_credentials()
    if run_object_exists(run_id, SELECTION_KEY) and run_object_exists(run_id, DEVELOPMENT_KEY):
        _print_locked(run_id)
        return
    if run_object_exists(run_id, SELECTION_KEY):
        selection = read_run_json(run_id, SELECTION_KEY)
        _score_split(run_id, DEVELOPMENT_SPLIT, str(selection["instruction"]), include_original=True)
        _print_locked(run_id)
        return
    optimization = load_examples("optimization")
    validation = balanced_validation_examples(load_examples("gepa_validation"))
    if len(validation.examples) != 10:
        raise SystemExit("selection set must contain 10 rows")
    log_dir = Path("/tmp") / f"dspy-gepa-balanced-{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    configure_task_model()
    rejections: list[dict[str, object]] = []
    pause = _Pause(COST_LIMIT_USD)
    compiled = _compile(build_seed_program(), optimization, validation, rejections, log_dir, max_metric_calls, pause)
    if pause.paused:
        print("status", "paused")
        print("pause_reason", pause.reason)
        print("test_rows_loaded", 0)
        return
    selected = _lock(run_id, compiled, optimization.post_texts, rejections)
    _score_split(run_id, DEVELOPMENT_SPLIT, selected["instruction"], include_original=True)
    print("run_id", run_id)
    print("selected_index", selected["index"])
    print("balanced_validation_accuracy", selected["accuracy"])
    print("status", "selection_locked")
    print("test_rows_loaded", 0)
    print("provider_cost_usd", f"{_history_cost_usd():.2f}")


def run_test(run_id: str) -> None:
    """Score the original and selected instructions once on the test split."""
    apply_lab_aws_credentials()
    if not run_object_exists(run_id, SELECTION_KEY):
        raise SystemExit("selection is not locked")
    if run_object_exists(run_id, TEST_KEY):
        _print_test(run_id, new_calls=0)
        return
    selection = read_run_json(run_id, SELECTION_KEY)
    if selection.get("selection_status") != "locked":
        raise SystemExit("selection_status is not locked")
    _score_split(run_id, TEST_SPLIT, str(selection["instruction"]), include_original=True)
    _write_results(run_id)
    _print_test(run_id, new_calls=122)


def _compile(
    program: dspy.Module,
    optimization: ExampleBatch,
    validation: ExampleBatch,
    rejections: list[dict[str, object]],
    log_dir: Path,
    max_metric_calls: int,
    pause: _Pause,
) -> dspy.Module:
    optimizer = dspy.GEPA(
        metric=gepa_metric,
        max_metric_calls=max_metric_calls,
        reflection_lm=build_reflection_model(),
        reflection_minibatch_size=None,
        candidate_selection_strategy="current_best",
        use_merge=False,
        track_stats=True,
        use_wandb=False,
        seed=RANDOM_SEED,
        num_threads=TASK_CONCURRENCY,
        log_dir=str(log_dir),
        instruction_proposer=_GuardedProposer(optimization.post_texts, rejections, pause),
        gepa_kwargs={
            "batch_sampler": BalancedReflectionSampler(),
            "acceptance_criterion": "strict_improvement",
            "stop_callbacks": [pause],
        },
    )
    return optimizer.compile(program, trainset=optimization.examples, valset=validation.examples)


def _lock(run_id: str, compiled: dspy.Module, post_texts: list[str], rejections: list[dict[str, object]]) -> dict[str, object]:
    details = compiled.detailed_results
    records = [
        CandidateRecord(index, float(score), str(module.classify.signature.instructions))
        for index, (module, score) in enumerate(zip(details.candidates, details.val_aggregate_scores, strict=True))
    ]
    chosen = select_candidate(records)
    reasons = rejection_reasons(chosen.instruction, post_texts)
    if reasons:
        raise SystemExit(f"selected instruction failed proposal checks: {reasons}")
    payload = {
        "selection_status": "locked",
        "run_id": run_id,
        "candidate_index": chosen.index,
        "balanced_validation_accuracy": chosen.accuracy,
        "prompt_sha256": _sha256_text(chosen.instruction),
        "instruction": chosen.instruction,
        "model_id": BEDROCK_MODEL_ID,
    }
    lines = [
        json.dumps({"index": record.index, "accuracy": record.accuracy, "instruction_length": len(record.instruction)})
        for record in records
    ]
    upload_run_bytes(run_id, "selection/candidate_metrics.jsonl", ("\n".join(lines) + "\n").encode())
    upload_run_bytes(run_id, SELECTION_KEY, json.dumps(payload, indent=2, sort_keys=True).encode())
    upload_run_bytes(run_id, "selection/optimized_prompt.txt", chosen.instruction.encode())
    upload_run_bytes(run_id, "optimization/rejection_log.json", json.dumps(rejections, indent=2).encode())
    return {"index": chosen.index, "accuracy": chosen.accuracy, "instruction": chosen.instruction}


def _score_split(run_id: str, split_name: str, instruction: str, include_original: bool) -> None:
    batch = load_examples(split_name)
    configure_task_model()
    programs = {}
    if include_original:
        programs["original"] = build_seed_program()
    programs["selected"] = KeepRemoveProgram(dspy_demonstrations(), instruction)
    metrics = {"threshold": 0.5, "positive_class": "remove"}
    for name, program in programs.items():
        rows = score_examples(program, batch.examples, concurrency=1)
        upload_run_bytes(run_id, f"evaluation/{split_name}_{name}_predictions.parquet", parquet_bytes(pd.DataFrame(rows)))
        metrics[name] = metrics_frame(rows)
    upload_run_bytes(run_id, f"evaluation/{split_name}_metrics.json", json.dumps(metrics, indent=2, sort_keys=True).encode())


def _write_results(run_id: str) -> None:
    development = read_run_json(run_id, DEVELOPMENT_KEY)
    test_metrics = read_run_json(run_id, TEST_KEY)
    selection = read_run_json(run_id, SELECTION_KEY)
    lines = [
        "# Balanced keep and remove GEPA ablation",
        "",
        "This ablation uses a new 405-post cohort with 203 keep posts and 202 remove posts.",
        "The finished natural-prevalence run is unchanged.",
        "",
        "## Cohort",
        "",
        "| Split | Posts | Keep | Remove |",
        "| --- | ---: | ---: | ---: |",
        "| Optimization | 222 | 111 | 111 |",
        "| GEPA validation | 61 | 31 | 30 |",
        "| Development | 61 | 30 | 31 |",
        "| Test | 61 | 31 | 30 |",
        "",
        "## Run",
        "",
        f"- Run ID: `{run_id}`",
        f"- Artifacts: `s3://{S3_BUCKET}/{S3_PREFIX}runs/{run_id}/`",
        f"- Model: `{BEDROCK_MODEL_ID}`",
        f"- Selected candidate: {selection['candidate_index']}",
        f"- Balanced validation accuracy: {selection['balanced_validation_accuracy']}",
        f"- Comparison run: `study2-dspy-gepa-2026-10-01-pilot`",
        "",
        "## Development",
        "",
        _table(development),
        "",
        "## Test",
        "",
        _table(test_metrics),
        "",
        "## Optimized instruction",
        "",
        "```text",
        str(selection["instruction"]),
        "```",
        "",
        "One missed remove changes development recall by about 3.2 percentage points and test recall by about 3.3 percentage points.",
        "",
    ]
    Path("experiments/dspy_gepa_balanced_labels_2026_10_02/RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def _table(metrics: dict[str, object]) -> str:
    rows = [
        "| Program | N | F1 | Accuracy | Recall | Precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("original", "selected"):
        row = metrics[name]
        rows.append(
            f"| {name.title()} | {int(row['rows'])} | {row['f1']:.6f} | {row['accuracy']:.6f} | "
            f"{row['recall']:.6f} | {row['precision']:.6f} |"
        )
    return "\n".join(rows)


def _print_locked(run_id: str) -> None:
    payload = read_run_json(run_id, SELECTION_KEY)
    print("run_id", run_id)
    print("selected_index", payload["candidate_index"])
    print("balanced_validation_accuracy", payload["balanced_validation_accuracy"])
    print("duplicate_task_calls", 0)
    print("status", "selection_locked")
    print("test_rows_loaded", 0)


def _print_test(run_id: str, new_calls: int) -> None:
    metrics = read_run_json(run_id, TEST_KEY)
    print("run_id", run_id)
    print("new_provider_calls", new_calls)
    for name in ("original", "selected"):
        row = metrics[name]
        print(name, "f1", f"{row['f1']:.6f}", "accuracy", f"{row['accuracy']:.6f}", "recall", f"{row['recall']:.6f}", "precision", f"{row['precision']:.6f}")


def _history_cost_usd() -> float:
    from dspy.clients.base_lm import GLOBAL_HISTORY

    input_tokens = 0
    output_tokens = 0
    for entry in GLOBAL_HISTORY:
        usage = entry.get("usage") or {}
        input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return (input_tokens * INPUT_PRICE_PER_MILLION + output_tokens * OUTPUT_PRICE_PER_MILLION) / 1_000_000


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()
