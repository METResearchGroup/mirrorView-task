"""Discovery batch formation for mixed and single-class LLM runs.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batching
    print(batching.DEFAULT_KEEP_PER_BATCH)
    "
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths

DEFAULT_KEEP_PER_BATCH = 10
DEFAULT_REMOVE_PER_BATCH = 10
DEFAULT_KEEP_SAMPLE_SIZE = 500
DEFAULT_REMOVE_SAMPLE_SIZE = 500
DEFAULT_POSTS_PER_BATCH = 10


def load_discovery_cohort(arm: str) -> pd.DataFrame:
    """Load discovery-split rows from the latest cohort parquet for one arm.

    Parameters
    ----------
    arm
        Text arm whose cohort parquet should be read.

    Returns
    -------
    pd.DataFrame
        Rows with ``split == discovery`` only.
    """
    cohort = _load_cohort_frame(arm)
    return cohort.loc[cohort["split"] == constants.DISCOVERY_SPLIT].copy()


def form_mixed_batches(
    cohort: pd.DataFrame,
    *,
    keep_per_batch: int = DEFAULT_KEEP_PER_BATCH,
    remove_per_batch: int = DEFAULT_REMOVE_PER_BATCH,
) -> list[dict[str, Any]]:
    """Form mixed keep/remove batches with unique message ids across batches.

    Parameters
    ----------
    cohort
        Discovery cohort rows with ``modal_decision`` and text columns.
    keep_per_batch
        Number of keep posts per batch.
    remove_per_batch
        Number of remove posts per batch.

    Returns
    -------
    list[dict[str, Any]]
        Batch dicts with keep and remove post lists.

    Raises
    ------
    ValueError
        When batch sizes are invalid or no full batch can be formed.
    """
    if keep_per_batch <= 0 or remove_per_batch <= 0:
        raise ValueError("keep_per_batch and remove_per_batch must be positive")
    keep_rows = _class_rows(cohort, constants.DECISION_KEEP).reset_index(drop=True)
    remove_rows = _class_rows(cohort, constants.DECISION_REMOVE).reset_index(drop=True)
    batch_count = min(len(keep_rows) // keep_per_batch, len(remove_rows) // remove_per_batch)
    if batch_count == 0:
        raise ValueError(
            "Cannot form any full batches from the cohort. "
            f"keep rows={len(keep_rows)}, remove rows={len(remove_rows)}."
        )
    return _build_mixed_batches(keep_rows, remove_rows, keep_per_batch, remove_per_batch, batch_count)


def form_single_class_batches(
    cohort: pd.DataFrame,
    *,
    keep_sample_size: int = DEFAULT_KEEP_SAMPLE_SIZE,
    remove_sample_size: int = DEFAULT_REMOVE_SAMPLE_SIZE,
    posts_per_batch: int = DEFAULT_POSTS_PER_BATCH,
    seed: int,
) -> list[dict[str, Any]]:
    """Sample keep and remove posts and form single-class batches.

    Parameters
    ----------
    cohort
        Discovery cohort rows.
    keep_sample_size
        Number of keep posts to sample.
    remove_sample_size
        Number of remove posts to sample.
    posts_per_batch
        Posts per batch for each label class.
    seed
        RNG seed for sampling.

    Returns
    -------
    list[dict[str, Any]]
        Keep batches followed by remove batches.
    """
    if posts_per_batch <= 0:
        raise ValueError("posts_per_batch must be positive")
    keep_sample = _sample_class_rows(cohort, constants.DECISION_KEEP, keep_sample_size, seed)
    remove_sample = _sample_class_rows(
        cohort,
        constants.DECISION_REMOVE,
        remove_sample_size,
        seed + 1,
    )
    keep_batches = _form_class_batches(keep_sample, constants.DECISION_KEEP, posts_per_batch)
    remove_batches = _form_class_batches(remove_sample, constants.DECISION_REMOVE, posts_per_batch)
    return keep_batches + remove_batches


def _load_cohort_frame(arm: str) -> pd.DataFrame:
    cohort_run_dir = paths.latest_timestamp_subdir(paths.cohort_dir(arm))
    cohort_path = cohort_run_dir / constants.COHORT_FILENAME
    if not cohort_path.is_file():
        raise FileNotFoundError(f"Missing cohort parquet: {cohort_path}")
    return pd.read_parquet(cohort_path)


def _class_rows(cohort: pd.DataFrame, label_class: str) -> pd.DataFrame:
    return cohort.loc[cohort["modal_decision"] == label_class].copy()


def _row_to_post(row: pd.Series) -> dict[str, str]:
    return {
        "message_id": str(row["post_id"]),
        "original_text": str(row["original_text"]),
        "mirror_text": str(row["mirror_text"]),
    }


def _build_mixed_batches(
    keep_rows: pd.DataFrame,
    remove_rows: pd.DataFrame,
    keep_per_batch: int,
    remove_per_batch: int,
    batch_count: int,
) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    keep_offset = 0
    remove_offset = 0
    for batch_id in range(batch_count):
        keep_slice = keep_rows.iloc[keep_offset : keep_offset + keep_per_batch]
        remove_slice = remove_rows.iloc[remove_offset : remove_offset + remove_per_batch]
        keep_offset += keep_per_batch
        remove_offset += remove_per_batch
        keep_posts = [_row_to_post(row) for _, row in keep_slice.iterrows()]
        remove_posts = [_row_to_post(row) for _, row in remove_slice.iterrows()]
        message_ids = sorted(post["message_id"] for post in keep_posts + remove_posts)
        batches.append(
            {
                "batch_id": batch_id,
                "message_ids": message_ids,
                "keep_posts": keep_posts,
                "remove_posts": remove_posts,
            }
        )
    return batches


def _sample_class_rows(
    cohort: pd.DataFrame,
    label_class: str,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    class_rows = _class_rows(cohort, label_class)
    if class_rows.empty:
        raise ValueError(f"No rows available for label class {label_class}")
    n_take = min(sample_size, len(class_rows))
    return class_rows.sample(n=n_take, random_state=seed).reset_index(drop=True)


def _form_class_batches(
    sample: pd.DataFrame,
    label_class: str,
    posts_per_batch: int,
) -> list[dict[str, Any]]:
    batch_count = len(sample) // posts_per_batch
    if batch_count == 0:
        raise ValueError(
            f"Cannot form any full batches for {label_class}. "
            f"rows={len(sample)}, posts_per_batch={posts_per_batch}."
        )
    batches: list[dict[str, Any]] = []
    for batch_id in range(batch_count):
        start = batch_id * posts_per_batch
        end = start + posts_per_batch
        posts = [_row_to_post(row) for _, row in sample.iloc[start:end].iterrows()]
        batches.append(
            {
                "batch_id": batch_id,
                "label_class": label_class,
                "message_ids": sorted(post["message_id"] for post in posts),
                "posts": posts,
            }
        )
    return batches
