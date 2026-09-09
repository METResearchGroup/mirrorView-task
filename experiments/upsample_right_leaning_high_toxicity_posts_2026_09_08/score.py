"""Score leftover right-medium posts with the Perspective thread-pool engine."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.engines.base import BatchExecutionEngine


def score_candidates(
    candidates: pd.DataFrame,
    *,
    scores_path: Path,
    engine: BatchExecutionEngine | None = None,
) -> pd.DataFrame:
    """Score candidates with Perspective and persist ``record_id`` probabilities.

    Parameters
    ----------
    candidates
        Leftover right-medium rows.
    scores_path
        Parquet path for ``record_id`` and ``toxicity_prob``. Existing finite
        probabilities in ``[0, 1]`` are skipped.
    engine
        Batch engine used to label pending rows. None builds the product
        ``is_toxic_tiered`` thread-pool engine.

    Returns
    -------
    pd.DataFrame
        Scores for every candidate id.

    Raises
    ------
    ValueError
        When any candidate still lacks a finite toxicity probability.
    """
    raise NotImplementedError
