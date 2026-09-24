"""GEPA evaluate runner for rebuilt union cohort test reads.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py --ablation-id R1_gepa_pair --split test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    DEFAULT_BATCH_SIZE,
    JevDataInst,
    ViewName,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.artifacts import upload_rebuilt
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_RUN_DIRNAME,
    OUTPUT_ROOT,
    STUDY_COMPONENT_KEY,
    WANDB_GROUP,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import (
    ABLATION_IDS,
    ABLATION_REGISTRY,
    DEFAULT_RATE_CAP_PER_MIN,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer, pricing, secrets
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import (
    ClassificationMetrics,
    CostSummary,
    SplitName,
    build_results_payload,
    latency_summary,
    probability_metrics,
    spearman_remove_share,
    subgroup_metrics,
    trivial_baselines,
    union_cohort_subgroups,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import render_posts_only_state
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run, log_artifact

TEST_RESULTS_FILENAME = "test_results.json"
DEFAULT_THRESHOLD = 0.5
EvalSplit = Literal["dev", "test"]
ScorerFn = Callable[..., jev_scorer.BatchResult]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _classification_metrics_to_dict(metrics: ClassificationMetrics) -> dict[str, Any]:
    payload = asdict(metrics)
    payload["confusion"] = asdict(metrics.confusion)
    return payload


def _row_to_jev_data_inst(row: object) -> JevDataInst:
    return JevDataInst(
        post_id=str(row.post_id),
        original_text=str(row.original_text),
        mirror_text=str(row.mirror_text),
        post_1_role=str(row.post_1_role),
        post_2_role=str(row.post_2_role),
        label=int(row.label),
        n_keep=int(row.n_keep),
        n_remove=int(row.n_remove),
        n_raters=int(row.n_raters),
        remove_share=float(row.remove_share),
        sampled_stance=str(row.sampled_stance),
        sample_toxicity_type=str(row.sample_toxicity_type),
    )


def load_selected_study_instruction(ablation_dir: Path) -> str:
    """Load study instruction for the dev-selected candidate."""
    dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
    gepa_result_path = ablation_dir / GEPA_RUN_DIRNAME / GEPA_RESULT_FILENAME
    if not dev_selection_path.is_file():
        raise FileNotFoundError(f"missing dev selection at {dev_selection_path}")
    if not gepa_result_path.is_file():
        raise FileNotFoundError(f"missing gepa result at {gepa_result_path}")
    dev_selection = _load_json(dev_selection_path)
    gepa_result = _load_json(gepa_result_path)
    selected_idx = int(dev_selection["selected_candidate_idx"])
    candidates = gepa_result["candidates"]
    return str(candidates[selected_idx][STUDY_COMPONENT_KEY])


def load_dev_selection_threshold(ablation_dir: Path) -> float:
    """Return the dev-A tuned threshold from dev_selection.json."""
    path = ablation_dir / DEV_SELECTION_FILENAME
    payload = _load_json(path)
    return float(payload["threshold"])


def _materialize_labels_frame(labels: pd.DataFrame) -> pd.DataFrame:
    columns = [
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
    available = [column for column in columns if column in labels.columns]
    return labels[available].copy()


def _compute_split_metrics(
    labels: pd.DataFrame,
    *,
    threshold: float,
) -> dict[SplitName, ClassificationMetrics]:
    split_names: list[SplitName] = ["test", "dev", "gepa_pool", "full"]
    metrics: dict[SplitName, ClassificationMetrics] = {}
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
            threshold=threshold,
        )
    return metrics


def score_instances_with_requests(
    instances: list[JevDataInst],
    *,
    view: ViewName,
    study_instruction: str,
    ablation_id: str,
    scorer: ScorerFn,
    client: Any,
    rate_limiter: RequestStartLimiter,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score posts in batches and return prediction and request frames."""
    prediction_rows: list[dict[str, Any]] = []
    request_rows: list[dict[str, Any]] = []
    instruction_hash = jev_scorer.instruction_sha256(study_instruction, view)

    for batch_index, chunk_start in enumerate(range(0, len(instances), batch_size)):
        chunk = instances[chunk_start : chunk_start + batch_size]
        state_texts = [
            render_posts_only_state(
                view,
                instance.original_text,
                instance.mirror_text,
                instance.post_1_role,
            )
            for instance in chunk
        ]
        rate_limiter.wait()
        started_at = datetime.now(timezone.utc).isoformat()
        batch_result = scorer(
            client,
            state_texts,
            view,
            study_instruction=study_instruction,
        )
        n_posts = len(chunk)
        per_post_latency = batch_result.latency_ms / n_posts if n_posts else 0.0
        request_rows.append(
            {
                "request_id": f"{ablation_id}:{batch_index}:1",
                "ablation_id": ablation_id,
                "batch_index": batch_index,
                "post_ids": [instance.post_id for instance in chunk],
                "n_posts": n_posts,
                "attempt": 1,
                "status": "ok",
                "error_type": None,
                "started_at_utc": started_at,
                "latency_ms": batch_result.latency_ms,
                "latency_per_post_ms": per_post_latency,
                "input_tokens": batch_result.input_tokens,
                "output_tokens": batch_result.output_tokens,
                "estimated_cost_usd": pricing.estimate_jev_cost_usd(
                    batch_result.input_tokens,
                    batch_result.output_tokens,
                ),
                "model": batch_result.model_version,
                "instruction_sha256": instruction_hash,
            }
        )
        for position, (instance, probability) in enumerate(
            zip(chunk, batch_result.probabilities)
        ):
            prediction_rows.append(
                {
                    "post_id": instance.post_id,
                    "probability_remove": float(probability),
                }
            )
    predictions = pd.DataFrame(prediction_rows)
    requests = pd.DataFrame(request_rows)
    return predictions, requests


