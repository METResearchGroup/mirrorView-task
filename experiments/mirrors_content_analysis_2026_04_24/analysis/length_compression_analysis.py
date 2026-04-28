"""Analysis of word count, post length, etc.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import (
    PUNCTUATION_RE,
    SENTENCE_SPLIT_RE,
    WORD_RE,
    safe_divide,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.metric_aggregator import (
    MetricAggregator,
    PairwiseAnalysisResult,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.table_renderer import TableRenderer
from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader


class CalculateMetric(ABC):
    """Single-text scalar metric: stable ``name``, prose ``describe()``, and ``calculate()``."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier used in column names (e.g. ``char_count``)."""

    @abstractmethod
    def describe(self) -> str:
        """What the metric measures and exactly how it is computed from the input string."""

    @abstractmethod
    def calculate(self, text: str) -> float:
        """Return the metric value for one normalized post string."""


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


class LengthCompressionAnalyzer:
    """Length / compression metrics with design-aware pairwise filter and partition splits."""

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        metrics: Sequence[CalculateMetric] | None = None,
    ) -> None:
        self.df = df
        self._metrics: tuple[CalculateMetric, ...] = (
            tuple(metrics) if metrics is not None else DEFAULT_LENGTH_METRICS
        )
        self._aggregator = MetricAggregator(df=self.df, metrics=self._metrics)
        self.results: dict[str, Any] = {
            "original_text_analysis": None,
            "mirror_text_analysis": None,
            "pairwise_analysis": None,
            "keep_remove_analysis": None,
        }

    def original_text_analysis(self) -> None:
        """Per-metric means by party×condition, party-only, condition-only, and global."""
        self.results["original_text_analysis"] = self._aggregator.original_text_analysis()

    def mirror_text_analysis(self) -> None:
        """Mirror metrics on trials where both posts are shown (same gate as pairwise)."""
        self.results["mirror_text_analysis"] = self._aggregator.mirror_text_analysis()

    def pairwise_analysis(self) -> None:
        """Pairwise rows only when original+mirror text exist and design shows both posts."""
        self.results["pairwise_analysis"] = self._aggregator.pairwise_analysis()

    def keep_remove_analysis(self) -> None:
        """Keep/remove aggregates by party×condition×phase, plus coarser partition levels."""
        packed = self.results["pairwise_analysis"]
        if not isinstance(packed, PairwiseAnalysisResult):
            raise RuntimeError("Run pairwise_analysis before keep_remove_analysis.")
        self.results["keep_remove_analysis"] = self._aggregator.keep_remove_analysis(packed.dataframe)

    def show_results(self) -> None:
        """Print analysis outputs as tables."""
        renderer = TableRenderer(self._metrics)
        renderer.render_metric_glossary()
        orig = self.results["original_text_analysis"]
        mir = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if orig is not None:
            renderer.render_metric_calculations(
                "Original text — means by party × condition (+ marginals)",
                orig,
            )

        if mir is not None:
            renderer.render_metric_calculations(
                "Mirror text — means by party × condition (+ marginals)",
                mir,
            )

        if isinstance(pairwise, PairwiseAnalysisResult):
            if not pairwise.dataframe.empty:
                renderer.render_pairwise_sample(pairwise.dataframe)
            if pairwise.partition_means:
                renderer.render_metric_calculations(
                    "Pairwise — mean ratio by party × condition (+ marginals)",
                    pairwise.partition_means,
                )

        if isinstance(keep_remove, dict):
            renderer.render_keep_remove(keep_remove)

    def save_results(self) -> None:
        """Persist results to disk (not implemented)."""
        pass

def main() -> None:
    dataloader = Dataloader()
    df = dataloader.get_latest_mirrorview_run_data()
    df = dataloader.transform_latest_mirrorview_run_data(df)

    analyzer = LengthCompressionAnalyzer(df)
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()

    analyzer.show_results()
    analyzer.save_results()


if __name__ == "__main__":
    main()
