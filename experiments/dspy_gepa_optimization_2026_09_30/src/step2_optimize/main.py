"""Validate the DSPy program locally, or run the paid GEPA smoke.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import dspy

from experiments.dspy_gepa_optimization_2026_09_30.shared import evaluation
from experiments.dspy_gepa_optimization_2026_09_30.shared.artifacts import upload_run_bytes
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    BEDROCK_MODEL_ID,
    DEVELOPMENT_SPLIT,
    INPUT_PRICE_PER_MILLION,
    OUTPUT_PRICE_PER_MILLION,
    PRELIMINARY_HIGH_MINUTES,
    PRELIMINARY_LOW_MINUTES,
    PRELIMINARY_MEDIAN_MINUTES,
    RANDOM_SEED,
    S3_BUCKET,
    S3_PREFIX,
    SMOKE_METRIC_CALLS,
    TASK_CONCURRENCY,
    TEST_SPLIT,
    WANDB_PROJECT_PATH,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.metric import (
    BalancedReflectionSampler,
    COPIED_OPTIMIZATION_TEXT,
    CandidateRecord,
    INSTRUCTION_TOO_LONG,
    MISSING_OUTPUT_CONTRACT,
    classification_metrics,
    gepa_metric,
    rejection_reasons,
    score_example,
    select_candidate,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    build_reflection_model,
    build_seed_program,
    configure_task_model,
    dspy_demonstrations,
    seed_instruction,
)
from lib.aws.s3 import S3
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import (
    apply_lab_aws_credentials,
    initialize_weave,
    trace_attributes,
)

PAID_CALLS = 0


def main() -> None:
    """Run contract checks or the smoke optimizer."""
    args = _parse_args()
    if args.validate_contracts:
        run_contract_checks()
        return
    if args.smoke:
        run_smoke(args)
        return
    if args.approved_smoke_run_id:
        raise SystemExit("pilot execution waits for explicit approval after the smoke report")
    raise SystemExit("pass --validate-contracts or --smoke")


def run_contract_checks() -> None:
    """Exercise output, metric, sampling, rejection, and tie-break contracts."""
    evaluation.CONTRACT_MODE = True
    evaluation.LOADED_SPLITS.clear()
    optimization = evaluation.optimization_batch()
    validation = evaluation.balanced_validation_batch(evaluation.gepa_validation_batch())
    _check_counts(optimization, validation)
    _check_metric()
    _check_sampler(optimization.examples)
    _check_rejections(optimization.post_texts)
    _check_tie_break()
    _check_metrics_math()
    if DEVELOPMENT_SPLIT in evaluation.LOADED_SPLITS or TEST_SPLIT in evaluation.LOADED_SPLITS:
        raise RuntimeError("contract mode loaded a held-out split")
    print("fixed_demonstrations", len(dspy_demonstrations()))
    print("balanced_validation_rows", len(validation.examples))
    print("balanced_validation_ids", ",".join(validation.post_ids))
    print("loaded_splits", ",".join(evaluation.LOADED_SPLITS))
    print("paid_calls", PAID_CALLS)
    print("contract_checks", "passed")


def _check_counts(optimization: evaluation.ExampleBatch, validation: evaluation.ExampleBatch) -> None:
    demonstrations = dspy_demonstrations()
    if len(demonstrations) != 10:
        raise RuntimeError("expected 10 fixed demonstrations")
    if sum(bool(row.is_remove) for row in demonstrations) != 5:
        raise RuntimeError("expected five remove demonstrations")
    if len(validation.examples) != 10:
        raise RuntimeError("expected 10 balanced validation rows")
    if len(optimization.examples) != 222:
        raise RuntimeError("expected 222 optimization rows")


def _check_metric() -> None:
    gold_remove = SimpleNamespace(is_remove=True)
    gold_keep = SimpleNamespace(is_remove=False)
    valid = score_example(gold_remove, SimpleNamespace(is_remove=True, p_remove=0.5))
    boundary = score_example(gold_keep, SimpleNamespace(is_remove=False, p_remove=0.49))
    disagree = score_example(gold_remove, SimpleNamespace(is_remove=False, p_remove=0.5))
    invalid = score_example(gold_remove, SimpleNamespace(is_remove=True, p_remove=1.2))
    if valid.score != 1.0 or not valid.contract_passed:
        raise RuntimeError("valid remove prediction was rejected")
    if boundary.score != 1.0:
        raise RuntimeError("keep prediction below 0.5 was rejected")
    if disagree.score != 0.0 or disagree.contract_passed:
        raise RuntimeError("threshold disagreement received credit")
    if invalid.score != 0.0 or "contract failure" not in invalid.feedback:
        raise RuntimeError("invalid probability received credit")
    metric = gepa_metric(gold_remove, SimpleNamespace(is_remove=True, p_remove=1.0), None, None, None)
    if metric.score != 1.0 or "Gold label: remove" not in metric.feedback:
        raise RuntimeError("GEPA metric feedback is incomplete")


def _check_sampler(examples: list[object]) -> None:
    first = _batch_labels(examples)
    second = _batch_labels(examples)
    if first != second:
        raise RuntimeError("reflection batches are not deterministic")
    for labels in first:
        if labels != ["keep", "remove"]:
            raise RuntimeError(f"reflection batch was {labels}")


def _batch_labels(examples: list[object]) -> list[list[str]]:
    sampler = BalancedReflectionSampler()
    loader = evaluation.IndexedExampleLoader(examples)
    labels = []
    for _ in range(3):
        ids = sampler.next_minibatch_ids(loader, state=None)
        labels.append(["remove" if examples[data_id].is_remove else "keep" for data_id in ids])
    return labels


def _check_rejections(post_texts: list[str]) -> None:
    seed = seed_instruction()
    missing = rejection_reasons(seed.replace("Allow Or Remove?", ""), post_texts)
    oversized = rejection_reasons(seed + (" more" * 400), post_texts)
    copied = rejection_reasons(f"{seed}\n{post_texts[0]}", post_texts)
    if MISSING_OUTPUT_CONTRACT not in missing:
        raise RuntimeError("missing contract was not rejected")
    if INSTRUCTION_TOO_LONG not in oversized:
        raise RuntimeError("oversized instruction was not rejected")
    if COPIED_OPTIMIZATION_TEXT not in copied:
        raise RuntimeError("copied optimization text was not rejected")


def _check_tie_break() -> None:
    selected = select_candidate(
        [
            CandidateRecord(1, 0.5, "short"),
            CandidateRecord(0, 0.5, "short"),
            CandidateRecord(2, 0.6, "much longer instruction"),
        ]
    )
    if selected.index != 2:
        raise RuntimeError("higher accuracy did not win")
    tied = select_candidate(
        [
            CandidateRecord(1, 0.5, "bbbb"),
            CandidateRecord(0, 0.5, "aa"),
        ]
    )
    if tied.index != 0:
        raise RuntimeError("shorter instruction did not win the tie")


def _check_metrics_math() -> None:
    metrics = classification_metrics([True, False], [False, False])
    empty = classification_metrics([], [])
    if metrics["recall"] != 0.0 or metrics["precision"] != 0.0:
        raise RuntimeError("zero-denominator metrics were not zero")
    if empty["f1"] != 0.0 or empty["accuracy"] != 0.0:
        raise RuntimeError("empty metrics were not zero")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize the keep-or-remove instruction.")
    parser.add_argument("--validate-contracts", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--approved-smoke-run-id", default="")
    parser.add_argument("--max-metric-calls", type=int, default=0)
    return parser.parse_args()


def run_smoke(args: argparse.Namespace) -> None:
    """Score the seed program and run the 30-call GEPA smoke."""
    if args.max_metric_calls != SMOKE_METRIC_CALLS:
        raise SystemExit(f"smoke requires --max-metric-calls {SMOKE_METRIC_CALLS}")
    evaluation.CONTRACT_MODE = False
    run_id = args.run_id or "study2-dspy-gepa-2026-10-01-smoke"
    completed = _completed_smoke(run_id)
    if completed is not None:
        _print_completed_smoke(run_id, completed)
        return
    apply_lab_aws_credentials()
    client = initialize_weave()
    task_lm = configure_task_model()
    program = build_seed_program()
    development = evaluation.load_scored_split(DEVELOPMENT_SPLIT)
    with trace_attributes({"run_id": run_id, "mode": "smoke", "stage": "baseline", "model_id": BEDROCK_MODEL_ID}):
        baseline_rows = evaluation.score_examples(program, development.examples)
    optimization = evaluation.optimization_batch()
    validation = evaluation.balanced_validation_batch(evaluation.gepa_validation_batch())
    rejections: list[dict[str, object]] = []
    log_dir = Path("/tmp") / f"dspy-gepa-{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    with trace_attributes({"run_id": run_id, "mode": "smoke", "stage": "optimizer", "model_id": BEDROCK_MODEL_ID}):
        compiled = _compile_gepa(program, optimization, validation, rejections, log_dir)
    client.finish()
    _publish_smoke(run_id, baseline_rows, compiled, rejections, task_lm, log_dir)
    print("smoke_run_id", run_id)
    print("status", "awaiting_user_approval")


def _completed_smoke(run_id: str) -> dict[str, object] | None:
    apply_lab_aws_credentials()
    store = S3(S3_BUCKET, region_name="us-east-2")
    key = f"{S3_PREFIX}runs/{run_id}/config.json"
    if not store.object_exists(key):
        return None
    payload = json.loads(store.get_bytes(key))
    if payload.get("status") != "awaiting_user_approval":
        return None
    return payload


def _print_completed_smoke(run_id: str, payload: dict[str, object]) -> None:
    estimates = payload.get("estimates", {})
    print("smoke_run_id", run_id)
    print("resumed_completed_checkpoint", "true")
    print("duplicate_task_calls", 0)
    print("wandb_project", payload.get("wandb_project", WANDB_PROJECT_PATH))
    print("run_uri", f"s3://{S3_BUCKET}/{S3_PREFIX}runs/{run_id}/")
    print("estimate_low_usd", estimates.get("low_cost_usd"))
    print("estimate_median_usd", estimates.get("median_cost_usd"))
    print("estimate_high_usd", estimates.get("high_cost_usd"))
    print("status", "awaiting_user_approval")


def _compile_gepa(program: object, optimization: evaluation.ExampleBatch, validation: evaluation.ExampleBatch, rejections: list[dict[str, object]], log_dir: Path) -> object:
    proposer = _GuardedProposer(optimization.post_texts, rejections)
    optimizer = dspy.GEPA(
        metric=gepa_metric,
        max_metric_calls=SMOKE_METRIC_CALLS,
        reflection_lm=build_reflection_model(),
        reflection_minibatch_size=None,
        candidate_selection_strategy="current_best",
        use_merge=False,
        track_stats=True,
        use_wandb=False,
        seed=RANDOM_SEED,
        num_threads=TASK_CONCURRENCY,
        log_dir=str(log_dir),
        instruction_proposer=proposer,
        gepa_kwargs={"batch_sampler": BalancedReflectionSampler(), "acceptance_criterion": "strict_improvement"},
    )
    return optimizer.compile(program, trainset=optimization.examples, valset=validation.examples)


class _GuardedProposer:
    """Propose an instruction and reject copies, length, or a broken contract."""

    def __init__(self, post_texts: list[str], rejections: list[dict[str, object]]) -> None:
        self._predict = dspy.Predict("current_instruction, feedback -> improved_instruction")
        self._post_texts = post_texts
        self._rejections = rejections

    def __call__(self, candidate: dict[str, str], reflective_dataset: object, components_to_update: list[str]) -> dict[str, str]:
        updated = {}
        for name in components_to_update:
            current = candidate[name]
            proposed = self._predict(current_instruction=current, feedback=str(reflective_dataset)[:4000]).improved_instruction
            reasons = rejection_reasons(str(proposed), self._post_texts)
            if reasons:
                self._rejections.append({"component": name, "reasons": reasons, "source": "optimizer"})
                continue
            if str(proposed) == current:
                continue
            updated[name] = str(proposed)
        return updated


def _publish_smoke(run_id: str, baseline_rows: list[dict[str, object]], compiled: object, rejections: list[dict[str, object]], task_lm: dspy.LM, log_dir: Path) -> None:
    metrics = evaluation.metrics_frame(baseline_rows)
    usage = _usage_summary(task_lm)
    estimates = _pilot_estimates(usage)
    manifest = {
        "run_id": run_id,
        "mode": "smoke",
        "status": "awaiting_user_approval",
        "model_id": BEDROCK_MODEL_ID,
        "baseline_metrics": metrics,
        "rejection_count": len(rejections),
        "estimates": estimates,
        "wandb_project": WANDB_PROJECT_PATH,
    }
    upload_run_bytes(run_id, "config.json", json.dumps(manifest, indent=2, sort_keys=True).encode())
    upload_run_bytes(run_id, "baseline/metrics.json", json.dumps(metrics, indent=2, sort_keys=True).encode())
    upload_run_bytes(run_id, "baseline/predictions.json", json.dumps(baseline_rows, indent=2, sort_keys=True).encode())
    upload_run_bytes(run_id, "optimization/rejection_log.json", json.dumps(rejections, indent=2).encode())
    upload_run_bytes(run_id, "optimization/usage.json", json.dumps(usage, indent=2, sort_keys=True).encode())
    _upload_log_dir(run_id, log_dir)
    _write_results(run_id, metrics, estimates, rejections, compiled)
    print("baseline_rows", len(baseline_rows))
    print("task_metric_budget", SMOKE_METRIC_CALLS)
    print("rejections", len(rejections))
    print("wandb_project", WANDB_PROJECT_PATH)
    print("run_uri", f"s3://{S3_BUCKET}/{S3_PREFIX}runs/{run_id}/")
    print("estimate_low_usd", estimates["low_cost_usd"])
    print("estimate_median_usd", estimates["median_cost_usd"])
    print("estimate_high_usd", estimates["high_cost_usd"])


def _usage_summary(task_lm: dspy.LM) -> dict[str, float]:
    input_tokens = 0
    output_tokens = 0
    for entry in task_lm.history:
        usage = entry.get("usage") or {}
        input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return {"calls": float(len(task_lm.history)), "input_tokens": float(input_tokens), "output_tokens": float(output_tokens)}


def _pilot_estimates(usage: dict[str, float]) -> dict[str, float]:
    calls = max(usage["calls"], 1.0)
    per_input = usage["input_tokens"] / calls
    per_output = usage["output_tokens"] / calls
    planned_calls = 1244.0

    def cost(multiplier: float) -> float:
        input_cost = planned_calls * per_input * multiplier * INPUT_PRICE_PER_MILLION / 1_000_000
        output_cost = planned_calls * per_output * multiplier * OUTPUT_PRICE_PER_MILLION / 1_000_000
        return round(input_cost + output_cost, 2)

    return {
        "low_cost_usd": cost(0.7),
        "median_cost_usd": cost(1.0),
        "high_cost_usd": cost(1.6),
        "low_minutes": PRELIMINARY_LOW_MINUTES,
        "median_minutes": PRELIMINARY_MEDIAN_MINUTES,
        "high_minutes": PRELIMINARY_HIGH_MINUTES,
        "measured_input_tokens": usage["input_tokens"],
        "measured_output_tokens": usage["output_tokens"],
        "measured_calls": usage["calls"],
    }


def _upload_log_dir(run_id: str, log_dir: Path) -> None:
    for path in log_dir.rglob("*"):
        if path.is_file() and path.stat().st_size < 5_000_000:
            relative = f"optimization/optimizer_state/{path.relative_to(log_dir).as_posix()}"
            upload_run_bytes(run_id, relative, path.read_bytes())


def _write_results(run_id: str, metrics: dict[str, float], estimates: dict[str, float], rejections: list[dict[str, object]], compiled: object) -> None:
    del compiled
    path = Path("experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md")
    path.write_text(
        "\n".join(
            [
                "# DSPy GEPA results",
                "",
                "## Split audit",
                "",
                "The setup manifest records 4,051 source rows, 10 exclusions, 4,041 eligible rows, and a 405-row cohort.",
                "",
                "## Optimizer run",
                "",
                f"Smoke run `{run_id}` is awaiting user approval.",
                f"Baseline development rows: {int(metrics['rows'])}. Contract failures: {int(metrics['contract_failures'])}.",
                f"F1 {metrics['f1']:.6f}, accuracy {metrics['accuracy']:.6f}, recall {metrics['recall']:.6f}, precision {metrics['precision']:.6f}.",
                f"Rejections recorded: {len(rejections)}.",
                "",
                "## Cost estimates",
                "",
                f"Low ${estimates['low_cost_usd']}, median ${estimates['median_cost_usd']}, high ${estimates['high_cost_usd']}.",
                "Preliminary ranges were $6, $9, and $18.",
                "",
                "## Prompt comparison",
                "",
                "Pending selection.",
                "",
                "## Metrics",
                "",
                "Pending the approved pilot and test evaluation.",
                "",
                "## Trace links",
                "",
                f"Weave project: `{WANDB_PROJECT_PATH}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
