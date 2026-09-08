"""Count political stance by LLM toxicity tier, overall and by platform."""

from __future__ import annotations

import pandas as pd


def stance_by_toxicity(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Return left/right counts by low, medium, and high toxicity.

    Parameters
    ----------
    frame
        Combined table with ``political_stance`` and ``llm_toxicity_tier``.

    Returns
    -------
    dict[str, dict[str, int]]
        Counts keyed by stance, then by toxicity tier. Missing cells are 0.
    """
    raise NotImplementedError


def stance_by_toxicity_by_integration(
    frame: pd.DataFrame,
) -> dict[str, dict[str, dict[str, int]]]:
    """Return stance by toxicity counts grouped by platform.

    Parameters
    ----------
    frame
        Combined table with ``integration``, ``political_stance``, and
        ``llm_toxicity_tier``.

    Returns
    -------
    dict[str, dict[str, dict[str, int]]]
        Counts keyed by platform, then stance, then toxicity tier.
    """
    raise NotImplementedError
