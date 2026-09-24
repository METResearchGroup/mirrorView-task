"""Compare Part 3 original topics with committed Part 2 assignments.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/compare_part2.py \\
      --topics-run-dir <part3 original topics run>
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

PART2_SOURCE_ASSIGNED = "assigned"
PART2_SOURCE_CENTROID = "centroid"
NOISE_TOPIC_ID = -1


def find_carryover_post_ids(part2_stimuli: pd.DataFrame, part3_posts: pd.DataFrame) -> set[str]:
    """Intersect Part 2 stimulus keys with Part 3 post ids."""
    part2_ids = set(part2_stimuli["post_primary_key"].astype(str).str.strip())
    part3_ids = set(part3_posts["post_id"].astype(str).str.strip())
    return part2_ids & part3_ids


def assign_part2_topics(carryover_ids: set[str], part2_assignments: pd.DataFrame) -> pd.DataFrame:
    """Mark carryover posts that already have a Part 2 topic as assigned."""
    assignments = part2_assignments.copy()
    assignments["post_id"] = assignments["message_id"].astype(str).str.strip()
    matched = assignments.loc[assignments["post_id"].isin(carryover_ids), ["post_id", "topic"]].copy()
    matched["part2_topic"] = matched["topic"].astype(int)
    matched["part2_topic_source"] = PART2_SOURCE_ASSIGNED
    return matched[["post_id", "part2_topic", "part2_topic_source"]].reset_index(drop=True)


def centroid_assign_part2_topic(post_embedding: np.ndarray, centroids: dict[int, np.ndarray]) -> dict:
    """Assign the topic whose L2-normalized centroid has the highest cosine."""
    post = np.asarray(post_embedding, dtype=np.float64)
    post = post / np.linalg.norm(post)
    best_topic = None
    best_score = -np.inf
    for topic, centroid in centroids.items():
        unit = np.asarray(centroid, dtype=np.float64)
        unit = unit / np.linalg.norm(unit)
        score = float(np.dot(post, unit))
        if score > best_score:
            best_topic = int(topic)
            best_score = score
    return {"part2_topic": best_topic, "part2_topic_source": PART2_SOURCE_CENTROID, "cosine": best_score}


def compute_topic_agreement(
    paired: pd.DataFrame,
    primary_only: bool,
) -> dict:
    """ARI and NMI between Part 2 and Part 3 topics.

    Parameters
    ----------
    paired
        Columns ``part2_topic``, ``part3_topic``, ``part2_topic_source``.
    primary_only
        When true, drop centroid-assigned rows.

    Returns
    -------
    dict
        ``ari``, ``nmi``, and ``n_posts``.
    """
    rows = paired
    if primary_only:
        rows = paired.loc[paired["part2_topic_source"] == PART2_SOURCE_ASSIGNED]
    part2 = rows["part2_topic"].astype(int).tolist()
    part3 = rows["part3_topic"].astype(int).tolist()
    if len(part2) < 2:
        return {"ari": float("nan"), "nmi": float("nan"), "n_posts": len(part2)}
    return {
        "ari": float(adjusted_rand_score(part2, part3)),
        "nmi": float(normalized_mutual_info_score(part2, part3)),
        "n_posts": len(part2),
    }
