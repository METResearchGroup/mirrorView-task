"""K-means clustering of kept-post features and removed-post features.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CLUSTER_ID_WIDTH,
    KMEANS_CLUSTERS_PER_SIDE,
    SEED,
    SIDE_KEPT,
    SIDE_REMOVED,
)
from shared.feature_discovery.llm_based.cluster import fit_kmeans

_SIDE_COUNT_COLUMNS = {
    SIDE_KEPT: "n_kept_side",
    SIDE_REMOVED: "n_removed_side",
}


def format_cluster_key(side: str, cluster_id: int) -> str:
    """Format a side and a size rank as a stable cluster key.

    Parameters
    ----------
    side
        ``kept`` or ``removed``.
    cluster_id
        Zero-based size rank within that side. Rank 0 is the largest group.

    Returns
    -------
    str
        Key such as ``kept_000`` or ``removed_014``.
    """
    return f"{side}_{cluster_id:0{CLUSTER_ID_WIDTH}d}"


def _ranked_labels(labels: np.ndarray) -> np.ndarray:
    """Renumber K-means labels so 0 is the largest group.

    Ties keep the smaller original label first.
    """
    counts = np.bincount(labels.astype(int))
    order = sorted(range(len(counts)), key=lambda index: (-int(counts[index]), index))
    remap = {old: new for new, old in enumerate(order)}
    return np.array([remap[int(label)] for label in labels], dtype=int)


def _side_frame(
    features: pd.DataFrame,
    matrix: np.ndarray,
    feature_ids: list[str],
    side: str,
) -> pd.DataFrame:
    """Cluster one side and return assignment rows in feature-id order."""
    count_column = _SIDE_COUNT_COLUMNS[side]
    by_id = features.set_index("feature_id", drop=False)
    selected = [
        feature_id
        for feature_id in feature_ids
        if int(by_id.loc[feature_id, count_column]) > 0
    ]
    if len(selected) < KMEANS_CLUSTERS_PER_SIDE:
        raise ValueError(
            f"{side} has {len(selected)} features, "
            f"fewer than {KMEANS_CLUSTERS_PER_SIDE} clusters"
        )
    row_of = {feature_id: index for index, feature_id in enumerate(feature_ids)}
    rows = [row_of[feature_id] for feature_id in selected]
    labels = fit_kmeans(matrix[rows], KMEANS_CLUSTERS_PER_SIDE, SEED)
    ranked = _ranked_labels(labels)
    return pd.DataFrame(
        {
            "side": side,
            "feature_id": selected,
            "cluster_id": ranked,
            "cluster_key": [format_cluster_key(side, int(label)) for label in ranked],
        }
    )


def assign_clusters(
    features: pd.DataFrame,
    matrix: np.ndarray,
    feature_ids: list[str],
) -> pd.DataFrame:
    """Assign each side's features to 15 K-means groups.

    A feature with counts on both sides appears twice, once per side.
    ``matrix`` rows must follow ``feature_ids``. Vectors are not scaled.

    Parameters
    ----------
    features
        Step 3 table with ``feature_id``, ``n_kept_side``, and ``n_removed_side``.
    matrix
        Embedding matrix aligned to ``feature_ids``.
    feature_ids
        Ordered feature ids matching ``embeddings.npy`` rows.

    Returns
    -------
    pandas.DataFrame
        Columns ``side``, ``feature_id``, ``cluster_id``, and ``cluster_key``.

    Raises
    ------
    ValueError
        When ``feature_ids`` does not match ``features.feature_id`` as a set,
        or a side has fewer features than the cluster count.
    """
    if set(feature_ids) != set(features["feature_id"]):
        raise ValueError("feature_ids does not match features.feature_id as a set")
    if len(feature_ids) != matrix.shape[0]:
        raise ValueError(
            f"feature_ids length {len(feature_ids)} != matrix rows {matrix.shape[0]}"
        )
    frames = [
        _side_frame(features, matrix, feature_ids, side)
        for side in (SIDE_KEPT, SIDE_REMOVED)
    ]
    return pd.concat(frames, ignore_index=True)


def summarize_clusters(
    assignments: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate member statistics for each side's clusters.

    Parameters
    ----------
    assignments
        Output of :func:`assign_clusters`.
    features
        Step 3 features table with occurrence and batch columns.

    Returns
    -------
    pandas.DataFrame
        One row per cluster with ``side``, ``cluster_key``, ``n_features``,
        ``n_occurrences``, ``n_batches``, ``n_kept_side``, and ``n_removed_side``,
        sorted by side and cluster key.
    """
    features_by_id = features.set_index("feature_id", drop=False)
    rows: list[dict[str, object]] = []
    grouped = assignments.groupby(["side", "cluster_key"], sort=True)
    for (side, cluster_key), group in grouped:
        member_ids = group["feature_id"].tolist()
        members = features_by_id.loc[member_ids]
        batch_union: set[str] = set()
        for batch_ids in members["batch_ids"]:
            batch_union.update(batch_ids)
        rows.append(
            {
                "side": side,
                "cluster_key": cluster_key,
                "n_features": len(member_ids),
                "n_occurrences": int(members["n_occurrences"].sum()),
                "n_batches": len(batch_union),
                "n_kept_side": int(members["n_kept_side"].sum()),
                "n_removed_side": int(members["n_removed_side"].sum()),
            }
        )
    result = pd.DataFrame.from_records(rows)
    return result.sort_values(["side", "cluster_key"]).reset_index(drop=True)
