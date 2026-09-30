"""Prompts and centroid samples for cluster naming."""

from __future__ import annotations

import numpy as np
import pandas as pd
from data_platform.generate_features.models import LabelTask

SYSTEM_PROMPT = """You are a computational linguistics analyst. A model read social-media post pairs from a keep/remove moderation task. Each pair is an original post and a mirror post that makes the same point from the opposite political side. The model listed features that set the kept pairs apart from the removed pairs, and similar features were then grouped into clusters.

You will see a sample of the features in one cluster.

Return a name for the cluster of at most eight words, and a definition of the cluster in one sentence. The name and the definition should describe what the features have in common, so that a reader can decide whether a new post pair has the feature.

Return as structured output."""

USER_TEMPLATE = """## Features in the cluster

{feature_bullets}

Return the name and the definition."""


def sample_cluster_features(
    assignments: pd.DataFrame,
    features: pd.DataFrame,
    matrix: np.ndarray,
    feature_ids: list[str],
    sample_size: int,
) -> dict[str, list[str]]:
    """Return the feature texts closest to each cluster centroid.

    Parameters
    ----------
    assignments
        Step 4 rows with ``cluster_key`` and ``feature_id``.
    features
        Step 3 table with ``feature_id`` and ``text``.
    matrix
        Embedding matrix aligned to ``feature_ids``.
    feature_ids
        Row order of ``matrix``.
    sample_size
        Maximum texts per cluster. Smaller clusters return every member.

    Returns
    -------
    dict[str, list[str]]
        Cluster key to texts, closest first. Equal distances break by ``feature_id``.

    Raises
    ------
    ValueError
        When a member id is missing or the matrix row count disagrees.
    """
    if len(feature_ids) != matrix.shape[0]:
        raise ValueError(
            f"feature_ids length {len(feature_ids)} != matrix rows {matrix.shape[0]}"
        )
    if sample_size <= 0:
        raise ValueError(f"sample_size must be positive, got {sample_size}")
    row_of = {feature_id: index for index, feature_id in enumerate(feature_ids)}
    text_of = features.set_index("feature_id")["text"]
    samples: dict[str, list[str]] = {}
    grouped = assignments.groupby("cluster_key", sort=True)
    for cluster_key, group in grouped:
        member_ids = group["feature_id"].tolist()
        missing = [feature_id for feature_id in member_ids if feature_id not in row_of]
        if missing:
            raise ValueError(f"feature id missing from feature_ids: {missing[0]}")
        rows = np.array([row_of[feature_id] for feature_id in member_ids])
        vectors = matrix[rows]
        centroid = vectors.mean(axis=0)
        distances = np.linalg.norm(vectors - centroid, axis=1)
        order = sorted(
            range(len(member_ids)),
            key=lambda index: (float(distances[index]), member_ids[index]),
        )
        chosen = order[:sample_size]
        samples[str(cluster_key)] = [str(text_of.loc[member_ids[index]]) for index in chosen]
    return samples


def render_cluster_prompt(feature_texts: list[str]) -> str:
    """Fill the user prompt with one bullet per feature text.

    Parameters
    ----------
    feature_texts
        Texts in closest-first order.

    Returns
    -------
    str
        User message for one cluster.
    """
    bullets = "\n".join(f"- {text}" for text in feature_texts)
    return USER_TEMPLATE.replace("{feature_bullets}", bullets)


def build_naming_tasks(
    samples: dict[str, list[str]],
    sizes: pd.DataFrame,
) -> list[LabelTask]:
    """Build one naming task per cluster, in cluster-key order.

    Parameters
    ----------
    samples
        Cluster key to closest feature texts.
    sizes
        Step 4 size table. Its ``cluster_key`` values set the task order.

    Returns
    -------
    list[LabelTask]
        Tasks whose ``uri`` is the cluster key.

    Raises
    ------
    ValueError
        When a size-table cluster has no sample.
    """
    order = sizes.sort_values("cluster_key")["cluster_key"].tolist()
    tasks: list[LabelTask] = []
    for cluster_key in order:
        texts = samples.get(str(cluster_key))
        if texts is None:
            raise ValueError(f"missing sample for {cluster_key}")
        tasks.append(LabelTask(uri=str(cluster_key), text=render_cluster_prompt(texts)))
    return tasks
