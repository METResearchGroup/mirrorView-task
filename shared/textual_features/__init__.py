"""Shared textual feature extractors and registry.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features import get_feature, CHAR_COUNT"
"""

from __future__ import annotations

from shared.textual_features.avg_sentence_length import AvgSentenceLengthMetric
from shared.textual_features.base import CalculateMetric
from shared.textual_features.char_count import CharCountMetric
from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric
from shared.textual_features.intergroup import (
    IntergroupClassification,
    classify_post as classify_intergroup_post,
    classify_texts as classify_intergroup_texts,
)
from shared.textual_features.prime import (
    PrimeClassification,
    classify_post as classify_prime_post,
    classify_texts as classify_prime_texts,
)
from shared.textual_features.punctuation_count import PunctuationCountMetric
from shared.textual_features.punctuation_density import PunctuationDensityMetric
from shared.textual_features.reading_ease import FleschReadingEaseMetric
from shared.textual_features.registry import (
    AVG_SENTENCE_LENGTH,
    CHAR_COUNT,
    FLESCH_KINCAID_GRADE,
    INTERGROUP,
    PRIME,
    PUNCTUATION_COUNT,
    PUNCTUATION_DENSITY,
    READING_EASE,
    SENTENCE_COUNT,
    VALENCE,
    WORD_COUNT,
    FEATURES,
    FeatureEntry,
    FeatureKind,
    get_feature,
)
from shared.textual_features.sentence_count import SentenceCountMetric
from shared.textual_features.valence import (
    ValenceClassification,
    classify_post as classify_valence_post,
    classify_texts as classify_valence_texts,
)
from shared.textual_features.word_count import WordCountMetric

__all__ = [
    "AVG_SENTENCE_LENGTH",
    "AvgSentenceLengthMetric",
    "CHAR_COUNT",
    "CalculateMetric",
    "CharCountMetric",
    "FEATURES",
    "FLESCH_KINCAID_GRADE",
    "FeatureEntry",
    "FeatureKind",
    "FleschKincaidGradeMetric",
    "FleschReadingEaseMetric",
    "INTERGROUP",
    "IntergroupClassification",
    "PRIME",
    "PUNCTUATION_COUNT",
    "PUNCTUATION_DENSITY",
    "PrimeClassification",
    "PunctuationCountMetric",
    "PunctuationDensityMetric",
    "READING_EASE",
    "SENTENCE_COUNT",
    "SentenceCountMetric",
    "VALENCE",
    "ValenceClassification",
    "WORD_COUNT",
    "WordCountMetric",
    "classify_intergroup_post",
    "classify_intergroup_texts",
    "classify_prime_post",
    "classify_prime_texts",
    "classify_valence_post",
    "classify_valence_texts",
    "get_feature",
]
