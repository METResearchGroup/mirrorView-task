"""Summarize marker rates and paired prompt-arm differences.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment4.markers import (
    score_trace,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    STATUS_VALID,
)

RATE_KEYS = ("prompt_arm", "model_id", "group")
PAIR_KEYS = ("post_id", "model_id")
E1_SUFFIX = "_e1"
E2_SUFFIX = "_e2"


def marker_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write family-flag rates for each prompt_arm, model_id, and group."""
    scored = _valid_scored(traces)
    rows = [
        _rate_row(arm, model_id, group, subset)
        for (arm, model_id, group), subset in scored.groupby(list(RATE_KEYS), sort=False)
    ]
    return pd.DataFrame(rows)


def paired_arm_comparison(exp1: pd.DataFrame, exp2: pd.DataFrame) -> pd.DataFrame:
    """Inner-join valid traces and write experiment 2 minus experiment 1 means."""
    raise NotImplementedError


def _valid_scored(traces: pd.DataFrame) -> pd.DataFrame:
    """Score valid thinking spans and attach family flags."""
    valid = traces[traces["status"] == STATUS_VALID]
    rows = [_row_with_flags(row) for row in valid.to_dict(orient="records")]
    return pd.DataFrame(rows)


def _row_with_flags(row: dict[str, object]) -> dict[str, object]:
    score = score_trace(str(row["thinking_text"]))
    return {
        **row,
        "uncertainty": score.uncertainty,
        "revision": score.revision,
        "tension": score.tension,
    }


def _rate_row(
    arm: str, model_id: str, group: str, subset: pd.DataFrame
) -> dict[str, object]:
    return {
        "prompt_arm": arm,
        "model_id": model_id,
        "group": group,
        "n_valid": int(len(subset)),
        "uncertainty_rate": float(subset["uncertainty"].mean()) if len(subset) else float("nan"),
        "revision_rate": float(subset["revision"].mean()) if len(subset) else float("nan"),
        "tension_rate": float(subset["tension"].mean()) if len(subset) else float("nan"),
    }
