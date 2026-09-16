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
GENERIC_DISCOURSE_TOKENS = frozenset(
    {
        "however",
        "maybe",
        "perhaps",
        "probably",
        "possibly",
        "wait",
        "actually",
        "instead",
    }
)
GENERIC_DISCOURSE_PHRASES = frozenset({"on the other hand"})
PROMPT_ECHO_PHRASES = frozenset({"both posts"})
PROMPT_ECHO_TOKENS = frozenset({"opposite"})
STRICT_UNCERTAINTY_TOKENS = UNCERTAINTY_TOKENS - GENERIC_DISCOURSE_TOKENS
STRICT_UNCERTAINTY_PHRASES = tuple(
    phrase
    for phrase in UNCERTAINTY_PHRASES
    if phrase not in GENERIC_DISCOURSE_PHRASES
)
STRICT_REVISION_TOKENS = REVISION_TOKENS - GENERIC_DISCOURSE_TOKENS
STRICT_TENSION_PHRASES = tuple(
    phrase for phrase in TENSION_PHRASES if phrase not in PROMPT_ECHO_PHRASES
)
STRICT_TENSION_TOKENS = TENSION_TOKENS - PROMPT_ECHO_TOKENS
EMPTY_TOKENS: frozenset[str] = frozenset()
THOUSAND = 1000.0


@dataclass(frozen=True)
class MarkerScore:
    """Family flags for one thinking span."""

    uncertainty: bool
    revision: bool
    tension: bool


@dataclass(frozen=True)
class MarkerDetail:
    """Broad, strict, and phrase flags plus strict hit counts for one span."""

    broad: MarkerScore
    strict: MarkerScore
    phrase: MarkerScore
    uncertainty_hits: int
    revision_hits: int
    tension_hits: int
    item_hits: dict[tuple[str, str, str], bool]


def score_trace(thinking_text: str) -> MarkerScore:
    """Return family flags from phrases and bag-of-words tokens on thinking text.

    Phrases match as substrings of the lowercased span. Tokens use
    ``tokenize_feature_value``. A family flag is true when any phrase or token
    in that family matches. Does not score completion text.
    """
    return score_trace_detail(thinking_text).broad


def score_trace_strict(thinking_text: str) -> MarkerScore:
    """Return family flags after dropping generic CoT tokens and prompt-echo items."""
    return score_trace_detail(thinking_text).strict


def score_trace_phrase(thinking_text: str) -> MarkerScore:
    """Return family flags from confirmed phrases only, ignoring token lists."""
    return score_trace_detail(thinking_text).phrase


def score_trace_detail(thinking_text: str) -> MarkerDetail:
    """Return broad, strict, and phrase flags, plus strict item-hit counts."""
    lowered = thinking_text.lower()
    tokens = tokenize_feature_value(thinking_text)
    empty: set[str] = set()
    return MarkerDetail(
        MarkerScore(
            _family_flag(lowered, tokens, UNCERTAINTY_PHRASES, UNCERTAINTY_TOKENS),
            _family_flag(lowered, tokens, REVISION_PHRASES, REVISION_TOKENS),
            _family_flag(lowered, tokens, TENSION_PHRASES, TENSION_TOKENS),
        ),
        MarkerScore(
            _family_flag(
                lowered,
                tokens,
                STRICT_UNCERTAINTY_PHRASES,
                STRICT_UNCERTAINTY_TOKENS,
            ),
            _family_flag(lowered, tokens, REVISION_PHRASES, STRICT_REVISION_TOKENS),
            _family_flag(
                lowered, tokens, STRICT_TENSION_PHRASES, STRICT_TENSION_TOKENS
            ),
        ),
        MarkerScore(
            _family_flag(lowered, empty, UNCERTAINTY_PHRASES, EMPTY_TOKENS),
            _family_flag(lowered, empty, REVISION_PHRASES, EMPTY_TOKENS),
            _family_flag(lowered, empty, TENSION_PHRASES, EMPTY_TOKENS),
        ),
        _family_hits(
            lowered, tokens, STRICT_UNCERTAINTY_PHRASES, STRICT_UNCERTAINTY_TOKENS
        ),
        _family_hits(lowered, tokens, REVISION_PHRASES, STRICT_REVISION_TOKENS),
        _family_hits(lowered, tokens, STRICT_TENSION_PHRASES, STRICT_TENSION_TOKENS),
        _item_hit_map(lowered, tokens),
    )


def item_hit_map(thinking_text: str) -> dict[tuple[str, str, str], bool]:
    """Return whether each confirmed marker item is present.

    Keys are ``(family, kind, item)`` with kind ``phrase`` or ``token``.
    """
    lowered = thinking_text.lower()
    tokens = tokenize_feature_value(thinking_text)
    return _item_hit_map(lowered, tokens)


def density_per_thousand(hit_count: int, thinking_token_count: int) -> float:
    """Return distinct strict item hits per 1,000 thinking tokens."""
    if thinking_token_count <= 0:
        return 0.0
    return THOUSAND * hit_count / thinking_token_count


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


def _family_hits(
    lowered: str,
    tokens: set[str],
    phrases: tuple[str, ...],
    token_set: frozenset[str],
) -> int:
    """Count distinct matching phrases plus distinct matching tokens in one family."""
    phrase_hits = sum(1 for phrase in phrases if phrase in lowered)
    token_hits = sum(1 for token in token_set if token in tokens)
    return phrase_hits + token_hits


def _item_hit_map(
    lowered: str, tokens: set[str]
) -> dict[tuple[str, str, str], bool]:
    hits: dict[tuple[str, str, str], bool] = {}
    hits.update(_phrase_hits("uncertainty", lowered, UNCERTAINTY_PHRASES))
    hits.update(_phrase_hits("revision", lowered, REVISION_PHRASES))
    hits.update(_phrase_hits("tension", lowered, TENSION_PHRASES))
    hits.update(_token_hits("uncertainty", tokens, UNCERTAINTY_TOKENS))
    hits.update(_token_hits("revision", tokens, REVISION_TOKENS))
    hits.update(_token_hits("tension", tokens, TENSION_TOKENS))
    return hits


def _phrase_hits(
    family: str, lowered: str, phrases: tuple[str, ...]
) -> dict[tuple[str, str, str], bool]:
    return {(family, "phrase", phrase): phrase in lowered for phrase in phrases}


def _token_hits(
    family: str, tokens: set[str], token_set: frozenset[str]
) -> dict[tuple[str, str, str], bool]:
    return {(family, "token", token): token in tokens for token in sorted(token_set)}
