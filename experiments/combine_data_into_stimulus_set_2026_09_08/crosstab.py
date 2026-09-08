"""Count political stance by LLM toxicity tier, overall and by platform."""

from __future__ import annotations

import pandas as pd


def stance_by_toxicity(frame: pd.DataFrame) -> dict:
    """Return left/right counts by low, medium, and high toxicity."""
    raise NotImplementedError


def stance_by_toxicity_by_integration(frame: pd.DataFrame) -> dict:
    """Return stance by toxicity counts grouped by platform."""
    raise NotImplementedError
