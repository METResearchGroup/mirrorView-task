"""Named catalog of textual features under ``shared/textual_features/``.

To run:

PYTHONPATH=. uv run python -c "from shared.textual_features.registry import get_feature, CHAR_COUNT; print(get_feature(CHAR_COUNT).build().name)"
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from shared.textual_features.avg_sentence_length import AvgSentenceLengthMetric
from shared.textual_features.base import CalculateMetric
from shared.textual_features.char_count import CharCountMetric
from shared.textual_features.flesch_kincaid_grade import FleschKincaidGradeMetric
from shared.textual_features.intergroup import classify_post as classify_intergroup_post
from shared.textual_features.prime import classify_post as classify_prime_post
from shared.textual_features.punctuation_count import PunctuationCountMetric
from shared.textual_features.punctuation_density import PunctuationDensityMetric
from shared.textual_features.reading_ease import FleschReadingEaseMetric
from shared.textual_features.sentence_count import SentenceCountMetric
from shared.textual_features.valence import classify_post as classify_valence_post
from shared.textual_features.word_count import WordCountMetric

CHAR_COUNT = "CHAR_COUNT"
WORD_COUNT = "WORD_COUNT"
SENTENCE_COUNT = "SENTENCE_COUNT"
AVG_SENTENCE_LENGTH = "AVG_SENTENCE_LENGTH"
PUNCTUATION_COUNT = "PUNCTUATION_COUNT"
PUNCTUATION_DENSITY = "PUNCTUATION_DENSITY"
FLESCH_KINCAID_GRADE = "FLESCH_KINCAID_GRADE"
READING_EASE = "READING_EASE"
VALENCE = "VALENCE"
INTERGROUP = "INTERGROUP"
PRIME = "PRIME"


class FeatureKind(str, Enum):
    """Whether a registry entry is a deterministic metric or an LLM classifier."""

    METRIC = "metric"
    CLASSIFIER = "classifier"


@dataclass(frozen=True)
class FeatureEntry:
    """Immutable catalog record for one textual feature.

    Parameters
    ----------
    name
        SCREAMING_SNAKE registry key.
    kind
        ``FeatureKind.METRIC`` or ``FeatureKind.CLASSIFIER``.
    metric_name
        Stable metric column name (metrics only); ``None`` for classifiers.
    build
        Zero-arg factory returning a ``CalculateMetric`` (metrics only).
    classify_post
        Single-post classifier callable (classifiers only).
    """

    name: str
    kind: FeatureKind
    metric_name: str | None
    build: Callable[[], CalculateMetric] | None
    classify_post: Callable[[str], Any] | None


FEATURES: dict[str, FeatureEntry] = {
    CHAR_COUNT: FeatureEntry(
        name=CHAR_COUNT,
        kind=FeatureKind.METRIC,
        metric_name="char_count",
        build=CharCountMetric,
        classify_post=None,
    ),
    WORD_COUNT: FeatureEntry(
        name=WORD_COUNT,
        kind=FeatureKind.METRIC,
        metric_name="word_count",
        build=WordCountMetric,
        classify_post=None,
    ),
    SENTENCE_COUNT: FeatureEntry(
        name=SENTENCE_COUNT,
        kind=FeatureKind.METRIC,
        metric_name="sentence_count",
        build=SentenceCountMetric,
        classify_post=None,
    ),
    AVG_SENTENCE_LENGTH: FeatureEntry(
        name=AVG_SENTENCE_LENGTH,
        kind=FeatureKind.METRIC,
        metric_name="avg_sentence_length",
        build=AvgSentenceLengthMetric,
        classify_post=None,
    ),
    PUNCTUATION_COUNT: FeatureEntry(
        name=PUNCTUATION_COUNT,
        kind=FeatureKind.METRIC,
        metric_name="punctuation_count",
        build=PunctuationCountMetric,
        classify_post=None,
    ),
    PUNCTUATION_DENSITY: FeatureEntry(
        name=PUNCTUATION_DENSITY,
        kind=FeatureKind.METRIC,
        metric_name="punctuation_density",
        build=PunctuationDensityMetric,
        classify_post=None,
    ),
    FLESCH_KINCAID_GRADE: FeatureEntry(
        name=FLESCH_KINCAID_GRADE,
        kind=FeatureKind.METRIC,
        metric_name="flesch_kincaid_grade",
        build=FleschKincaidGradeMetric,
        classify_post=None,
    ),
    READING_EASE: FeatureEntry(
        name=READING_EASE,
        kind=FeatureKind.METRIC,
        metric_name="flesch_reading_ease",
        build=FleschReadingEaseMetric,
        classify_post=None,
    ),
    VALENCE: FeatureEntry(
        name=VALENCE,
        kind=FeatureKind.CLASSIFIER,
        metric_name=None,
        build=None,
        classify_post=classify_valence_post,
    ),
    INTERGROUP: FeatureEntry(
        name=INTERGROUP,
        kind=FeatureKind.CLASSIFIER,
        metric_name=None,
        build=None,
        classify_post=classify_intergroup_post,
    ),
    PRIME: FeatureEntry(
        name=PRIME,
        kind=FeatureKind.CLASSIFIER,
        metric_name=None,
        build=None,
        classify_post=classify_prime_post,
    ),
}


def get_feature(name: str) -> FeatureEntry:
    """Return the registry entry for ``name``.

    Parameters
    ----------
    name
        SCREAMING_SNAKE registry constant.

    Returns
    -------
    FeatureEntry
        Catalog record for the feature.

    Raises
    ------
    KeyError
        If ``name`` is not in the catalog.
    """
    try:
        return FEATURES[name]
    except KeyError as exc:
        known = ", ".join(sorted(FEATURES))
        raise KeyError(
            f"Unknown textual feature {name!r}. Valid names are in "
            f"shared.textual_features.registry: {known}"
        ) from exc