def build_test_results_payload(
    labels: pd.DataFrame,
    requests: pd.DataFrame,
    *,
    ablation_id: str,
    dev_threshold: float,
    headline_split: EvalSplit,
    wall_time_s: float,
) -> dict[str, Any]:
    """Build test_results.json payload aligned with union Stage A metrics."""
    headline = labels.loc[labels["split"] == headline_split]
    y_true = headline["keep_remove_label"].astype(int).tolist()
    y_prob = headline["p_remove"].astype(float).tolist()
    metrics_at_dev = probability_metrics(y_true, y_prob, threshold=dev_threshold)
    metrics_at_default = probability_metrics(y_true, y_prob, threshold=DEFAULT_THRESHOLD)

    split_metrics = _compute_split_metrics(labels, threshold=DEFAULT_THRESHOLD)
    trivial = trivial_baselines(y_true)
    subgroups = subgroup_metrics(headline, threshold=DEFAULT_THRESHOLD)
    subgroups.extend(union_cohort_subgroups(headline, threshold=DEFAULT_THRESHOLD))
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
        ablation_id=ablation_id,
        split_metrics=split_metrics,
        dev_tuned_test_metrics=metrics_at_dev,
        dev_tuned_threshold=dev_threshold,
        trivial=trivial,
        subgroups=subgroups,
        spearman=spearman,
        latency=latency,
        cost=cost,
        wall_time_s=wall_time_s,
    )
    payload["headline_split"] = headline_split
    payload["metrics_at_dev_threshold"] = _classification_metrics_to_dict(metrics_at_dev)
    payload["metrics_at_0_5"] = _classification_metrics_to_dict(metrics_at_default)
    return payload


