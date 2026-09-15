"""Confirmed uncertainty, revision, and tension markers for thinking traces.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

from dataclasses import dataclass

from experiments.unanimous_vs_majority_labels_2026_08_08.src.bow_tokens import (
    tokenize_feature_value,
)

UNCERTAINTY_PHRASES = (
    "not sure",
    "hard to say",
    "on the other hand",
    "could go either",
    "i am unsure",
    "i'm unsure",
)
REVISION_PHRASES = (
    "on second thought",
    "changed my mind",
    "first i thought",
    "i initially",
)
TENSION_PHRASES = (
    "double standard",
    "both posts",
    "same standard",
    "different standard",
)
UNCERTAINTY_TOKENS = frozenset(
    {
        "maybe",
        "perhaps",
        "unsure",
        "uncertain",
        "borderline",
        "ambiguous",
        "conflicted",
        "however",
        "probably",
        "possibly",
    }
)
REVISION_TOKENS = frozenset(
    {"wait", "actually", "reconsider", "initially", "instead"}
)
TENSION_TOKENS = frozenset(
    {
        "tension",
        "contradiction",
        "conflict",
        "inconsistent",
        "opposite",
        "conflicting",
    }
)


@dataclass(frozen=True)
class MarkerScore:
    """Family flags for one thinking span."""

    uncertainty: bool
    revision: bool
    tension: bool


def score_trace(thinking_text: str) -> MarkerScore:
    """Return family flags from phrases and bag-of-words tokens on thinking text."""
    lowered = thinking_text.lower()
    tokens = tokenize_feature_value(thinking_text)
    return MarkerScore(
        uncertainty=_family_flag(lowered, tokens, UNCERTAINTY_PHRASES, UNCERTAINTY_TOKENS),
        revision=_family_flag(lowered, tokens, REVISION_PHRASES, REVISION_TOKENS),
        tension=_family_flag(lowered, tokens, TENSION_PHRASES, TENSION_TOKENS),
    )


def _family_flag(
    lowered: str,
    tokens: set[str],
    phrases: tuple[str, ...],
    token_set: frozenset[str],
) -> bool:
    """True when any phrase is a substring or any family token is present."""
    if any(phrase in lowered for phrase in phrases):
        return True
    return any(token in tokens for token in token_set)
