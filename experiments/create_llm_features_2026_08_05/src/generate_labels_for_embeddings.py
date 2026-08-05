"""Stage 4: label HDBSCAN clusters with an LLM via research_tools runner.

Run from repo root::

    PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py \\
      --label-class keep \\
      --clusters-run-dir experiments/create_llm_features_2026_08_05/outputs/clusters/keep/<STAGE3_TS> \\
      --sample-per-cluster 8 \\
      --seed 42
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from experiments.create_llm_features_2026_08_05.src.paths import (
    LabelClass,
    latest_timestamp_subdir,
    stage3_root,
    stage4_root,
    validate_label_class,
)
from experiments.create_llm_features_2026_08_05.src.prompts import (
    build_cluster_label_messages,
)
from experiments.create_llm_features_2026_08_05.src.schemas import ClusterLabelResult
from research_tools.llm.runner import run

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_SAMPLE_PER_CLUSTER = 8
DEFAULT_SEED = 42
_METADATA_FILENAME = "metadata.json"
ASSIGNMENTS_HDBSCAN_FILENAME = "assignments_hdbscan.json"
NOISE_CLUSTER_ID = -1


def prompt_fn(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one HDBSCAN cluster labeling item."""
    return build_cluster_label_messages(item)


def writer_map_fn(item: dict[str, Any], result: ClusterLabelResult) -> dict[str, Any]:
    """Map one cluster item and structured result to a JSON-serializable row."""
    return {
        "cluster_id": item["cluster_id"],
        "label_class": item["label_class"],
        "n_members": item["n_members"],
        "sampled_feature_ids": [
            feature["feature_id"] for feature in item["sampled_features"]
        ],
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[[dict[str, Any], ClusterLabelResult], dict[str, Any]],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], ClusterLabelResult], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(item: dict[str, Any], result: ClusterLabelResult) -> dict[str, Any]:
        row = base_writer(item, result)
        progress_bar.update(1)
        return row

    return wrapped


def resolve_clusters_run_dir(
    label_class: str,
    clusters_run_dir: str | None,
) -> Path:
    """Resolve Stage-3 run directory from an explicit path or the latest timestamp."""
    if clusters_run_dir:
        path = Path(clusters_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"clusters-run-dir not found: {path}")
        return path
    return latest_timestamp_subdir(stage3_root(label_class))


