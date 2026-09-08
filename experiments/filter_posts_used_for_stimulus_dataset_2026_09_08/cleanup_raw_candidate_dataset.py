"""Drop previously used posts, duplicate ids, and duplicate text."""

from __future__ import annotations

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CleanupSummary,
)


def cleanup_raw_candidate_dataset(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, CleanupSummary]:
    """Return the cleaned table and drop-count summary."""
    raise NotImplementedError
