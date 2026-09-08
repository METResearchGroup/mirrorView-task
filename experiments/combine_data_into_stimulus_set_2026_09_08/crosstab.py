"""Count political stance by LLM toxicity tier, overall and by platform."""

from __future__ import annotations

import pandas as pd

from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    INTEGRATION_CROSSTAB_ORDER,
    STANCE_CROSSTAB_ROWS,
    TOXICITY_CROSSTAB_COLUMNS,
)

INTEGRATION_COLUMN = "integration"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"


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
    grouped = frame.groupby([STANCE_COLUMN, TOXICITY_COLUMN], dropna=False).size()
    return _fill_stance_counts(grouped)


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
    grouped = frame.groupby(
        [INTEGRATION_COLUMN, STANCE_COLUMN, TOXICITY_COLUMN],
        dropna=False,
    ).size()
    return _fill_integration_counts(grouped)


def _empty_stance_counts() -> dict[str, dict[str, int]]:
    return {
        stance: {tier: 0 for tier in TOXICITY_CROSSTAB_COLUMNS}
        for stance in STANCE_CROSSTAB_ROWS
    }


def _fill_stance_counts(grouped: pd.Series) -> dict[str, dict[str, int]]:
    counts = _empty_stance_counts()
    for (stance, tier), row_count in grouped.items():
        counts.setdefault(str(stance), {})
        counts[str(stance)][str(tier)] = int(row_count)
    return counts


def _fill_integration_counts(
    grouped: pd.Series,
) -> dict[str, dict[str, dict[str, int]]]:
    counts = {
        integration: _empty_stance_counts() for integration in INTEGRATION_CROSSTAB_ORDER
    }
    for (integration, stance, tier), row_count in grouped.items():
        platform = str(integration)
        counts.setdefault(platform, _empty_stance_counts())
        counts[platform].setdefault(str(stance), {})
        counts[platform][str(stance)][str(tier)] = int(row_count)
    return counts