def load_hdbscan_assignments(clusters_run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load HDBSCAN assignments and Stage-3 metadata.

    Parameters
    ----------
    clusters_run_dir
        Stage-3 timestamped run directory.

    Returns
    -------
    tuple[list[dict[str, Any]], dict[str, Any]]
        Assignment rows and metadata dict.

    Raises
    ------
    FileNotFoundError
        When assignments_hdbscan.json is missing.
    ValueError
        When metadata claims a non-HDBSCAN downstream method.
    """
    assignments_path = clusters_run_dir / ASSIGNMENTS_HDBSCAN_FILENAME
    if not assignments_path.is_file():
        raise FileNotFoundError(
            f"Missing {ASSIGNMENTS_HDBSCAN_FILENAME} in {clusters_run_dir}. "
            "Do not fall back to KMeans assignments."
        )
    assignments = json.loads(assignments_path.read_text(encoding="utf-8"))
    metadata_path = clusters_run_dir / _METADATA_FILENAME
    metadata: dict[str, Any] = {}
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        downstream = metadata.get("downstream_method")
        if downstream is not None and downstream != "hdbscan":
            raise ValueError(
                f"Expected downstream_method='hdbscan', got {downstream!r}"
            )
    return assignments, metadata


def _member_feature_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Project an assignment row to the sampled-feature payload for prompts."""
    return {
        "feature_id": row["feature_id"],
        "message_id": row["message_id"],
        "feature_name": row["feature_name"],
        "feature_value": row["feature_value"],
        "category": str(row.get("category") or ""),
        "rationale": str(row.get("rationale") or ""),
        "evidence_span": row.get("evidence_span"),
    }


def build_cluster_label_items(
    assignments: list[dict[str, Any]],
    label_class: str,
    sample_per_cluster: int,
    seed: int,
) -> tuple[list[dict[str, Any]], int]:
    """Build one runner item per non-noise HDBSCAN cluster.

    Parameters
    ----------
    assignments
        HDBSCAN assignment rows.
    label_class
        keep or remove.
    sample_per_cluster
        Max members sampled per cluster.
    seed
        Base RNG seed; salted with cluster_id.

    Returns
    -------
    tuple[list[dict[str, Any]], int]
        Runner items and count of noise rows skipped.
    """
    if sample_per_cluster <= 0:
        raise ValueError(f"sample_per_cluster must be positive, got {sample_per_cluster}")

    by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    n_noise_skipped = 0
    for row in assignments:
        cluster_id = int(row["cluster_id"])
        if cluster_id == NOISE_CLUSTER_ID:
            n_noise_skipped += 1
            continue
        by_cluster[cluster_id].append(row)

    items: list[dict[str, Any]] = []
    for cluster_id in sorted(by_cluster):
        members = by_cluster[cluster_id]
        rng = np.random.default_rng(seed + int(cluster_id))
        n_sample = min(sample_per_cluster, len(members))
        indices = rng.choice(len(members), size=n_sample, replace=False)
        sampled = [_member_feature_payload(members[int(i)]) for i in indices]
        items.append(
            {
                "cluster_id": int(cluster_id),
                "label_class": label_class,
                "n_members": len(members),
                "sampled_features": sampled,
            }
        )
    return items, n_noise_skipped


def run_cluster_labeling(
    items: list[dict[str, Any]],
    label_class: str,
    source_clusters_run_dir: Path,
    sample_per_cluster: int,
    seed: int,
    n_noise_skipped: int,
    model: str,
) -> Any:
    """Run LLM labeling for each HDBSCAN cluster and return the output path."""
    if not items:
        raise ValueError(
            "No non-noise HDBSCAN clusters to label. "
            f"n_noise_skipped={n_noise_skipped}"
        )

    progress_bar = tqdm(
        total=len(items),
        desc=f"Stage 4 labels ({label_class})",
    )
    try:
        return run(
            items,
            prompt_fn=prompt_fn,
            response_model=ClusterLabelResult,
            model=model,
            output_base_path=stage4_root(label_class),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "stage": "cluster_labeling",
                "label_class": label_class,
                "source_clusters_run_dir": str(source_clusters_run_dir),
                "clustering_method": "hdbscan",
                "sample_per_cluster": sample_per_cluster,
                "seed": seed,
                "model": model,
                "cluster_ids": [item["cluster_id"] for item in items],
                "n_noise_skipped": n_noise_skipped,
            },
        )
    finally:
        progress_bar.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 4."""
    parser = argparse.ArgumentParser(
        description="Label HDBSCAN feature clusters with gpt-5.4-nano (not KMeans)."
    )
    parser.add_argument(
        "--label-class",
        required=True,
        choices=[LabelClass.KEEP.value, LabelClass.REMOVE.value],
    )
    parser.add_argument(
        "--clusters-run-dir",
        default=None,
        help="Stage-3 run dir; defaults to latest under stage3_root/.",
    )
    parser.add_argument(
        "--sample-per-cluster",
        type=int,
        default=DEFAULT_SAMPLE_PER_CLUSTER,
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: label HDBSCAN clusters for one label class."""
    args = parse_args(argv)
    label_class = validate_label_class(args.label_class).value
    clusters_run_dir = resolve_clusters_run_dir(label_class, args.clusters_run_dir)
    assignments, _metadata = load_hdbscan_assignments(clusters_run_dir)
    items, n_noise_skipped = build_cluster_label_items(
        assignments,
        label_class,
        args.sample_per_cluster,
        args.seed,
    )
    print(
        f"label_class={label_class} clusters={len(items)} "
        f"n_noise_skipped={n_noise_skipped} "
        f"source={clusters_run_dir}"
    )
    output_dir = run_cluster_labeling(
        items,
        label_class,
        clusters_run_dir,
        args.sample_per_cluster,
        args.seed,
        n_noise_skipped,
        args.model,
    )
    print(f"Wrote Stage-4 labels to {output_dir}")


if __name__ == "__main__":
    main()
