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
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import artifacts
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
    union_cohort_subgroups,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    VIEW_MIRROR,
    VIEW_ORIGINAL,
    VIEW_PAIR,
    render_state_text,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import (
    COHORT_PARQUET,
    COHORT_UNION_PARQUET,
    COHORT_UNION_SPLIT_HASH_JSON,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run, log_artifact

ABLATION_IDS: tuple[str, ...] = (
    "A1_pair_study_prompt",
    "A2_original_only",
    "A3_mirror_only",
    "A4_pair_features_addendum",
)

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
OUTPUT_ROOT = EXPERIMENT_ROOT / "jev_baseline/outputs"
OUTPUT_ROOT_UNION = EXPERIMENT_ROOT / "jev_baseline/outputs_union"
SPLIT_HASH_JSON = EXPERIMENT_ROOT / "data/split_hash.json"
TASK_SHUFFLE_SEED = jev_scorer.SMOKE_SEED
DEFAULT_THRESHOLD = 0.5
SHARED_TEST_METRIC_TOLERANCE = 1e-4
COHORT_SOURCE_PART3 = "part3"
COHORT_SOURCE_UNION = "union"

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
    wandb_group: str
    cohort_source: str
    part3_output_dir: Path


@dataclass(frozen=True)
class ScoringCounts:
    """Reused vs newly scored posts and API requests for union runs."""

    posts_reused: int
    posts_new_scored: int
    requests_new: int


def resolve_ablation(ablation_id: str, *, cohort_source: str = COHORT_SOURCE_PART3) -> AblationConfig:
    """Map ablation_id to view, prompt arm, output dir, and Wandb run name."""
    if cohort_source not in {COHORT_SOURCE_PART3, COHORT_SOURCE_UNION}:
        raise ValueError(f"unknown cohort_source: {cohort_source}")
    try:
        entry = ABLATION_REGISTRY[ablation_id]
    except KeyError:
        raise ValueError(f"unknown ablation_id: {ablation_id}") from None
    base_name = str(entry["wandb_name"])
    if cohort_source == COHORT_SOURCE_UNION:
        return AblationConfig(
            ablation_id=ablation_id,
            view=str(entry["view"]),
            add_criteria=bool(entry["add_criteria"]),
            output_dir=OUTPUT_ROOT_UNION / ablation_id,
            wandb_name=f"{base_name}_union",
            wandb_group="jev_baseline_union",
            cohort_source=cohort_source,
            part3_output_dir=OUTPUT_ROOT / ablation_id,
        )
    return AblationConfig(
        ablation_id=ablation_id,
        view=str(entry["view"]),
        add_criteria=bool(entry["add_criteria"]),
        output_dir=OUTPUT_ROOT / ablation_id,
        wandb_name=base_name,
        wandb_group="jev_baseline",
        cohort_source=cohort_source,
        part3_output_dir=OUTPUT_ROOT / ablation_id,
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


def _load_split_hash(cohort_source: str) -> str:
    hash_path = (
        COHORT_UNION_SPLIT_HASH_JSON
        if cohort_source == COHORT_SOURCE_UNION
        else SPLIT_HASH_JSON
    )
    payload = json.loads((_REPO_ROOT / hash_path).read_text(encoding="utf-8"))
    return str(payload["split_hash"])


def study_part_coverage_label(n_raters_part2: int, n_raters_part3: int) -> str:
    """Return part2_only, part3_only, both, or unknown from rater counts."""
    if n_raters_part2 > 0 and n_raters_part3 > 0:
        return "both"
    if n_raters_part2 > 0:
        return "part2_only"
    if n_raters_part3 > 0:
        return "part3_only"
    return "unknown"


def _existing_prediction_post_ids(predictions_path: Path) -> set[str]:
    if not predictions_path.is_file():
        return set()
    post_ids: set[str] = set()
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            post_ids.add(str(payload["post_id"]))
    return post_ids


def seed_reused_predictions(
    *,
    source_predictions_path: Path,
    union_predictions_path: Path,
    union_post_ids: set[str],
) -> tuple[int, int]:
    """Append Part 3 prediction rows for union overlap without calling Jev."""
    if not source_predictions_path.is_file():
        raise FileNotFoundError(f"missing source predictions at {source_predictions_path}")
    existing = _existing_prediction_post_ids(union_predictions_path)
    union_predictions_path.parent.mkdir(parents=True, exist_ok=True)
    seeded = 0
    skipped = 0
    with source_predictions_path.open(encoding="utf-8") as source_handle:
        with union_predictions_path.open("a", encoding="utf-8") as union_handle:
            for line in source_handle:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                post_id = str(payload["post_id"])
                if post_id not in union_post_ids:
                    skipped += 1
                    continue
                if post_id in existing:
                    continue
                union_handle.write(stripped + "\n")
                existing.add(post_id)
                seeded += 1
    return seeded, skipped


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


def _materialize_labels_frame(labels: pd.DataFrame, *, include_union_columns: bool = False) -> pd.DataFrame:
    base_columns = [
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
    union_columns = [
        "n_raters_part2",
        "n_raters_part3",
        "in_part3_cohort_a",
        "label_changed_vs_part3",
        "study_part_coverage",
    ]
    columns = base_columns + (union_columns if include_union_columns else [])
    available = [column for column in columns if column in labels.columns]
    return labels[available].copy()


def _attach_study_part_coverage(labels: pd.DataFrame) -> pd.DataFrame:
    tagged = labels.copy()
    tagged["study_part_coverage"] = [
        study_part_coverage_label(int(part2), int(part3))
        for part2, part3 in zip(
            tagged["n_raters_part2"],
            tagged["n_raters_part3"],
            strict=True,
        )
    ]
    return tagged


def _classification_metrics_to_plain(metrics: Any) -> dict[str, float | int]:
    return {
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "balanced_accuracy": metrics.balanced_accuracy,
        "roc_auc": metrics.roc_auc,
        "pr_auc": metrics.pr_auc,
        "n": metrics.n,
    }


def _metrics_match_reference(
    computed: dict[str, float | int],
    reference: dict[str, float | int],
    *,
    tolerance: float,
) -> bool:
    for key in ("f1", "precision", "recall", "accuracy"):
        if abs(float(computed[key]) - float(reference[key])) > tolerance:
            return False
    return True


def _load_prediction_map(predictions_path: Path) -> dict[str, float]:
    mapping: dict[str, float] = {}
    if not predictions_path.is_file():
        return mapping
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            mapping[str(payload["post_id"])] = float(payload["probability_remove"])
    return mapping


def _shared_test_post_ids(labels: pd.DataFrame, part3_cohort: pd.DataFrame) -> set[str]:
    union_test = labels.loc[labels["split"].eq("test"), "post_id"].astype(str)
    part3_test = part3_cohort.loc[part3_cohort["split"].eq("test"), "post_id"].astype(str)
    return set(union_test) & set(part3_test)


def _metrics_from_part3_predictions(
    part3_cohort: pd.DataFrame,
    *,
    shared_post_ids: set[str],
    part3_predictions_path: Path,
) -> dict[str, float | int]:
    part3_test = part3_cohort.loc[
        part3_cohort["split"].eq("test") & part3_cohort["post_id"].astype(str).isin(shared_post_ids)
    ]
    prediction_map = _load_prediction_map(part3_predictions_path)
    scores = [prediction_map[str(post_id)] for post_id in part3_test["post_id"]]
    metrics = probability_metrics(
        part3_test["label"].astype(int).tolist(),
        scores,
        threshold=DEFAULT_THRESHOLD,
    )
    return _classification_metrics_to_plain(metrics)


def _build_shared_test_comparison(
    labels: pd.DataFrame,
    *,
    part3_cohort: pd.DataFrame,
    part3_reference_results: dict[str, Any] | None,
    part3_predictions_path: Path,
    tolerance: float,
) -> dict[str, Any]:
    shared_ids = _shared_test_post_ids(labels, part3_cohort)
    union_test = labels.loc[labels["split"].eq("test")].copy()
    shared_union = union_test.loc[union_test["post_id"].astype(str).isin(shared_ids)]
    part3_test = part3_cohort.loc[part3_cohort["split"].eq("test")][["post_id", "label"]].copy()
    part3_test["post_id"] = part3_test["post_id"].astype(str)
    shared_part3 = part3_test.loc[part3_test["post_id"].isin(shared_ids)].merge(
        shared_union[["post_id", "p_remove"]],
        on="post_id",
        how="inner",
        validate="one_to_one",
    )
    metrics_union_labels = probability_metrics(
        shared_union["keep_remove_label"].astype(int).tolist(),
        shared_union["p_remove"].astype(float).tolist(),
        threshold=DEFAULT_THRESHOLD,
    )
    metrics_part3_labels = probability_metrics(
        shared_part3["label"].astype(int).tolist(),
        shared_part3["p_remove"].astype(float).tolist(),
        threshold=DEFAULT_THRESHOLD,
    )
    metrics_part3_plain = _classification_metrics_to_plain(metrics_part3_labels)
    recomputed_part3_reference = _metrics_from_part3_predictions(
        part3_cohort,
        shared_post_ids=shared_ids,
        part3_predictions_path=part3_predictions_path,
    )
    matches_reference = _metrics_match_reference(
        metrics_part3_plain,
        recomputed_part3_reference,
        tolerance=tolerance,
    )
    full_part3_test_reference = (
        part3_reference_results.get("metrics_at_0_5", {}).get("test", {})
        if part3_reference_results
        else {}
    )
    return {
        "n_shared_test_posts": len(shared_ids),
        "metrics_union_labels": _classification_metrics_to_plain(metrics_union_labels),
        "metrics_part3_labels": metrics_part3_plain,
        "metrics_part3_shared_recomputed": recomputed_part3_reference,
        "metrics_part3_full_test_reference": full_part3_test_reference,
        "matches_part3_reference": matches_reference,
    }


def finalize_union_ablation(
    output_dir: Path,
    cohort: pd.DataFrame,
    *,
    part3_cohort: pd.DataFrame,
    part3_reference_results: dict[str, Any] | None,
    part3_predictions_path: Path,
    scoring_counts: ScoringCounts,
    tolerance: float = SHARED_TEST_METRIC_TOLERANCE,
) -> dict[str, Any]:
    """Finalize union outputs with extra subgroups and shared-test checks."""
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
    labels = _attach_study_part_coverage(labels)

    labels_path = output_dir / "labels.parquet"
    _materialize_labels_frame(labels, include_union_columns=True).to_parquet(labels_path, index=False)

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
    subgroups.extend(union_cohort_subgroups(test_subset, threshold=DEFAULT_THRESHOLD))
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

    payload = build_results_payload(
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
    payload["cohort_source"] = COHORT_SOURCE_UNION
    payload["scoring_counts"] = {
        "posts_reused": scoring_counts.posts_reused,
        "posts_new_scored": scoring_counts.posts_new_scored,
        "requests_new": scoring_counts.requests_new,
    }
    payload["shared_test_comparison"] = _build_shared_test_comparison(
        labels,
        part3_cohort=part3_cohort,
        part3_reference_results=part3_reference_results,
        part3_predictions_path=part3_predictions_path,
        tolerance=tolerance,
    )
    return payload


def _load_part3_reference_results(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _upload_union_ablation_artifacts(output_dir: Path, ablation_id: str) -> str:
    base_key = (
        f"{artifacts.EXPERIMENT_S3_PREFIX}/jev_baseline_union/{ablation_id}"
    )
    store = CampaignObjectStore(artifacts.OUTPUT_S3_BUCKET)
    for filename in ("labels.parquet", "requests.parquet", "results.json"):
        local_path = output_dir / filename
        key = f"{base_key}/{filename}"
        body = local_path.read_bytes()
        existing = store.get(key)
        if existing is None:
            store.put_new(key, body)
        else:
            store.replace(key, body, etag=existing.etag)
    return f"s3://{artifacts.OUTPUT_S3_BUCKET}/{base_key}/"


def score_ablation(
    ablation_id: str,
    *,
    cohort_path: Path,
    cohort_source: str = COHORT_SOURCE_PART3,
    resume: bool = True,
) -> Path:
    """Score cohort A for one ablation and return output_dir."""
    config = resolve_ablation(ablation_id, cohort_source=cohort_source)
    cohort = _load_cohort(cohort_path)
    part3_cohort = (
        _load_cohort(_REPO_ROOT / COHORT_PARQUET)
        if cohort_source == COHORT_SOURCE_UNION
        else None
    )
    tasks = build_post_tasks(
        cohort,
        view=config.view,
        add_criteria=config.add_criteria,
    )
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / jev_scorer.PREDICTIONS_FILENAME
    requests_path = output_dir / jev_scorer.REQUESTS_FILENAME
    if not resume:
        if predictions_path.is_file():
            predictions_path.unlink()
        if requests_path.is_file():
            requests_path.unlink()

    scoring_counts = ScoringCounts(posts_reused=0, posts_new_scored=0, requests_new=0)
    if cohort_source == COHORT_SOURCE_UNION:
        union_post_ids = set(cohort["post_id"].astype(str))
        part3_post_ids = set(part3_cohort["post_id"].astype(str)) if part3_cohort is not None else set()
        overlap_ids = union_post_ids & part3_post_ids
        source_predictions = config.part3_output_dir / jev_scorer.PREDICTIONS_FILENAME
        seeded, _skipped = seed_reused_predictions(
            source_predictions_path=source_predictions,
            union_predictions_path=predictions_path,
            union_post_ids=overlap_ids,
        )
        scoring_counts = ScoringCounts(
            posts_reused=seeded,
            posts_new_scored=len(union_post_ids - _existing_prediction_post_ids(predictions_path)),
            requests_new=0,
        )

    split_hash = _load_split_hash(cohort_source)
    prompt_hash = jev_scorer.instruction_sha256(None, config.view)
    run = init_run(
        WandbRunSpec(
            group=config.wandb_group,
            name=config.wandb_name,
            job_type="score",
            config={
                "ablation_id": ablation_id,
                "cohort_source": cohort_source,
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
    s3_prefix = ""
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
        if cohort_source == COHORT_SOURCE_UNION:
            requests_new = len(_load_requests_frame(requests_path))
            assert part3_cohort is not None
            part3_ids = set(part3_cohort["post_id"].astype(str))
            union_ids = set(cohort["post_id"].astype(str))
            scoring_counts = ScoringCounts(
                posts_reused=len(union_ids & part3_ids),
                posts_new_scored=len(union_ids - part3_ids),
                requests_new=requests_new,
            )
            part3_reference = _load_part3_reference_results(
                config.part3_output_dir / "results.json"
            )
            results = finalize_union_ablation(
                output_dir,
                cohort,
                part3_cohort=part3_cohort,
                part3_reference_results=part3_reference,
                part3_predictions_path=config.part3_output_dir / jev_scorer.PREDICTIONS_FILENAME,
                scoring_counts=scoring_counts,
            )
        else:
            results = finalize_ablation(output_dir, cohort)
        results["wall_time_s"] = time.perf_counter() - wall_start
        results_path = output_dir / "results.json"
        results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        if cohort_source == COHORT_SOURCE_UNION:
            s3_prefix = _upload_union_ablation_artifacts(output_dir, ablation_id)
            results["s3_prefix"] = s3_prefix
            results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

        labels_path = output_dir / "labels.parquet"
        requests_parquet_path = output_dir / "requests.parquet"
        log_artifact(run, labels_path, name=f"{ablation_id}_labels", artifact_type="dataset")
        log_artifact(
            run,
            requests_parquet_path,
            name=f"{ablation_id}_requests",
            artifact_type="dataset",
        )
        log_artifact(run, results_path, name=f"{ablation_id}_results", artifact_type="evaluation")

        log_payload: dict[str, Any] = {
            "test_f1": results["metrics_at_0_5"]["test"]["f1"],
            "test_accuracy": results["metrics_at_0_5"]["test"]["accuracy"],
            "dev_tuned_test_f1": results["dev_tuned_test_metrics"]["f1"],
            "cost_usd": results["cost"]["cost_usd"],
        }
        if cohort_source == COHORT_SOURCE_UNION:
            log_payload.update(
                {
                    "posts_reused": scoring_counts.posts_reused,
                    "posts_new_scored": scoring_counts.posts_new_scored,
                    "requests_new": scoring_counts.requests_new,
                    "shared_test_matches_part3_reference": results["shared_test_comparison"][
                        "matches_part3_reference"
                    ],
                }
            )
        run.log(log_payload)
        if cohort_source == COHORT_SOURCE_UNION:
            print(
                f"ablation_id={ablation_id} cohort_source=union "
                f"posts_reused={scoring_counts.posts_reused} "
                f"posts_new_scored={scoring_counts.posts_new_scored} "
                f"requests_new={scoring_counts.requests_new} "
                f"s3_prefix={s3_prefix} wandb_url={run.url}"
            )
    finally:
        run.finish()

    deadletter_path = output_dir / jev_scorer.DEADLETTER_FILENAME
    deadletter_count = 0
    if deadletter_path.is_file():
        with deadletter_path.open(encoding="utf-8") as handle:
            deadletter_count = sum(1 for line in handle if line.strip())
    posts_scored = len(_load_predictions_frame(predictions_path))
    if cohort_source == COHORT_SOURCE_PART3:
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
    """CLI: --ablation-id (required), --cohort-path, --cohort-source, --all, --no-resume."""
    parser = argparse.ArgumentParser(description="Stage A Jev baseline runner")
    parser.add_argument("--ablation-id", choices=ABLATION_IDS)
    parser.add_argument(
        "--cohort-source",
        choices=[COHORT_SOURCE_PART3, COHORT_SOURCE_UNION],
        default=COHORT_SOURCE_PART3,
    )
    parser.add_argument("--cohort-path", type=Path, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not args.all and args.ablation_id is None:
        parser.error("pass --ablation-id or --all")

    if args.cohort_path is None:
        args.cohort_path = (
            COHORT_UNION_PARQUET
            if args.cohort_source == COHORT_SOURCE_UNION
            else COHORT_PARQUET
        )

    ablation_ids = ABLATION_IDS if args.all else (args.ablation_id,)
    for ablation in ablation_ids:
        score_ablation(
            ablation,
            cohort_path=_REPO_ROOT / args.cohort_path,
            cohort_source=args.cohort_source,
            resume=not args.no_resume,
        )


if __name__ == "__main__":
    main(sys.argv[1:])  # pragma: no cover
