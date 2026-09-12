"""Shared pytest fixtures for AI simulation responses tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
    POSTS_PER_USER,
)

REFLECTION_QUESTION = (
    "You just completed a series of content moderation decisions where you saw "
    "pairs of posts expressing opposing political viewpoints on the same topic - "
    "one from a left-leaning perspective and one from a right-leaning perspective - "
    "and made a single joint decision about both. In a few sentences, please "
    "describe what was going through your mind as you made these decisions. What, "
    "if anything, influenced how you evaluated the posts as a pair?"
)


def _trial_row(
    *,
    prolific_id: str,
    trial_index: int,
    decision: str,
    pair_order: list[str],
    **extra: object,
) -> dict[str, object]:
    return {
        "prolific_id": prolific_id,
        "participant_id": f"pid-{prolific_id}",
        "trial_index": trial_index,
        "evaluation_mode": "linked_fate",
        "decision": decision,
        "pair_order": json.dumps(pair_order),
        "original_text": f"original-{trial_index}",
        "mirror_text": f"mirror-{trial_index}",
        "post_id": f"post-{trial_index}",
        "sampled_stance": "left",
        "sample_toxicity_type": "sample_low_toxicity",
        "phase1_pair_reflection_text": "I thought about both sides.",
        "phase1_pair_influence_rating": 4,
        "age": "30",
        "gender": "woman",
        "education": "bachelors",
        "political_affiliation": "democrat",
        "party_lean": "democrat",
        "party_group": "democrat",
        "political_ideology": "3",
        "political_follow": "5",
        "rep_id": "2",
        "dem_id": "6",
        "attitude_reduce_abortion": "50",
        **extra,
    }


def _complete_user_rows(
    prolific_id: str,
    *,
    reflection_text: str = "I thought about both sides.",
    education: str = "bachelors",
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trial_index in range(POSTS_PER_USER):
        rows.append(
            _trial_row(
                prolific_id=prolific_id,
                trial_index=trial_index,
                decision="keep" if trial_index % 2 == 0 else "remove",
                pair_order=["original", "mirror"],
                phase1_pair_reflection_text=reflection_text,
                education=education,
            )
        )
    return rows


@pytest.fixture
def make_cohort_csv(tmp_path: Path):
    """Write one CSV per user and return paths with epoch metadata."""

    def _make(users: list[tuple[str, int]], **row_overrides: object) -> list[Path]:
        paths: list[Path] = []
        for prolific_id, epoch_ms in users:
            rows = _complete_user_rows(prolific_id, **row_overrides)
            frame = pd.DataFrame(rows)
            path = tmp_path / f"data_{epoch_ms}_{prolific_id}.csv"
            frame.to_csv(path, index=False)
            paths.append(path)
        return paths

    return _make


@pytest.fixture
def sample_user() -> CohortUser:
    """Return one cohort user for prompt tests."""
    return CohortUser(
        prolific_id="user-a",
        participant_id="pid-user-a",
        source_file_epoch_ms=10,
        party_group="democrat",
        age="30",
        gender="woman",
        education="bachelors",
        political_affiliation="democrat",
        party_lean="democrat",
        political_ideology="3",
        political_follow="5",
        rep_id="2",
        dem_id="6",
        attitude_reduce_abortion="50",
        attitude_citizenship_undocumented="50",
        attitude_restrict_guns="50",
        attitude_regulate_environment="50",
        attitude_raise_wealth_taxes="50",
        attitude_expand_medicaid="50",
        phase1_pair_reflection_text="I weighed both posts together.",
        phase1_pair_influence_rating=5,
    )


@pytest.fixture
def sample_trials() -> list[CohortTrial]:
    """Return one user's trials with a mirror-first pair order."""
    return [
        CohortTrial(
            prolific_id="user-a",
            pair_index=1,
            post_id="post-0",
            original_text="original-0",
            mirror_text="mirror-0",
            pair_order=("mirror", "original"),
            gold_remove=0,
            sampled_stance="left",
            sample_toxicity_type="sample_low_toxicity",
            trial_index=0,
        )
    ]


@pytest.fixture
def reflection_question() -> str:
    """Return the live study reflection question text."""
    return REFLECTION_QUESTION
