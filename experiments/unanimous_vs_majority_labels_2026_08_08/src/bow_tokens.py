"""Bag-of-words token helpers for Analysis 2 word clouds.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.unanimous_vs_majority_labels_2026_08_08.src.bow_tokens import tokenize_feature_value; print(tokenize_feature_value('None of the mirror text'))"
"""

from __future__ import annotations

import re

_NON_LETTER_SPLIT = re.compile(r"[^A-Za-z]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "none",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "it",
        "they",
        "them",
        "their",
        "this",
        "that",
        "these",
        "those",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "but",
        "if",
        "as",
        "not",
        "no",
        "so",
        "than",
        "too",
        "very",
        "can",
        "will",
        "just",
        "about",
        "into",
        "over",
        "after",
        "before",
        "between",
        "through",
        "during",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "s",
        "t",
        "don",
        "should",
        "now",
    }
)
_META_TOKENS = frozenset({"mirror", "original", "mirrors", "mirrored"})
_EXTRA_EXCLUDED = frozenset({"vs", "framing", "uses", "short", "via"})


def tokenize_feature_value(feature_value: str) -> set[str]:
    """Tokenize one feature value with the locked bag-of-words rules.

    Parameters
    ----------
    feature_value
        Stage 1 ``feature_value`` string.

    Returns
    -------
    set[str]
        Lowercased tokens after stopword, meta-token, and extra exclusion scrubbing.
    """
    lowered = str(feature_value).lower()
    raw_tokens = [tok for tok in _NON_LETTER_SPLIT.split(lowered) if tok]
    kept: set[str] = set()
    for token in raw_tokens:
        if len(token) <= 1:
            continue
        if token in _STOPWORDS:
            continue
        if token in _META_TOKENS:
            continue
        if token in _EXTRA_EXCLUDED:
            continue
        kept.add(token)
    return kept
