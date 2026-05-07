"""Readability and linguistic complexity analysis.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/readability_complexity_analysis.py
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Sequence

import pandas as pd
import spacy

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import safe_divide
from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric
from experiments.mirrors_content_analysis_2026_04_24.analysis.metric_aggregator import (
    MetricAggregator,
    PairwiseAnalysisResult,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.table_renderer import TableRenderer
from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

VOWEL_GROUP_RE = re.compile(r"[aeiouy]+", re.IGNORECASE)
NON_LETTER_RE = re.compile(r"[^a-z]")


@lru_cache(maxsize=1)
def _nlp() -> spacy.language.Language:
    """Minimal English pipeline for deterministic token/sentence boundaries."""
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def _count_syllables(word: str) -> int:
    w = NON_LETTER_RE.sub("", word.lower())
    if not w:
        return 0
    groups = VOWEL_GROUP_RE.findall(w)
    syllables = len(groups)
    if w.endswith("e") and syllables > 1:
        syllables -= 1
    return max(1, syllables)


def _readability_counts(text: str) -> tuple[int, int, int]:
    doc = _nlp()(text)
    words = [token.text for token in doc if token.is_alpha]
    sentence_count = sum(1 for sent in doc.sents if sent.text.strip())
    if sentence_count == 0:
        sentence_count = 1
    word_count = len(words)
    syllable_count = sum(_count_syllables(word) for word in words)
    return word_count, sentence_count, syllable_count


class FleschKincaidGradeMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "flesch_kincaid_grade"

    def describe(self) -> str:
        return (
            "Flesch-Kincaid Grade Level: 0.39*(words/sentences) + "
            "11.8*(syllables/words) - 15.59, using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        words, sentences, syllables = _readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            0.39 * safe_divide(float(words), float(sentences))
            + 11.8 * safe_divide(float(syllables), float(words))
            - 15.59
        )


class FleschReadingEaseMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "flesch_reading_ease"

    def describe(self) -> str:
        return (
            "Flesch Reading Ease: 206.835 - 1.015*(words/sentences) - "
            "84.6*(syllables/words), using spaCy sentence and token boundaries."
        )

    def calculate(self, text: str) -> float:
        words, sentences, syllables = _readability_counts(text)
        if words == 0:
            return 0.0
        return float(
            206.835
            - 1.015 * safe_divide(float(words), float(sentences))
            - 84.6 * safe_divide(float(syllables), float(words))
        )


DEFAULT_READABILITY_METRICS: tuple[CalculateMetric, ...] = (
    FleschKincaidGradeMetric(),
    FleschReadingEaseMetric(),
)


class ReadabilityComplexityAnalyzer:
    """Readability metrics with design-aware pairwise filter and partition splits."""

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        metrics: Sequence[CalculateMetric] | None = None,
    ) -> None:
        self.df = df
        self._metrics: tuple[CalculateMetric, ...] = (
            tuple(metrics) if metrics is not None else DEFAULT_READABILITY_METRICS
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

    analyzer = ReadabilityComplexityAnalyzer(df)
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()

    analyzer.show_results()
    analyzer.save_results()


if __name__ == "__main__":
    main()
