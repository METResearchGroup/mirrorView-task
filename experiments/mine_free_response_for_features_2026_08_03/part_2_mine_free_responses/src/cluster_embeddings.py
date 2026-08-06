"""Stage 3: dual HDBSCAN + KMeans clustering via shared feature_discovery helpers.

Run from repo root::

    PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/cluster_embeddings.py \\
      --likert-group low \\
      --embeddings-run-dir experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/outputs/generated_embeddings/low/<STAGE2_TS> \\
      --seed 42
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.paths import (
    LikertGroup,
    latest_timestamp_subdir,
    stage2_root,
    stage3_root,
    validate_likert_group,
)
from shared.feature_discovery.llm_based.cluster import (
    DEFAULT_MIN_CLUSTER_SIZE,
    DEFAULT_SEED,
    run_dual_clustering,
)
from shared.feature_discovery.llm_based.paths import make_run_timestamp


def resolve_embeddings_run_dir(
    likert_group: str,
    embeddings_run_dir: str | None,
) -> Path:
    """Resolve Stage-2 run directory from an explicit path or the latest timestamp."""
    if embeddings_run_dir:
        path = Path(embeddings_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"embeddings-run-dir not found: {path}")
        return path
    return latest_timestamp_subdir(stage2_root(likert_group))


def run_cluster_embeddings(
    likert_group: str,
    embeddings_run_dir: str | None,
    seed: int,
    min_cluster_size: int,
) -> Path:
    """Cluster Stage-2 embeddings with HDBSCAN and KMeans for one Likert group.

    Parameters
    ----------
    likert_group
        low or high.
    embeddings_run_dir
        Explicit Stage-2 directory or None for latest.
    seed
        RNG seed for KMeans / silhouette / PCA.
    min_cluster_size
        Preferred HDBSCAN min_cluster_size (may be lowered for tiny n).

    Returns
    -------
    Path
        Stage-3 run directory.
    """
    validate_likert_group(likert_group)
    source_dir = resolve_embeddings_run_dir(likert_group, embeddings_run_dir)
    class_root = stage3_root(likert_group)
    return run_dual_clustering(
        embeddings_run_dir=source_dir,
        cluster_output_root=class_root,
        class_png_dir=class_root,
        label_class=likert_group,
        run_timestamp=make_run_timestamp(),
        seed=seed,
        min_cluster_size=min_cluster_size,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 3."""
    parser = argparse.ArgumentParser(
        description=(
            "Cluster free-response feature embeddings with HDBSCAN "
            "(downstream) and KMeans (comparison)."
        )
    )
    parser.add_argument(
        "--likert-group",
        required=True,
        choices=[LikertGroup.LOW.value, LikertGroup.HIGH.value],
    )
    parser.add_argument(
        "--embeddings-run-dir",
        default=None,
        help="Stage-2 run dir; defaults to latest under stage2_root/.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=DEFAULT_MIN_CLUSTER_SIZE,
        help="Preferred HDBSCAN min_cluster_size (auto-lowered for tiny smoke n).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: dual-cluster Stage-2 embeddings for one Likert group."""
    args = parse_args(argv)
    out_dir = run_cluster_embeddings(
        args.likert_group,
        args.embeddings_run_dir,
        args.seed,
        args.min_cluster_size,
    )
    print(f"Wrote Stage-3 clusters to {out_dir}")


if __name__ == "__main__":
    main()
