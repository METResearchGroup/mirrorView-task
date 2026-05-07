from __future__ import annotations

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import (
    PUNCTUATION_RE,
    SENTENCE_SPLIT_RE,
    WORD_RE,
    safe_divide,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric


class CharCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "char_count"

    def describe(self) -> str:
        return (
            "Post length in characters. Counts every codepoint in the string after normalization "
            "(including spaces, punctuation, and line breaks). Formula: float(len(text))."
        )

    def calculate(self, text: str) -> float:
        return float(len(text))


class WordCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "word_count"

    def describe(self) -> str:
        return (
            "Approximate word count via regex tokenization: count how many times the pattern "
            r"\b\w+\b matches (word characters bounded by word boundaries). "
            "Same notion as many simple NLP word counts; not full Unicode word segmentation."
        )

    def calculate(self, text: str) -> float:
        return float(len(WORD_RE.findall(text)))


class SentenceCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "sentence_count"

    def describe(self) -> str:
        return (
            "Sentence count by splitting on one-or-more occurrences of ., !, or ?. "
            "Non-empty trimmed segments after the split are counted; empty runs are ignored."
        )

    def calculate(self, text: str) -> float:
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return float(len(parts))


class AvgSentenceLengthMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "avg_sentence_length"

    def describe(self) -> str:
        return (
            "Mean words per sentence for this post. Computed as word_count / sentence_count "
            "using the same word and sentence definitions as the separate word and sentence metrics; "
            "0 if sentence_count is 0 (avoids division by zero)."
        )

    def calculate(self, text: str) -> float:
        wc = float(len(WORD_RE.findall(text)))
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        sc = float(len(parts))
        return safe_divide(wc, sc)


class PunctuationCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "punctuation_count"

    def describe(self) -> str:
        return (
            "Count of punctuation-like characters: each match of the regex [^\\w\\s] "
            "(not a word character, not whitespace) counts as one punctuation token."
        )

    def calculate(self, text: str) -> float:
        return float(len(PUNCTUATION_RE.findall(text)))


class PunctuationDensityMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "punctuation_density"

    def describe(self) -> str:
        return (
            "Punctuation per character: punctuation_count / char_count for the same string, "
            "using the punctuation and character definitions above. 0 if the string has length 0."
        )

    def calculate(self, text: str) -> float:
        char_count = len(text)
        punct = float(len(PUNCTUATION_RE.findall(text)))
        return safe_divide(punct, float(char_count) if char_count else 0.0)


DEFAULT_LENGTH_METRICS: tuple[CalculateMetric, ...] = (
    CharCountMetric(),
    WordCountMetric(),
    SentenceCountMetric(),
    AvgSentenceLengthMetric(),
    PunctuationCountMetric(),
    PunctuationDensityMetric(),
)
