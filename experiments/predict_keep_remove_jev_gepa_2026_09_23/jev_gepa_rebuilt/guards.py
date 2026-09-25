"""Proposal guards for optimized GEPA candidate text.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_guards.py -q
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    MAX_OPTIMIZED_COMPONENT_CHARS,
    TRAIN_QUOTE_MIN_SUBSTRING_LEN,
)


@dataclass(frozen=True)
class GuardResult:
    """Outcome of running memorization and length guards on one candidate."""

    ok: bool
    reason: str | None


def _violates_train_substring(value: str, train_post_texts: Sequence[str]) -> bool:
    if len(value) < TRAIN_QUOTE_MIN_SUBSTRING_LEN:
        return False
    for start in range(0, len(value) - TRAIN_QUOTE_MIN_SUBSTRING_LEN + 1):
        fragment = value[start : start + TRAIN_QUOTE_MIN_SUBSTRING_LEN]
        for train_text in train_post_texts:
            if fragment in train_text:
                return True
    return False


def check_candidate_guards(
    candidate: dict[str, str],
    *,
    train_post_texts: Sequence[str],
) -> GuardResult:
    """Reject candidates that exceed length cap or quote train post text."""
    for value in candidate.values():
        if len(value) > MAX_OPTIMIZED_COMPONENT_CHARS:
            return GuardResult(ok=False, reason="length_cap")
        if _violates_train_substring(value, train_post_texts):
            return GuardResult(ok=False, reason="train_substring")
    return GuardResult(ok=True, reason=None)
