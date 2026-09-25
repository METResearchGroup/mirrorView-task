"""GEPA evaluate runner for test reads and transfer evals.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py --ablation-id B1_gepa_pair --split test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import ViewName
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize import (
    ABLATION_REGISTRY,
    OUTPUT_ROOT,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer, secrets
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import (
    CostSummary,
    SplitName,
    build_results_payload,
    latency_summary,
    probability_metrics,
    spearman_remove_share,
    subgroup_metrics,
    trivial_baselines,
    tune_threshold_for_f1,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import render_state_text
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_PARQUET
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run, log_artifact

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
JEV_GEPA_ROOT = EXPERIMENT_ROOT / "jev_gepa"
DEFAULT_THRESHOLD = 0.5
DEV_SELECTION_FILENAME = "dev_selection.json"
CANDIDATES_RELATIVE_PATH = Path("gepa_run") / "candidates.json"
FINAL_PROMPT_FILENAME = "final_prompt.txt"
TRANSFER_OUTPUT_ROOT = OUTPUT_ROOT / "transfers"

TRANSFER_REGISTRY: dict[str, dict[str, str]] = {
    "transfer_B1_on_original": {
        "prompt_source": "B1_gepa_pair",
        "view": "original",
    },
    "transfer_B1_on_mirror": {
        "prompt_source": "B1_gepa_pair",
        "view": "mirror",
    },
    "transfer_B2_on_mirror": {
        "prompt_source": "B2_gepa_original",
        "view": "mirror",
    },
    "transfer_B3_on_original": {
        "prompt_source": "B3_gepa_mirror",
        "view": "original",
    },
}

B1_ABLATION_ID = "B1_gepa_pair"
B1T_ABLATION_ID = "B1T_gepa_pair_terra"


@dataclass(frozen=True)
class EvalConfig:
    """Resolved GEPA evaluation run for a primary ablation or transfer."""

    ablation_id: str | None
    transfer_id: str | None
    instruction: str
    view: ViewName
    split: Literal["dev", "test"]
    output_dir: Path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ablation_output_dir(ablation_id: str) -> Path:
    return OUTPUT_ROOT / ablation_id


def load_selected_instruction(ablation_id: str) -> str:
    """Read instruction text from dev_selection.json + candidates list for that ablation."""
    ablation_dir = _ablation_output_dir(ablation_id)
    dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
    candidates_path = ablation_dir / CANDIDATES_RELATIVE_PATH
    if not dev_selection_path.is_file():
        raise FileNotFoundError(f"missing dev selection at {dev_selection_path}")
    if not candidates_path.is_file():
        raise FileNotFoundError(f"missing candidates at {candidates_path}")
    dev_selection = _load_json(dev_selection_path)
    candidates = _load_json(candidates_path)
    selected_idx = int(dev_selection["selected_candidate_idx"])
    return str(candidates[selected_idx]["instruction"])


def write_final_prompt(ablation_id: str) -> Path:
    """Write final_prompt.txt from the dev-selected candidate instruction."""
    instruction = load_selected_instruction(ablation_id)
    output_path = _ablation_output_dir(ablation_id) / FINAL_PROMPT_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(instruction + "\n", encoding="utf-8")
    return output_path


def _load_cohort(cohort_path: Path) -> pd.DataFrame:
    if not cohort_path.is_file():
        raise FileNotFoundError(f"cohort parquet missing at {cohort_path}")
    return pd.read_parquet(cohort_path)


def _load_predictions_frame(predictions_path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not predictions_path.is_file():
        return pd.DataFrame(columns=["post_id", "probability_remove"])
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    if not rows:
        return pd.DataFrame(columns=["post_id", "probability_remove"])
    return pd.DataFrame(rows)


def _load_requests_frame(requests_path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not requests_path.is_file():
        return pd.DataFrame()
    with requests_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _materialize_labels_frame(labels: pd.DataFrame) -> pd.DataFrame:
    return labels[
        [
            "post_id",
            "split",
            "keep_remove_label",
            "p_remove",
            "predicted_label",
            "sampled_stance",
            "sample_toxicity_type",
            "remove_share",
            "is_unanimous",
            "n_raters",
        ]
    ].copy()


def build_split_tasks(
    cohort: pd.DataFrame,
    *,
    split: Literal["dev", "test"],
    view: ViewName,
) -> list[jev_scorer.PostTask]:
    """Build PostTask list for one split."""
    subset = cohort.loc[cohort["split"].eq(split)]
    tasks: list[jev_scorer.PostTask] = []
    for row in subset.itertuples():
        tasks.append(
            jev_scorer.PostTask(
                post_id=str(row.post_id),
                state_text=render_state_text(
                    view,
                    str(row.original_text),
                    str(row.mirror_text),
                    str(row.post_1_role),
                    add_criteria=False,
                ),
                gold_label=int(row.label),
            )
        )
    return tasks


def _compute_split_metrics(labels: pd.DataFrame) -> dict[SplitName, Any]:
    split_names: list[SplitName] = ["test", "dev", "gepa_pool", "full"]
    metrics: dict[SplitName, Any] = {}
    for split_name in split_names:
        if split_name == "full":
            subset = labels
        else:
            subset = labels.loc[labels["split"] == split_name]
        if subset.empty:
            continue
        metrics[split_name] = probability_metrics(
            subset["keep_remove_label"].astype(int).tolist(),
            subset["p_remove"].astype(float).tolist(),
            threshold=DEFAULT_THRESHOLD,
        )
    return metrics


def _assert_prediction_coverage(predictions: pd.DataFrame, cohort: pd.DataFrame) -> None:
    n_predictions = len(predictions)
    n_cohort = len(cohort)
    if n_predictions != n_cohort:
        missing = n_cohort - n_predictions
        raise RuntimeError(
            f"prediction coverage incomplete: {n_predictions}/{n_cohort} rows scored; "
            f"{missing} missing"
        )


def finalize_eval_output(
    output_dir: Path,
    cohort: pd.DataFrame,
    *,
    ablation_id: str,
    headline_split: Literal["dev", "test"],
) -> dict[str, Any]:
    """Join predictions and write labels, requests, and results.json."""
    predictions_path = output_dir / jev_scorer.PREDICTIONS_FILENAME
    requests_jsonl_path = output_dir / jev_scorer.REQUESTS_FILENAME
    predictions = _load_predictions_frame(predictions_path)
    if predictions.empty:
        raise ValueError(f"no predictions found at {predictions_path}")

    _assert_prediction_coverage(predictions, cohort)

    labels = cohort.merge(
        predictions[["post_id", "probability_remove"]],
        on="post_id",
        how="inner",
        validate="one_to_one",
    )
    labels = labels.rename(columns={"label": "keep_remove_label", "probability_remove": "p_remove"})
    labels["predicted_label"] = (labels["p_remove"] >= DEFAULT_THRESHOLD).astype(int)

    labels_path = output_dir / "labels.parquet"
    _materialize_labels_frame(labels).to_parquet(labels_path, index=False)

    requests = _load_requests_frame(requests_jsonl_path)
    requests_path = output_dir / "requests.parquet"
    requests.to_parquet(requests_path, index=False)

    split_metrics = _compute_split_metrics(labels)
    dev_subset = labels.loc[labels["split"] == "dev"]
    test_subset = labels.loc[labels["split"] == "test"]
    if dev_subset.empty:
        dev_threshold = DEFAULT_THRESHOLD
        dev_tuned_test_metrics = None
    else:
        dev_threshold, _dev_f1 = tune_threshold_for_f1(
            dev_subset["keep_remove_label"].astype(int).tolist(),
            dev_subset["p_remove"].astype(float).tolist(),
        )
        if test_subset.empty:
            dev_tuned_test_metrics = None
        else:
            dev_tuned_test_metrics = probability_metrics(
                test_subset["keep_remove_label"].astype(int).tolist(),
                test_subset["p_remove"].astype(float).tolist(),
                threshold=dev_threshold,
            )
    headline_subset = labels.loc[labels["split"] == headline_split]
    trivial = trivial_baselines(headline_subset["keep_remove_label"].astype(int).tolist())
    subgroups = subgroup_metrics(headline_subset, threshold=DEFAULT_THRESHOLD)
    spearman = spearman_remove_share(
        labels["remove_share"].astype(float).tolist(),
        labels["p_remove"].astype(float).tolist(),
    )

    ok_requests = requests.loc[requests["status"] == "ok"] if not requests.empty else requests
    request_latencies = (
        ok_requests["latency_ms"].astype(float).tolist() if not ok_requests.empty else []
    )
    post_latencies = (
        ok_requests["latency_per_post_ms"].astype(float).tolist()
        if not ok_requests.empty
        else []
    )
    latency = latency_summary(request_latencies, post_latencies)
    cost = CostSummary(
        input_tokens=int(ok_requests["input_tokens"].sum()) if not ok_requests.empty else 0,
        output_tokens=int(ok_requests["output_tokens"].sum()) if not ok_requests.empty else 0,
        cost_usd=float(ok_requests["estimated_cost_usd"].sum()) if not ok_requests.empty else 0.0,
    )

    return build_results_payload(
        ablation_id=ablation_id,
        split_metrics=split_metrics,
        dev_tuned_test_metrics=dev_tuned_test_metrics,
        dev_tuned_threshold=dev_threshold,
        trivial=trivial,
        subgroups=subgroups,
        spearman=spearman,
        latency=latency,
        cost=cost,
        wall_time_s=0.0,
    )


def evaluate_instruction(config: EvalConfig) -> dict[str, Any]:
    """Score all posts in split once with a fixed instruction."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    cohort = _load_cohort(_REPO_ROOT / COHORT_PARQUET)
    split_cohort = cohort.loc[cohort["split"].eq(config.split)]
    tasks = build_split_tasks(cohort, split=config.split, view=config.view)
    run_name = config.transfer_id or config.ablation_id or "evaluate"
    wandb_config: dict[str, object] = {
        "view": config.view,
        "split": config.split,
        "model": jev_scorer.JEV_MODEL_ID,
        "batch_size": jev_scorer.BATCH_SIZE,
        "rate_cap_per_min": jev_scorer.MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
    }
    if config.ablation_id is not None:
        wandb_config["ablation_id"] = config.ablation_id
    if config.transfer_id is not None:
        wandb_config["transfer_id"] = config.transfer_id

    run = init_run(
        WandbRunSpec(
            group="jev_gepa",
            name=f"{run_name}_{config.split}",
            job_type="evaluate",
            config=wandb_config,
        )
    )
    wall_start = time.perf_counter()
    try:
        jev_scorer.run_scoring_pass(
            tasks,
            config.output_dir,
            view=config.view,
            api_key=secrets.get_jev_api_key(),
            max_starts_per_minute=jev_scorer.MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
            instruction=config.instruction,
            ablation_id=config.ablation_id or config.transfer_id or "",
        )
        results = finalize_eval_output(
            config.output_dir,
            split_cohort,
            ablation_id=config.ablation_id or config.transfer_id or run_name,
            headline_split=config.split,
        )
        results["headline_split"] = config.split
        results["wall_time_s"] = time.perf_counter() - wall_start
        if config.transfer_id is not None:
            results["transfer_id"] = config.transfer_id
        results_path = config.output_dir / "results.json"
        results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

        labels_path = config.output_dir / "labels.parquet"
        requests_path = config.output_dir / "requests.parquet"
        log_artifact(run, labels_path, name=f"{run_name}_{config.split}_labels", artifact_type="dataset")
        log_artifact(run, requests_path, name=f"{run_name}_{config.split}_requests", artifact_type="dataset")
        log_artifact(run, results_path, name=f"{run_name}_{config.split}_results", artifact_type="evaluation")
        run.log(
            {
                f"{config.split}_f1": results["split_metrics"][config.split]["f1"],
                "cost_usd": results["cost"]["cost_usd"],
            }
        )
        return results
    finally:
        run.finish()


def resolve_primary_eval_config(ablation_id: str, split: Literal["dev", "test"]) -> EvalConfig:
    """Build EvalConfig for a primary ablation test/dev read."""
    view = str(ABLATION_REGISTRY[ablation_id]["view"])
    instruction = load_selected_instruction(ablation_id)
    output_dir = _ablation_output_dir(ablation_id) / ("test_eval" if split == "test" else "dev_eval")
    return EvalConfig(
        ablation_id=ablation_id,
        transfer_id=None,
        instruction=instruction,
        view=view,  # type: ignore[arg-type]
        split=split,
        output_dir=output_dir,
    )


def resolve_transfer_eval_config(
    transfer_id: str,
    split: Literal["dev", "test"],
) -> EvalConfig:
    """Build EvalConfig for a transfer eval row."""
    try:
        entry = TRANSFER_REGISTRY[transfer_id]
    except KeyError as exc:
        raise ValueError(f"unknown transfer_id: {transfer_id}") from exc
    prompt_source = str(entry["prompt_source"])
    view = str(entry["view"])
    instruction = load_selected_instruction(prompt_source)
    output_dir = TRANSFER_OUTPUT_ROOT / transfer_id / split
    return EvalConfig(
        ablation_id=None,
        transfer_id=transfer_id,
        instruction=instruction,
        view=view,  # type: ignore[arg-type]
        split=split,
        output_dir=output_dir,
    )


