"""Length / punctuation metrics (thin re-exports from shared).

To run:

PYTHONPATH=. uv run python -c "from experiments.mirrors_content_analysis_2026_04_24.analysis.length_compression_analysis.metrics import DEFAULT_LENGTH_METRICS"
"""

from __future__ import annotations

from shared.textual_features.avg_sentence_length import AvgSentenceLengthMetric
from shared.textual_features.base import CalculateMetric
from shared.textual_features.char_count import CharCountMetric
from shared.textual_features.punctuation_count import PunctuationCountMetric
from shared.textual_features.punctuation_density import PunctuationDensityMetric
from shared.textual_features.sentence_count import SentenceCountMetric
from shared.textual_features.word_count import WordCountMetric

DEFAULT_LENGTH_METRICS: tuple[CalculateMetric, ...] = (
    CharCountMetric(),
    WordCountMetric(),
    SentenceCountMetric(),
    AvgSentenceLengthMetric(),
    PunctuationCountMetric(),
    PunctuationDensityMetric(),
)

__all__ = [
    "AvgSentenceLengthMetric",
    "CalculateMetric",
    "CharCountMetric",
    "DEFAULT_LENGTH_METRICS",
    "PunctuationCountMetric",
    "PunctuationDensityMetric",
    "SentenceCountMetric",
    "WordCountMetric",
]
