"""Pinned constants for the separability original vs mirror experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from data_platform.generate_features.platform_cli import CAMPAIGN_BATCH_SIZE

SHUFFLE_SEED = 42
BEDROCK_LABEL_MAX_TOKENS = 256
SMOKE_ROW_COUNT = 10
FULL_ROW_COUNT = 10000
ATTEMPT_COUNT = 1
PART_INDEX_WIDTH = 5
BATCH_ID_PREFIX = "part-"
REQUEST_ID_SEPARATOR = "-"

CATALOG_S3_BUCKET = "mirrorview-experimental-artifacts"
CATALOG_S3_KEY = "experiments/curate_study_2_phase_3_stimuli/flips.csv"
CATALOG_S3_URI = f"s3://{CATALOG_S3_BUCKET}/{CATALOG_S3_KEY}"
CATALOG_SHA256 = "c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139"
CATALOG_ROW_COUNT = FULL_ROW_COUNT

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
EXPERIMENT_S3_PREFIX = (
    "experiments/test_separability_original_mirror_posts_2026_09_09"
)
PRESENTATION_S3_KEY = f"{EXPERIMENT_S3_PREFIX}/outputs/presentations.parquet"
LABELS_S3_PREFIX = f"{EXPERIMENT_S3_PREFIX}/outputs/labels"
LABELS_ROOT_URI = f"s3://{OUTPUT_S3_BUCKET}/{LABELS_S3_PREFIX}"
OPENAI_LABELS_ROOT_URI = f"{LABELS_ROOT_URI}"
OPENAI_SMOKE_ROOT_URI = f"{LABELS_ROOT_URI}/openai"
BEDROCK_LABELS_ROOT_URI = f"{LABELS_ROOT_URI}"
BEDROCK_SMOKE_ROOT_URI = f"{LABELS_ROOT_URI}/bedrock"
SMOKE_FEATURE_NAME = "smoke"
OPENAI_FEATURE_NAME = "openai"
BEDROCK_FEATURE_NAME = "bedrock"
FEATURE_NAME = "separability"

EXPERIMENT_DIRNAME = "test_separability_original_mirror_posts_2026_09_09"
CACHE_DIRNAME = "cache"
CACHE_FILENAME = "flips.csv"
OUTPUTS_DIRNAME = "outputs"
PRESENTATION_FILENAME = "presentations.parquet"
RESULTS_FILENAME = "RESULTS.md"

ID_COLUMN = "post_primary_key"
ORIGINAL_TEXT_COLUMN = "original_text"
MIRRORED_TEXT_COLUMN = "mirrored_text"
SAMPLED_STANCE_COLUMN = "sampled_stance"
SAMPLE_TOXICITY_TYPE_COLUMN = "sample_toxicity_type"
FIRST_TEXT_COLUMN = "first_text"
SECOND_TEXT_COLUMN = "second_text"
GOLD_HUMAN_SLOT_COLUMN = "gold_human_slot"
PROMPT_TEXT_COLUMN = "prompt_text"
SOURCE_RECORD_ID_COLUMN = "source_record_id"
HUMAN_SLOT_COLUMN = "human_slot"
REASON_COLUMN = "reason"
LABEL_TIMESTAMP_COLUMN = "label_timestamp"

CATALOG_REQUIRED_COLUMNS = (
    ID_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    MIRRORED_TEXT_COLUMN,
    SAMPLED_STANCE_COLUMN,
    SAMPLE_TOXICITY_TYPE_COLUMN,
)
PRESENTATION_COLUMNS = (
    ID_COLUMN,
    FIRST_TEXT_COLUMN,
    SECOND_TEXT_COLUMN,
    GOLD_HUMAN_SLOT_COLUMN,
    SAMPLED_STANCE_COLUMN,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    PROMPT_TEXT_COLUMN,
)

SORT_KIND = "mergesort"
EMPTY_CELL = ""
NAN_CELL = "nan"
CSV_INDEX = False

CAMPAIGN_ID = EXPERIMENT_DIRNAME
DATASET_ID = "study_2_phase_3_catalog"
PREPROCESSED_RUN = "presentations"
CAMPAIGN_PLATFORM = "experiment"

WROTE_PRESENTATIONS_FORMAT = "wrote {row_count} presentations"
SHA256_PRINT_FORMAT = "sha256={digest}"
FINAL_EXISTS_FORMAT = "final file exists: {uri}"
LABELED_SUMMARY_FORMAT = "labeled {labeled} of {expected}"
FAILED_SUMMARY_FORMAT = "failed={failed}"
CELL_KEY_SEPARATOR = "+"

PRINT_METRIC_ACCURACY = "accuracy"
PRINT_METRIC_PRECISION = "precision"
PRINT_METRIC_RECALL = "recall"
PRINT_METRIC_F1 = "f1"
METRIC_ROW_ORDER = (
    PRINT_METRIC_ACCURACY,
    PRINT_METRIC_RECALL,
    PRINT_METRIC_PRECISION,
    PRINT_METRIC_F1,
)
OVERALL_ENGINE_ORDER = (OPENAI_FEATURE_NAME, BEDROCK_FEATURE_NAME)
CELL_STANCE_ORDER = ("left", "right")
CELL_TOXICITY_ORDER = ("low", "medium", "high")
ZERO_METRICS = {
    PRINT_METRIC_ACCURACY: 0.0,
    PRINT_METRIC_PRECISION: 0.0,
    PRINT_METRIC_RECALL: 0.0,
    PRINT_METRIC_F1: 0.0,
}


class GoldHumanSlot(str, Enum):
    """Which presented slot holds the human-written post."""

    FIRST = "first"
    SECOND = "second"


class EngineName(str, Enum):
    """Labeling engine identifier."""

    OPENAI = "openai"
    BEDROCK = "bedrock"


class SampledStance(str, Enum):
    """Political stance copied from the catalog."""

    LEFT = "left"
    RIGHT = "right"


class SampleToxicityType(str, Enum):
    """Toxicity bucket copied from the catalog."""

    LOW = "sample_low_toxicity"
    MIDDLE = "sample_middle_toxicity"
    HIGH = "sample_high_toxicity"


class ToxicityLabel(str, Enum):
    """Short toxicity label used in score cell keys."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


TOXICITY_LABEL_BY_SAMPLE_TYPE = {
    SampleToxicityType.LOW.value: ToxicityLabel.LOW.value,
    SampleToxicityType.MIDDLE.value: ToxicityLabel.MEDIUM.value,
    SampleToxicityType.HIGH.value: ToxicityLabel.HIGH.value,
}
VALID_SAMPLED_STANCES = frozenset(item.value for item in SampledStance)
VALID_SAMPLE_TOXICITY_TYPES = frozenset(item.value for item in SampleToxicityType)
POSITIVE_HUMAN_SLOT = GoldHumanSlot.FIRST.value
BINARY_POSITIVE = 1
BINARY_NEGATIVE = 0


@dataclass(frozen=True)
class CatalogSource:
    """Pinned catalog CSV identity."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class PresentationWriteResult:
    """Paths and digest from one presentation upload."""

    row_count: int
    s3_uri: str
    sha256: str
    local_path: str


PINNED_CATALOG = CatalogSource(
    s3_uri=CATALOG_S3_URI,
    sha256=CATALOG_SHA256,
    expected_row_count=CATALOG_ROW_COUNT,
)


def pinned_catalog() -> CatalogSource:
    """Return the pinned 10,000 row catalog identity."""
    return PINNED_CATALOG


def campaign_batch_size() -> int:
    """Return the campaign part size imported from platform_cli."""
    return CAMPAIGN_BATCH_SIZE
