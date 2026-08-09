"""Shared text helpers for deterministic textual features.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.text_utils import safe_divide"
"""

from __future__ import annotations

import re
from functools import lru_cache

import spacy

WORD_RE = re.compile(r"\b\w+\b")
PUNCTUATION_RE = re.compile(r"[^\w\s]")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)
NON_LETTER_RE = re.compile(r"[^a-z]")


def safe_divide(numerator: float, denominator: float) -> float:
    """Return numerator / denominator, or 0.0 when denominator is non-positive.

    Parameters
    ----------
    numerator
        Division numerator.
    denominator
        Division denominator.

    Returns
    -------
    float
        Quotient, or 0.0 if ``denominator <= 0``.
    """
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


@lru_cache(maxsize=1)
def nlp() -> spacy.language.Language:
    """Minimal English pipeline for deterministic token/sentence boundaries."""
    pipeline = spacy.blank("en")
    pipeline.add_pipe("sentencizer")
    return pipeline


def count_syllables(word: str) -> int:
    """Count syllables with the same heuristic as the mirrors readability metrics.

    Parameters
    ----------
    word
        Token text.

    Returns
    -------
    int
        Syllable estimate (at least 1 for non-empty letter words; 0 for empty).
    """
    cleaned = NON_LETTER_RE.sub("", word.lower())
    if not cleaned:
        return 0
    groups = VOWEL_GROUP_RE.findall(cleaned)
    syllables = len(groups)
    if cleaned.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def readability_counts(text: str) -> tuple[int, int, int]:
    """Return word, sentence, and syllable counts for readability formulas.

    Parameters
    ----------
    text
        Input post string.

    Returns
    -------
    tuple[int, int, int]
        ``(word_count, sentence_count, syllable_count)``. Sentence count is at
        least 1 when the spaCy doc has no non-empty sentences.
    """
    doc = nlp()(text)
    words = [token.text for token in doc if token.is_alpha]
    sentence_count = sum(1 for sent in doc.sents if sent.text.strip())
    if sentence_count == 0:
        sentence_count = 1
    word_count = len(words)
    syllable_count = sum(count_syllables(word) for word in words)
    return word_count, sentence_count, syllable_count
