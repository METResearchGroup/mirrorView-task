"""Summarize marker rates and paired prompt-arm differences.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

import pandas as pd


def marker_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write family-flag rates for each prompt_arm, model_id, and group."""
    raise NotImplementedError


def paired_arm_comparison(exp1: pd.DataFrame, exp2: pd.DataFrame) -> pd.DataFrame:
    """Inner-join valid traces and write experiment 2 minus experiment 1 means."""
    raise NotImplementedError
