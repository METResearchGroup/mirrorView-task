"""Prompt rendering for the four experiment ablations."""

from __future__ import annotations

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
)

STUDY_SYSTEM_PROMPT = ""


def render_pairs(trials: list[CohortTrial]) -> str:
    """Render all post pairs for one user."""
    raise NotImplementedError


def render_demographics(user: CohortUser) -> str:
    """Render non-empty demographic and attitude fields."""
    raise NotImplementedError


def render_reflection(user: CohortUser) -> str:
    """Render the reflection question, answer, and influence rating."""
    raise NotImplementedError


def render_user_prompt(
    experiment_number: int,
    user: CohortUser,
    trials: list[CohortTrial],
) -> str:
    """Render the user prompt for one experiment ablation."""
    raise NotImplementedError
