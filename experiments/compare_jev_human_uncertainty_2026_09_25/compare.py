"""Join five-labeler remove counts to Jev probabilities.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py -q
"""

from __future__ import annotations

import pandas as pd


def jev_bin_for_probability(probability: float) -> int:
    raise NotImplementedError


def attach_jev_bin(frame: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def attach_difference_score(frame: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def join_on_post_id(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def build_comparison_frame(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame:
    """Return the inner join with a Jev bin and a difference score."""
    joined = join_on_post_id(human, jev)
    binned = attach_jev_bin(joined)
    return attach_difference_score(binned)
