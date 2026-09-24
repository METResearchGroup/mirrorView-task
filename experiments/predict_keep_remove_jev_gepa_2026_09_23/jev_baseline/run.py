"""Stage A Jev baseline runner for cohort A ablations A1 through A4.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py --ablation-id A1_pair_study_prompt
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

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
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    VIEW_MIRROR,
    VIEW_ORIGINAL,
    VIEW_PAIR,
    render_state_text,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_PARQUET
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run, log_artifact

ABLATION_IDS: tuple[str, ...] = (
    "A1_pair_study_prompt",
    "A2_original_only",
    "A3_mirror_only",
    "A4_pair_features_addendum",
)

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
OUTPUT_ROOT = EXPERIMENT_ROOT / "jev_baseline/outputs"
SPLIT_HASH_JSON = EXPERIMENT_ROOT / "data/split_hash.json"
TASK_SHUFFLE_SEED = jev_scorer.SMOKE_SEED
DEFAULT_THRESHOLD = 0.5

ABLATION_REGISTRY: dict[str, dict[str, Any]] = {
    "A1_pair_study_prompt": {
        "view": VIEW_PAIR,
        "add_criteria": False,
        "wandb_name": "A1_pair_study_prompt",
    },
    "A2_original_only": {
        "view": VIEW_ORIGINAL,
        "add_criteria": False,
        "wandb_name": "A2_original_only",
    },
    "A3_mirror_only": {
        "view": VIEW_MIRROR,
        "add_criteria": False,
        "wandb_name": "A3_mirror_only",
    },
    "A4_pair_features_addendum": {
        "view": VIEW_PAIR,
        "add_criteria": True,
        "wandb_name": "A4_pair_features_addendum",
    },
}


@dataclass(frozen=True)
class AblationConfig:
    """Resolved Stage A ablation with view, prompt arm, output path, and Wandb name."""

    ablation_id: str
    view: str
    add_criteria: bool
    output_dir: Path
    wandb_name: str


def resolve_ablation(ablation_id: str) -> AblationConfig:
    """Map ablation_id to view, prompt arm, output dir, and Wandb run name."""
    try:
        entry = ABLATION_REGISTRY[ablation_id]
    except KeyError:
        raise ValueError(f"unknown ablation_id: {ablation_id}") from None
    return AblationConfig(
        ablation_id=ablation_id,
        view=str(entry["view"]),
        add_criteria=bool(entry["add_criteria"]),
        output_dir=OUTPUT_ROOT / ablation_id,
        wandb_name=str(entry["wandb_name"]),
    )


def build_post_tasks(
    cohort: pd.DataFrame,
    *,
    view: str,
    add_criteria: bool,
) -> list[jev_scorer.PostTask]:
    """Shuffle post_ids and build PostTask list for scoring."""
    rng = np.random.default_rng(TASK_SHUFFLE_SEED)
    shuffled_indices = rng.permutation(cohort.index.to_numpy())
    shuffled = cohort.loc[shuffled_indices]
    tasks: list[jev_scorer.PostTask] = []
    for row in shuffled.itertuples():
        tasks.append(
            jev_scorer.PostTask(
                post_id=str(row.post_id),
                state_text=render_state_text(
                    view,
                    str(row.original_text),
                    str(row.mirror_text),
                    str(row.post_1_role),
                    add_criteria=add_criteria,
                ),
                gold_label=int(row.label),
            )
        )
    return tasks


def _load_cohort(cohort_path: Path) -> pd.DataFrame:
    if not cohort_path.is_file():
        raise FileNotFoundError(f"cohort parquet missing at {cohort_path}")
    return pd.read_parquet(cohort_path)


def _load_split_hash() -> str:
    payload = json.loads(SPLIT_HASH_JSON.read_text(encoding="utf-8"))
    return str(payload["split_hash"])


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


def _split_frame(labels: pd.DataFrame, split_name: str) -> pd.DataFrame:
    if split_name == "full":
        return labels
    return labels.loc[labels["split"] == split_name]


def _compute_split_metrics(labels: pd.DataFrame) -> dict[SplitName, Any]:
    split_names: list[SplitName] = ["test", "dev", "gepa_pool", "full"]
    metrics: dict[SplitName, Any] = {}
    for split_name in split_names:
        subset = _split_frame(labels, split_name)
        metrics[split_name] = probability_metrics(
            subset["keep_remove_label"].astype(int).tolist(),
            subset["p_remove"].astype(float).tolist(),
            threshold=DEFAULT_THRESHOLD,
        )
    return metrics


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


def score_ablation(
    ablation_id: str,
    *,
    cohort_path: Path,
    output_dir: Path,
    resume: bool = True,
) -> Path:
    """Score cohort A for one ablation and return output_dir."""
    config = resolve_ablation(ablation_id)
    cohort = _load_cohort(cohort_path)
    tasks = build_post_tasks(
        cohort,
        view=config.view,
        add_criteria=config.add_criteria,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / jev_scorer.PREDICTIONS_FILENAME
    if not resume and predictions_path.is_file():
        predictions_path.unlink()
        requests_path = output_dir / jev_scorer.REQUESTS_FILENAME
        if requests_path.is_file():
            requests_path.unlink()

    split_hash = _load_split_hash()
    prompt_hash = jev_scorer.instruction_sha256(None, config.view)
    run = init_run(
        WandbRunSpec(
            group="jev_baseline",
            name=config.wandb_name,
            job_type="score",
            config={
                "ablation_id": ablation_id,
                "view": config.view,
                "model": jev_scorer.JEV_MODEL_ID,
                "batch_size": jev_scorer.BATCH_SIZE,
                "rate_cap_per_min": jev_scorer.MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
                "split_hash": split_hash,
                "prompt_hash": prompt_hash,
            },
        )
    )

    wall_start = time.perf_counter()
    try:
        jev_scorer.run_scoring_pass(
            tasks,
            output_dir,
            view=config.view,
            api_key=secrets.get_jev_api_key(),
            max_starts_per_minute=jev_scorer.MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
            instruction=None,
            ablation_id=ablation_id,
            add_criteria=config.add_criteria,
        )
        results = finalize_ablation(output_dir, cohort)
        results["wall_time_s"] = time.perf_counter() - wall_start
        results_path = output_dir / "results.json"
        results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

        labels_path = output_dir / "labels.parquet"
        requests_path = output_dir / "requests.parquet"
        log_artifact(run, labels_path, name=f"{ablation_id}_labels", artifact_type="dataset")
        log_artifact(run, requests_path, name=f"{ablation_id}_requests", artifact_type="dataset")
        log_artifact(run, results_path, name=f"{ablation_id}_results", artifact_type="evaluation")

        run.log(
            {
                "test_f1": results["metrics_at_0_5"]["test"]["f1"],
                "test_accuracy": results["metrics_at_0_5"]["test"]["accuracy"],
                "dev_tuned_test_f1": results["dev_tuned_test_metrics"]["f1"],
                "cost_usd": results["cost"]["cost_usd"],
            }
        )
    finally:
        run.finish()

    deadletter_path = output_dir / jev_scorer.DEADLETTER_FILENAME
    deadletter_count = 0
    if deadletter_path.is_file():
        with deadletter_path.open(encoding="utf-8") as handle:
            deadletter_count = sum(1 for line in handle if line.strip())
    posts_scored = len(_load_predictions_frame(predictions_path))
    print(
        f"ablation_id={ablation_id} posts_scored={posts_scored} deadletter={deadletter_count}"
    )
    return output_dir


def _assert_prediction_coverage(predictions: pd.DataFrame, cohort: pd.DataFrame) -> None:
    n_predictions = len(predictions)
    n_cohort = len(cohort)
    if n_predictions != n_cohort:
        missing = n_cohort - n_predictions
        raise RuntimeError(
            f"prediction coverage incomplete: {n_predictions}/{n_cohort} rows scored; "
            f"{missing} missing"
        )


def finalize_ablation(output_dir: Path, cohort: pd.DataFrame) -> dict[str, Any]:
    """Join predictions, write labels/requests parquet and results.json."""
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
    dev_subset = _split_frame(labels, "dev")
    test_subset = _split_frame(labels, "test")
    dev_threshold, _dev_f1 = tune_threshold_for_f1(
        dev_subset["keep_remove_label"].astype(int).tolist(),
        dev_subset["p_remove"].astype(float).tolist(),
    )
    dev_tuned_test_metrics = probability_metrics(
        test_subset["keep_remove_label"].astype(int).tolist(),
        test_subset["p_remove"].astype(float).tolist(),
        threshold=dev_threshold,
    )
    trivial = trivial_baselines(test_subset["keep_remove_label"].astype(int).tolist())
    subgroups = subgroup_metrics(test_subset, threshold=DEFAULT_THRESHOLD)
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
        ablation_id=str(output_dir.name),
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


def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id (required), --cohort-path, --all, --no-resume."""
    parser = argparse.ArgumentParser(description="Stage A Jev baseline runner")
    parser.add_argument("--ablation-id", choices=ABLATION_IDS)
    parser.add_argument("--cohort-path", type=Path, default=COHORT_PARQUET)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not args.all and args.ablation_id is None:
        parser.error("pass --ablation-id or --all")

    ablation_ids = ABLATION_IDS if args.all else (args.ablation_id,)
    for ablation in ablation_ids:
        config = resolve_ablation(ablation)
        score_ablation(
            ablation,
            cohort_path=args.cohort_path,
            output_dir=config.output_dir,
            resume=not args.no_resume,
        )


if __name__ == "__main__":
    main(sys.argv[1:])  # pragma: no cover
