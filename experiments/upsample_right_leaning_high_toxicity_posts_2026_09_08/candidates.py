"""Build leftover right-medium Perspective candidates."""

from __future__ import annotations

import pandas as pd

from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    CandidateBuildResult,
)


def build_perspective_candidates(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
    medium_upsample: pd.DataFrame,
    pr260_source_record_ids: set[str],
) -> CandidateBuildResult:
    """Return leftover right-medium rows that may be scored and promoted.

    Parameters
    ----------
    cleaned
        Cleaned combined table.
    sample
        The 10,200 post sample.
    medium_upsample
        The 2,000 unused medium posts.
    pr260_source_record_ids
        Pull request 260 promotion ``source_record_id`` values.

    Returns
    -------
    CandidateBuildResult
        Candidate rows and drop counts.

    Raises
    ------
    ValueError
        When fewer than 300 candidates remain.
    """
    raise NotImplementedError