def _read_dev_selection_metric(ablation_id: str, key: str) -> float:
    path = _ablation_output_dir(ablation_id) / DEV_SELECTION_FILENAME
    payload = _load_json(path)
    return float(payload[key])


def _read_test_f1(ablation_id: str) -> float:
    results_path = _ablation_output_dir(ablation_id) / "test_eval" / "results.json"
    payload = _load_json(results_path)
    return float(payload["split_metrics"]["test"]["f1"])


def compare_b1_b1t() -> dict[str, Any]:
    """Return nested dict keyed by ablation_id with dev_f1, test_f1, reflection_cost_usd."""
    comparison: dict[str, Any] = {}
    for ablation_id in (B1_ABLATION_ID, B1T_ABLATION_ID):
        comparison[ablation_id] = {
            "dev_f1": _read_dev_selection_metric(ablation_id, "selected_dev_f1"),
            "test_f1": _read_test_f1(ablation_id),
            "reflection_cost_usd": _read_dev_selection_metric(ablation_id, "reflection_cost_usd"),
        }
    return comparison


def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id for primary test read; --transfer-id for transfer eval; --split dev|test."""
    parser = argparse.ArgumentParser(description="Evaluate GEPA-selected prompts on dev or test")
    parser.add_argument("--ablation-id", choices=sorted(ABLATION_REGISTRY))
    parser.add_argument("--transfer-id", choices=sorted(TRANSFER_REGISTRY))
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    args = parser.parse_args(argv)

    if args.ablation_id is None and args.transfer_id is None:
        parser.error("pass --ablation-id or --transfer-id")
    if args.ablation_id is not None and args.transfer_id is not None:
        parser.error("pass only one of --ablation-id or --transfer-id")

    if args.ablation_id is not None:
        config = resolve_primary_eval_config(args.ablation_id, args.split)
    else:
        config = resolve_transfer_eval_config(args.transfer_id, args.split)

    results = evaluate_instruction(config)
    print(
        f"eval complete split={config.split} "
        f"f1={results['split_metrics'][config.split]['f1']:.4f} "
        f"cost_usd={results['cost']['cost_usd']:.4f}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
