"""Shared fixtures for predict keep/remove Jev and GEPA tests."""

from __future__ import annotations

import pandas as pd
import pytest


def trial_row(
    *,
    trial_type: str = "moderation-trial",
    trial_index: int = 1,
    time_elapsed: float = 10.0,
    post_id: str = "P1",
    prolific_id: str = "W1",
    decision: str = "keep",
    original_text: str = "original",
    mirror_text: str = "mirror",
    sampled_stance: str = "left",
    sample_toxicity_type: str = "low",
    evaluation_mode: str = "linked_fate",
) -> dict[str, object]:
    """Build one Part 3 trial row for unit tests."""
    return {
        "trial_type": trial_type,
        "trial_index": trial_index,
        "time_elapsed": time_elapsed,
        "post_id": post_id,
        "prolific_id": prolific_id,
        "decision": decision,
        "original_text": original_text,
        "mirror_text": mirror_text,
        "sampled_stance": sampled_stance,
        "sample_toxicity_type": sample_toxicity_type,
        "evaluation_mode": evaluation_mode,
    }


@pytest.fixture
def mixed_trials() -> pd.DataFrame:
    """Synthetic trials covering unanimous, majority, tie, and filter edge cases."""
    rows = [
        trial_row(post_id="P1", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W3", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W4", decision="keep", trial_index=1),
        trial_row(post_id="P2", prolific_id="W1", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W2", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W3", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W4", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W3", decision="remove", trial_index=1),
        trial_row(post_id="P3", prolific_id="W4", decision="remove", trial_index=1),
        trial_row(post_id="P4", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P4", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(
            post_id="P5",
            prolific_id="W",
            decision="keep",
            trial_index=1,
            time_elapsed=10.0,
        ),
        trial_row(
            post_id="P5",
            prolific_id="W",
            decision="keep",
            trial_index=5,
            time_elapsed=10.0,
        ),
        trial_row(
            trial_type="moderation-practice",
            post_id="P6",
            prolific_id="W9",
            decision="keep",
        ),
        trial_row(post_id="", prolific_id="W10", decision="keep"),
    ]
    return pd.DataFrame(rows)
