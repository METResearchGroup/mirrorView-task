"""HDBSCAN clustering and assignment helpers for step 4.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step4_cluster_records/run.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CLUSTER_ID_WIDTH,
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_NOISE_LABEL,
)
from shared.feature_discovery.llm_based.cluster import fit_hdbscan, resolve_hdbscan_params


def format_cluster_key(cluster_id: int) -> str:
    """Format a numeric cluster id as a stable string key.

    Parameters
    ----------
    cluster_id
        Non-negative HDBSCAN cluster label.

    Returns
    -------
    str
        Key ``cluster_NNN`` with zero-padded width from ``CLUSTER_ID_WIDTH``.
    """
    return f"cluster_{cluster_id:0{CLUSTER_ID_WIDTH}d}"


def cluster_features(
    matrix: np.ndarray,
    min_cluster_size: int,
) -> tuple[np.ndarray, dict]:
    """Run HDBSCAN on the embedding matrix.

    Resolves ``min_cluster_size`` and ``min_samples`` for the row count, then
    fits HDBSCAN on the raw vectors (no scaling).

    Parameters
    ----------
    matrix
        Embedding matrix with shape ``(n_features, n_dims)``.
    min_cluster_size
        Requested HDBSCAN ``min_cluster_size`` (typically 5).

    Returns
    -------
    tuple[numpy.ndarray, dict]
        Per-row cluster labels and the params metadata dict from ``fit_hdbscan``.

    Raises
    ------
    ValueError
        When ``matrix`` has fewer than two rows.
    """
    n_features = matrix.shape[0]
    if n_features < 2:
        raise ValueError(f"Need at least 2 features to cluster, got {n_features}")
    effective_size, min_samples, _ = resolve_hdbscan_params(
        n_features, min_cluster_size
    )
    return fit_hdbscan(matrix, effective_size, min_samples)


def assign_clusters(
    features: pd.DataFrame,
    matrix: np.ndarray,
    feature_ids: list[str],
) -> tuple[pd.DataFrame, dict]:
    """Cluster features and build per-feature assignment rows.

    ``matrix`` rows must align with ``feature_ids`` order. Noise label ``-1``
    yields a null ``cluster_key``.

    Parameters
    ----------
    features
        Step 3 features table with a ``feature_id`` column.
    matrix
        Embedding matrix aligned to ``feature_ids``.
    feature_ids
        Ordered feature ids matching ``embeddings.npy`` rows.

    Returns
    -------
    tuple[pandas.DataFrame, dict]
        Assignments with ``feature_id``, ``cluster_id``, and ``cluster_key``,
        plus the HDBSCAN params dict from the single run.

    Raises
    ------
    ValueError
        When ``feature_ids`` does not match ``features.feature_id`` as a set,
        or row counts disagree.
    """
    if set(feature_ids) != set(features["feature_id"]):
        raise ValueError("feature_ids does not match features.feature_id as a set")
    if len(feature_ids) != matrix.shape[0]:
        raise ValueError(
            f"feature_ids length {len(feature_ids)} != matrix rows {matrix.shape[0]}"
        )

    labels, params = cluster_features(matrix, HDBSCAN_MIN_CLUSTER_SIZE)

    cluster_keys = [
        format_cluster_key(int(label))
        if int(label) != HDBSCAN_NOISE_LABEL
        else None
        for label in labels
    ]
    assignments = pd.DataFrame(
        {
            "feature_id": feature_ids,
            "cluster_id": labels.astype(int),
            "cluster_key": cluster_keys,
        }
    )
    return assignments, params


def summarize_clusters(
    assignments: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate member statistics for each non-noise cluster.

    Parameters
    ----------
    assignments
        Output of :func:`assign_clusters`.
    features
        Step 3 features table with occurrence and batch columns.

    Returns
    -------
    pandas.DataFrame
        One row per cluster with ``cluster_key``, ``n_features``,
        ``n_occurrences``, ``n_batches``, ``n_kept_side``, and ``n_removed_side``,
        sorted by ``cluster_key``.
    """
    non_noise = assignments[assignments["cluster_id"] != HDBSCAN_NOISE_LABEL]
    features_by_id = features.set_index("feature_id", drop=False)

    rows: list[dict[str, object]] = []
    for cluster_key, group in non_noise.groupby("cluster_key", sort=True):
        member_ids = group["feature_id"].tolist()
        members = features_by_id.loc[member_ids]
        batch_union: set[str] = set()
        for batch_ids in members["batch_ids"]:
            batch_union.update(batch_ids)
        rows.append(
            {
                "cluster_key": cluster_key,
                "n_features": len(member_ids),
                "n_occurrences": int(members["n_occurrences"].sum()),
                "n_batches": len(batch_union),
                "n_kept_side": int(members["n_kept_side"].sum()),
                "n_removed_side": int(members["n_removed_side"].sum()),
            }
        )
    result = pd.DataFrame.from_records(rows)
    if result.empty:
        return result
    return result.sort_values("cluster_key").reset_index(drop=True)
