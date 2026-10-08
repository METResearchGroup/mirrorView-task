"""Score the locked seed and selected programs once on the test split.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step3_evaluate/main.py --run-id RUN_ID
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version

import pandas as pd

from experiments.dspy_gepa_optimization_2026_09_30.shared.artifacts import parquet_bytes, upload_run_bytes
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    BEDROCK_MODEL_ID,
    DEVELOPMENT_SPLIT,
    PROBABILITY_THRESHOLD,
    S3_BUCKET,
    S3_PREFIX,
    TEST_SPLIT,
    WANDB_PROJECT_PATH,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.evaluation import load_scored_split, metrics_frame, score_examples
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    build_seed_program,
    configure_task_model,
    dspy_demonstrations,
    seed_instruction,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import KeepRemoveProgram
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import (
    apply_lab_aws_credentials,
    initialize_weave,
    trace_attributes,
)
from lib.aws.s3 import S3

TEST_OBJECTS = (
    "test/baseline_predictions.parquet",
    "test/optimized_predictions.parquet",
    "test/metrics.json",
)


def main() -> None:
    """Evaluate both locked programs, or return the existing test artifacts."""
    args = _parse_args()
    apply_lab_aws_credentials()
    selection = _locked_selection(args.run_id)
    if _test_is_complete(args.run_id):
        _print_existing(args.run_id)
        return
    test_rows = load_scored_split(TEST_SPLIT)
    client = initialize_weave()
    configure_task_model()
    seed = build_seed_program()
    selected = KeepRemoveProgram(dspy_demonstrations(), selection["instruction"])
    with trace_attributes({"run_id": args.run_id, "mode": "pilot", "stage": "test", "model_id": BEDROCK_MODEL_ID}):
        baseline = score_examples(seed, test_rows.examples, concurrency=1)
    upload_run_bytes(args.run_id, "test/baseline_predictions.parquet", parquet_bytes(pd.DataFrame(baseline)))
    with trace_attributes({"run_id": args.run_id, "mode": "pilot", "stage": "test", "model_id": BEDROCK_MODEL_ID}):
        optimized = score_examples(selected, test_rows.examples, concurrency=1)
    upload_run_bytes(args.run_id, "test/optimized_predictions.parquet", parquet_bytes(pd.DataFrame(optimized)))
    metrics = {
        "threshold": PROBABILITY_THRESHOLD,
        "positive_class": "remove",
        "baseline": metrics_frame(baseline),
        "optimized": metrics_frame(optimized),
        "test_post_ids": list(test_rows.post_ids),
    }
    upload_run_bytes(args.run_id, "test/metrics.json", json.dumps(metrics, indent=2, sort_keys=True).encode())
    development = _read_json(args.run_id, "selection/development_metrics.json")
    _write_results(args.run_id, selection, development, metrics)
    client.finish()
    _print_metrics(args.run_id, metrics, new_calls=len(baseline) + len(optimized))


def _locked_selection(run_id: str) -> dict[str, object]:
    key = f"{S3_PREFIX}runs/{run_id}/selection/selected_program.json"
    store = _store()
    if not store.object_exists(key):
        raise SystemExit("selection is not locked")
    payload = json.loads(store.get_bytes(key))
    if payload.get("selection_status") != "locked":
        raise SystemExit("selected_program.json is present but selection_status is not locked")
    if not store.object_exists(f"{S3_PREFIX}runs/{run_id}/selection/development_metrics.json"):
        raise SystemExit("development metrics are missing")
    if payload.get("prompt_sha256") != _sha256(str(payload.get("instruction", ""))):
        raise SystemExit("selected prompt hash does not match the stored instruction")
    return payload


def _test_is_complete(run_id: str) -> bool:
    store = _store()
    return all(store.object_exists(f"{S3_PREFIX}runs/{run_id}/{relative}") for relative in TEST_OBJECTS)


def _print_existing(run_id: str) -> None:
    metrics = _read_json(run_id, "test/metrics.json")
    _print_metrics(run_id, metrics, new_calls=0)


def _print_metrics(run_id: str, metrics: dict[str, object], new_calls: int) -> None:
    print("run_id", run_id)
    print("locked_candidate", "true")
    print("baseline_test_rows", int(metrics["baseline"]["rows"]))
    print("optimized_test_rows", int(metrics["optimized"]["rows"]))
    print("threshold", metrics["threshold"])
    print("new_provider_calls", new_calls)
    print("run_uri", f"s3://{S3_BUCKET}/{S3_PREFIX}runs/{run_id}/")
    for arm in ("baseline", "optimized"):
        row = metrics[arm]
        print(arm, "f1", f"{row['f1']:.6f}", "accuracy", f"{row['accuracy']:.6f}", "recall", f"{row['recall']:.6f}", "precision", f"{row['precision']:.6f}")


def _write_results(run_id: str, selection: dict[str, object], development: dict[str, float], test_metrics: dict[str, object]) -> None:
    from pathlib import Path

    baseline = test_metrics["baseline"]
    optimized = test_metrics["optimized"]
    lines = [
        "# DSPy GEPA optimization for Study 2",
        "",
        "## Split audit",
        "",
        "The prepared input has 4,051 unanimous source rows, 10 excluded prompt examples, 4,041 eligible rows, and a 405-row pilot cohort.",
        "Optimization has 222 rows, and GEPA validation, development, and test each have 61 rows.",
        "Remove counts are 17, 5, 5, and 5.",
        "",
        "## Run provenance",
        "",
        f"- Pilot run: `{run_id}`",
        f"- Approved smoke run: `{selection['approved_smoke_run_id']}`",
        f"- Analysis artifacts: `s3://{S3_BUCKET}/{S3_PREFIX}runs/{run_id}/`",
        f"- Weave project: `{WANDB_PROJECT_PATH}`",
        f"- Model: `{BEDROCK_MODEL_ID}`",
        f"- Packages: DSPy {version('dspy')}, GEPA {version('gepa')}, Weave {version('weave')}",
        "",
        "## Selection rule",
        "",
        "The selected prompt has the highest balanced validation accuracy.",
        "An exact tie uses the shorter instruction, then the earlier candidate index.",
        f"Development F1 did not change the selection. Threshold is {PROBABILITY_THRESHOLD}, and remove is the positive class.",
        "",
        "## Development metrics",
        "",
        _metric_table("Selected program", development),
        "",
        "## Human label note",
        "",
        "Development and test each contain five remove rows. Each missed remove changes recall by 20 percentage points.",
        "",
        "## Prompt comparison",
        "",
        "### Original instruction",
        "",
        "```text",
        seed_instruction(),
        "```",
        "",
        "### Optimized instruction",
        "",
        "```text",
        str(selection["instruction"]),
        "```",
        "",
        "## Model metrics",
        "",
        "### Test posts",
        "",
        "| Program | N | F1 | Accuracy | Recall | Precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        _metric_row("Original", baseline),
        _metric_row("Selected", optimized),
        "",
        "## Limitations",
        "",
        "This is a 405-row pilot. The metrics are directional because each test split has five remove rows.",
        "",
    ]
    Path("experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def _metric_table(label: str, metrics: dict[str, float]) -> str:
    return "\n".join(
        [
            "| Program | N | F1 | Accuracy | Recall | Precision |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            _metric_row(label, metrics),
        ]
    )


def _metric_row(label: str, metrics: dict[str, float]) -> str:
    return (
        f"| {label} | {int(metrics['rows'])} | {metrics['f1']:.6f} | {metrics['accuracy']:.6f} | "
        f"{metrics['recall']:.6f} | {metrics['precision']:.6f} |"
    )


def _read_json(run_id: str, relative: str) -> dict:
    return json.loads(_store().get_bytes(f"{S3_PREFIX}runs/{run_id}/{relative}"))


def _store() -> S3:
    return S3(S3_BUCKET, region_name="us-east-2")


def _sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a locked DSPy GEPA run.")
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