def run_evaluate(
    ablation_id: str,
    split: EvalSplit,
    *,
    ablation_dir: Path,
    cohort_parquet: Path,
    force: bool = False,
    scorer: ScorerFn | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Score the selected candidate once on ``split`` and write test_results.json."""
    results_path = ablation_dir / TEST_RESULTS_FILENAME
    if results_path.is_file() and not force:
        print("test_already_scored")
        return _load_json(results_path)

    view = str(ABLATION_REGISTRY[ablation_id]["view"])
    study_instruction = load_selected_study_instruction(ablation_dir)
    dev_threshold = load_dev_selection_threshold(ablation_dir)
    frame = pd.read_parquet(cohort_parquet)
    split_frame = frame.loc[frame["split"].eq(split)]
    instances = [_row_to_jev_data_inst(row) for row in split_frame.itertuples()]

    scorer_fn = scorer or jev_scorer.score_batch_with_study_instruction
    if client is None:
        resolved_client = jev_scorer.build_client(secrets.get_jev_api_key())
    else:
        resolved_client = client
    rate_limiter = RequestStartLimiter(DEFAULT_RATE_CAP_PER_MIN)

    run = init_run(
        WandbRunSpec(
            group=WANDB_GROUP,
            name=f"{ablation_id}_{split}_eval",
            job_type="evaluate",
            config={
                "ablation_id": ablation_id,
                "split": split,
                "view": view,
                "rate_cap_per_min": DEFAULT_RATE_CAP_PER_MIN,
                "batch_size": DEFAULT_BATCH_SIZE,
            },
        )
    )
    wall_start = time.perf_counter()
    try:
        predictions, requests = score_instances_with_requests(
            instances,
            view=view,  # type: ignore[arg-type]
            study_instruction=study_instruction,
            ablation_id=ablation_id,
            scorer=scorer_fn,
            client=resolved_client,
            rate_limiter=rate_limiter,
        )
        labels = split_frame.merge(predictions, on="post_id", how="inner", validate="one_to_one")
        labels = labels.rename(columns={"label": "keep_remove_label", "probability_remove": "p_remove"})
        labels["predicted_label"] = (labels["p_remove"] >= DEFAULT_THRESHOLD).astype(int)

        labels_path = ablation_dir / "labels.parquet"
        _materialize_labels_frame(labels).to_parquet(labels_path, index=False)
        requests_path = ablation_dir / "requests.parquet"
        requests.to_parquet(requests_path, index=False)

        payload = build_test_results_payload(
            labels,
            requests,
            ablation_id=ablation_id,
            dev_threshold=dev_threshold,
            headline_split=split,
            wall_time_s=time.perf_counter() - wall_start,
        )
        results_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        upload_rebuilt(ablation_dir)
        log_artifact(run, labels_path, name=f"{ablation_id}_{split}_labels", artifact_type="dataset")
        log_artifact(run, requests_path, name=f"{ablation_id}_{split}_requests", artifact_type="dataset")
        log_artifact(
            run,
            results_path,
            name=f"{ablation_id}_{split}_results",
            artifact_type="evaluation",
        )
        run.log(
            {
                f"{split}_f1_dev_threshold": payload["metrics_at_dev_threshold"]["f1"],
                f"{split}_f1_at_0_5": payload["metrics_at_0_5"]["f1"],
                "cost_usd": payload["cost"]["cost_usd"],
            }
        )
        print(f"wrote {results_path}")
        return payload
    finally:
        run.finish()


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for rebuilt GEPA evaluation."""
    parser = argparse.ArgumentParser(description="Run rebuilt Jev GEPA evaluation")
    parser.add_argument("--ablation-id", required=True, choices=sorted(ABLATION_IDS))
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--force", action="store_true", help="Re-score even if test_results.json exists")
    args = parser.parse_args(argv)
    ablation_dir = OUTPUT_ROOT / args.ablation_id
    cohort_parquet = _REPO_ROOT / COHORT_UNION_PARQUET
    run_evaluate(
        args.ablation_id,
        args.split,
        ablation_dir=ablation_dir,
        cohort_parquet=cohort_parquet,
        force=args.force,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
