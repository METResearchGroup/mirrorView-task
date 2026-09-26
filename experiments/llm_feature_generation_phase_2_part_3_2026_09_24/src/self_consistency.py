"""Self-consistency re-labeling via OpenAI Batch.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency \\
      --codebook outputs/shared/codebook/approved_<ts>/codebook.json \\
      --label-matrix outputs/shared/label_matrix.parquet \\
      --sample-size 200 --seed 42
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batch_client, constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts import (
    load_codebook,
    load_union_cohort,
    post_text_for_surface,
    require_approved_codebook,
)

RELABEL_FILENAME = "relabeled.jsonl"
SCORES_FILENAME = "scores.json"
BATCH_INPUTS_DIRNAME = "batch_inputs"


def sample_label_pairs(matrix: pd.DataFrame, sample_size: int, seed: int) -> pd.DataFrame:
    """Sample matrix rows reproducibly for self-consistency."""
    rng = np.random.default_rng(seed)
    if len(matrix) < sample_size:
        raise ValueError(f"matrix has {len(matrix)} rows; need {sample_size}")
    indices = rng.choice(len(matrix), size=sample_size, replace=False)
    return matrix.iloc[sorted(indices)].reset_index(drop=True)


def score_self_consistency(
    baseline: pd.DataFrame,
    relabeled: pd.DataFrame,
    feature_ids: list[str],
) -> dict[str, Any]:
    """Compute per-feature agreement between baseline and relabeled frames."""
    relabeled = relabeled.set_index(["post_id", "text_surface"])
    baseline_indexed = baseline.set_index(["post_id", "text_surface"])
    per_feature: dict[str, dict[str, float | int]] = {}
    below: list[str] = []
    n_pairs = len(baseline_indexed)
    for feature_id in feature_ids:
        agree = float((baseline_indexed[feature_id] == relabeled[feature_id]).mean())
        per_feature[feature_id] = {"agreement_rate": agree, "n_pairs": n_pairs}
        if agree < constants.SELF_CONSISTENCY_THRESHOLD:
            below.append(feature_id)
    return {"per_feature": per_feature, "features_below_threshold": below}


def run_self_consistency(
    codebook_path: Path,
    label_matrix_path: Path,
    sample_size: int,
    seed: int,
    client: batch_client.OpenAIBatchClient | None = None,
) -> Path:
    """Re-label a sample via Batch and write scores under ``self_consistency/``."""
    require_approved_codebook(codebook_path)
    features, _ = load_codebook(codebook_path)
    feature_ids = [feature["feature_id"] for feature in features]
    matrix = pd.read_parquet(label_matrix_path)
    sample = sample_label_pairs(matrix, sample_size, seed)
    run_dir = paths.self_consistency_dir() / paths.make_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    tasks = _tasks_for_sample(sample)
    jsonl_paths = batch_client.build_batch_jsonl_from_tasks(
        tasks,
        features,
        run_dir / BATCH_INPUTS_DIRNAME,
    )
    openai_client = client or batch_client.get_openai_client()
    batch_ids = [batch_client.submit_batch(openai_client, path) for path in jsonl_paths]
    relabeled_rows: list[batch_client.LabelShardRow] = []
    for batch_id in batch_ids:
        batch = batch_client.poll_batch(openai_client, batch_id)
        output_lines, _ = batch_client.download_results(openai_client, batch)
        relabeled_rows.extend(batch_client.parse_batch_output(output_lines))
        usage = batch_client.collect_usage_from_output_lines(output_lines)
        batch_client.append_batch_cost_log(
            stage=batch_client.STAGE_SELF_CONSISTENCY_BATCH,
            **usage,
        )
    relabel_path = run_dir / RELABEL_FILENAME
    batch_client.write_label_shard_rows(relabel_path, relabeled_rows)
    relabeled_frame = _rows_to_frame(relabeled_rows, feature_ids)
    scores = score_self_consistency(sample, relabeled_frame, feature_ids)
    payload = {"sample_size": sample_size, "seed": seed, **scores}
    scores_path = run_dir / SCORES_FILENAME
    scores_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    mean_agreement = float(np.mean([v["agreement_rate"] for v in scores["per_feature"].values()]))
    print(
        f"self_consistency sample_size={sample_size} seed={seed} "
        f"batch_requests={len(tasks)} mean_agreement={mean_agreement:.2f}"
    )
    if scores["features_below_threshold"]:
        print(f"features_below_90pct={scores['features_below_threshold']}")
    print(f"Wrote {scores_path}")
    return scores_path


def main(argv: list[str] | None = None) -> None:
    """CLI entry for self-consistency Batch re-labeling."""
    parser = argparse.ArgumentParser(description="Self-consistency via Batch re-label.")
    parser.add_argument("--codebook", required=True)
    parser.add_argument("--label-matrix", required=True)
    parser.add_argument("--sample-size", type=int, default=constants.SELF_CONSISTENCY_SAMPLE)
    parser.add_argument("--seed", type=int, default=constants.DEFAULT_SEED)
    args = parser.parse_args(argv)
    run_self_consistency(
        Path(args.codebook),
        Path(args.label_matrix),
        args.sample_size,
        args.seed,
    )


def _tasks_for_sample(sample: pd.DataFrame) -> list[batch_client.LabelTask]:
    cohort = load_union_cohort().set_index("post_id")
    tasks: list[batch_client.LabelTask] = []
    for _, row in sample.iterrows():
        post_id = str(row["post_id"])
        surface = str(row["text_surface"])
        text = post_text_for_surface(cohort.loc[post_id], surface)
        tasks.append(batch_client.LabelTask(post_id=post_id, text_surface=surface, text=text))
    return tasks


def _rows_to_frame(rows: list[batch_client.LabelShardRow], feature_ids: list[str]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for row in rows:
        record: dict[str, Any] = {"post_id": row.post_id, "text_surface": row.text_surface}
        for feature_id in feature_ids:
            record[feature_id] = int(bool(row.labels.get(feature_id, False)))
        records.append(record)
    return pd.DataFrame(records)


if __name__ == "__main__":
    main()
