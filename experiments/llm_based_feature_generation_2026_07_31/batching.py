"""Load shared Part 2 modal keep/remove labels and form batches."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

FROZEN_SUBSET_CSV = Path(__file__).resolve().parent / "data" / "sampled_subset.csv"
PRODUCTION_SAMPLE_FRACTION = 0.50


def load_posts() -> pd.DataFrame:
    """Load shared modal keep/remove labels (one row per post)."""
    return load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)


def sample_posts(
    posts: pd.DataFrame,
    *,
    fraction: float,
    seed: int,
    exclude_ids: set[str] | None = None,
) -> pd.DataFrame:
    """Sample a fraction of posts without replacement, stratified by decision."""
    if not 0 < fraction <= 1:
        raise ValueError(f"fraction must be in (0, 1], got {fraction}")

    frame = posts.copy()
    if exclude_ids:
        frame = frame[~frame["message_id"].isin(exclude_ids)].copy()

    sampled_parts: list[pd.DataFrame] = []
    for decision in ("keep", "remove"):
        class_rows = frame[frame["decision"] == decision]
        if class_rows.empty:
            continue
        sample_size = min(len(class_rows), math.ceil(len(class_rows) * fraction))
        sampled_parts.append(class_rows.sample(n=sample_size, random_state=seed))

    if not sampled_parts:
        return frame.iloc[0:0].copy()

    return (
        pd.concat(sampled_parts, ignore_index=True)
        .sample(frac=1, random_state=seed)
        .reset_index(drop=True)
    )


def load_or_create_frozen_subset(
    posts: pd.DataFrame,
    *,
    fraction: float = PRODUCTION_SAMPLE_FRACTION,
    seed: int,
    subset_path: Path = FROZEN_SUBSET_CSV,
) -> tuple[pd.DataFrame, bool]:
    """Load the frozen production subset CSV, or create it on first 50% run."""
    if subset_path.is_file():
        loaded = pd.read_csv(subset_path, low_memory=False)
        required = {"message_id", "original_text", "mirror_text", "decision"}
        missing = required - set(loaded.columns)
        if missing:
            raise KeyError(f"Frozen subset missing columns: {sorted(missing)}")
        return loaded[list(required)].reset_index(drop=True), False

    sampled = sample_posts(posts, fraction=fraction, seed=seed)
    subset_path.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(subset_path, index=False)
    return sampled, True


def resolve_production_sample(
    posts: pd.DataFrame,
    *,
    sample_fraction: float,
    seed: int,
    exclude_ids: set[str] | None = None,
) -> tuple[pd.DataFrame, str]:
    """Return the sampled frame and a short description of how it was chosen."""
    if math.isclose(sample_fraction, PRODUCTION_SAMPLE_FRACTION):
        if exclude_ids:
            raise ValueError(
                "--exclude-ids-from is not supported with the frozen 50% production subset."
            )
        sampled, created = load_or_create_frozen_subset(posts, seed=seed)
        source = "created frozen subset" if created else "loaded frozen subset"
        return sampled, source

    sampled = sample_posts(
        posts,
        fraction=sample_fraction,
        seed=seed,
        exclude_ids=exclude_ids,
    )
    return sampled, f"live sample fraction={sample_fraction}"


def form_batches(
    sample: pd.DataFrame,
    *,
    keep_per_batch: int = 10,
    remove_per_batch: int = 10,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    """Form mixed keep/remove batches with unique message ids across batches."""
    if keep_per_batch <= 0 or remove_per_batch <= 0:
        raise ValueError("keep_per_batch and remove_per_batch must be positive")

    keep_rows = sample[sample["decision"] == "keep"].reset_index(drop=True)
    remove_rows = sample[sample["decision"] == "remove"].reset_index(drop=True)

    batch_count = min(len(keep_rows) // keep_per_batch, len(remove_rows) // remove_per_batch)
    if batch_count == 0:
        raise ValueError(
            "Cannot form any full batches from the sample. "
            f"keep rows={len(keep_rows)}, remove rows={len(remove_rows)}, "
            f"requested keep_per_batch={keep_per_batch}, remove_per_batch={remove_per_batch}."
        )

    batches: list[dict[str, Any]] = []
    keep_offset = 0
    remove_offset = 0
    for batch_id in range(batch_count):
        keep_slice = keep_rows.iloc[keep_offset : keep_offset + keep_per_batch]
        remove_slice = remove_rows.iloc[remove_offset : remove_offset + remove_per_batch]
        keep_offset += keep_per_batch
        remove_offset += remove_per_batch

        keep_posts = keep_slice.to_dict(orient="records")
        remove_posts = remove_slice.to_dict(orient="records")
        message_ids = sorted(
            [str(post["message_id"]) for post in keep_posts + remove_posts]
        )
        batches.append(
            {
                "batch_id": batch_id,
                "message_ids": message_ids,
                "keep_posts": keep_posts,
                "remove_posts": remove_posts,
            }
        )

    leftover = pd.concat(
        [
            keep_rows.iloc[keep_offset:],
            remove_rows.iloc[remove_offset:],
        ],
        ignore_index=True,
    )
    return batches, leftover


if __name__ == "__main__":
    posts_frame = load_posts()
    sampled = sample_posts(posts_frame, fraction=0.50, seed=42)
    batch_list, leftover_rows = form_batches(sampled, keep_per_batch=10, remove_per_batch=10)
    all_ids = [message_id for batch in batch_list for message_id in batch["message_ids"]]
    assert len(all_ids) == len(set(all_ids)), "duplicate message_id across batches"
    print(
        "posts",
        len(posts_frame),
        "sample",
        len(sampled),
        "batches",
        len(batch_list),
        "leftover",
        len(leftover_rows),
    )
