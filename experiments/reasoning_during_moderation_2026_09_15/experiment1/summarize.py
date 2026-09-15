"""Summarize experiment 1 thinking-token counts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --summarize
"""

from __future__ import annotations

import pandas as pd


def summarize_tokens(traces: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError
