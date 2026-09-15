"""Shared fixtures for reasoning-during-moderation cohort tests."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
    EVALUATION_MODE_LINKED_FATE,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
    TRIAL_TYPE_MODERATION,
)

TRIAL_TYPE_PRACTICE = "moderation-practice"
EVALUATION_MODE_SINGLE = "single"


def trial_row(
    post_id: str,
    prolific_id: str,
    decision: str,
    original_text: str = "original",
    mirror_text: str = "mirror",
    trial_type: str = TRIAL_TYPE_MODERATION,
    evaluation_mode: str = EVALUATION_MODE_LINKED_FATE,
    trial_index: int = 0,
    time_elapsed: int = 0,
    response_time_ms: float = 1000.0,
) -> dict[str, object]:
    """Build one jsPsych-style trial dict."""
    return {
        "post_id": post_id,
        "prolific_id": prolific_id,
        "decision": decision,
        "original_text": original_text,
        "mirror_text": mirror_text,
        "trial_type": trial_type,
        "evaluation_mode": evaluation_mode,
        "trial_index": trial_index,
        "time_elapsed": time_elapsed,
        "response_time_ms": response_time_ms,
    }


def _keep_rows(post_id: str, text_key: str, count: int, start: int) -> list[dict[str, object]]:
    original = f"o-{text_key}"
    mirror = f"m-{text_key}"
    return [
        trial_row(
            post_id,
            f"w{start + index}",
            DECISION_KEEP,
            original,
            mirror,
            trial_index=index,
            time_elapsed=index,
        )
        for index in range(count)
    ]


def _remove_rows(
    post_id: str, text_key: str, count: int, start: int
) -> list[dict[str, object]]:
    original = f"o-{text_key}"
    mirror = f"m-{text_key}"
    return [
        trial_row(
            post_id,
            f"w{start + index}",
            DECISION_REMOVE,
            original,
            mirror,
            trial_index=index,
            time_elapsed=index,
        )
        for index in range(count)
    ]


@pytest.fixture
def mixed_trial_rows() -> list[dict[str, object]]:
    """Posts A through G plus practice, single-mode, duplicate, and conflict rows."""
    rows: list[dict[str, object]] = []
    rows.extend(_keep_rows("A", "A", 4, 1))
    rows.extend(_keep_rows("B", "B", 2, 10))
    rows.extend(_remove_rows("B", "B", 2, 12))
    rows.extend(_keep_rows("C", "C", 3, 20))
    rows.extend(_remove_rows("C", "C", 2, 23))
    rows.extend(_keep_rows("D", "D", 2, 30))
    rows.extend(_remove_rows("D", "D", 3, 32))
    rows.extend(_remove_rows("E", "E", 4, 40))
    rows.extend(_keep_rows("F", "F", 4, 50))
    rows.append(
        trial_row("F", "w54", DECISION_REMOVE, "o-F", "m-F", trial_index=4, time_elapsed=4)
    )
    rows.extend(_keep_rows("G", "G", 3, 60))
    rows.append(
        trial_row(
            "P",
            "practice",
            DECISION_KEEP,
            "o-P",
            "m-P",
            trial_type=TRIAL_TYPE_PRACTICE,
        )
    )
    rows.append(
        trial_row(
            "S",
            "single",
            DECISION_KEEP,
            "o-S",
            "m-S",
            evaluation_mode=EVALUATION_MODE_SINGLE,
        )
    )
    rows.append(
        trial_row("B", "w10", DECISION_KEEP, "o-B", "m-B", trial_index=9, time_elapsed=9)
    )
    rows.append(
        trial_row("C", "w20", DECISION_REMOVE, "o-C", "m-C", trial_index=8, time_elapsed=8)
    )
    return rows


@pytest.fixture
def mixed_trials(mixed_trial_rows: list[dict[str, object]]) -> pd.DataFrame:
    """Frame of mixed_trial_rows."""
    return pd.DataFrame(mixed_trial_rows)
