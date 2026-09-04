"""Locked classifier, platform, and output column contracts for training parquets."""

from pathlib import Path

CLASSIFIER_NAMES: tuple[str, ...] = (
    "is_likely_spam",
    "is_news_or_opinion",
    "is_political",
    "is_self_contained",
    "is_structurally_complete",
    "is_toxic_tiered",
    "political_stance",
)

PLATFORMS: tuple[str, ...] = ("bluesky", "twitter", "reddit")

DEFAULT_DATA_ROOT: Path = Path(
    "/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data"
)

S3_BUCKET: str = "met-ml-training"
S3_PREFIX: str = "mirrorview/create_feature_generation_training_sets_2026_09_04"

OUTPUT_ID_COLUMN: str = "uri"
LABEL_TIMESTAMP_COLUMN: str = "label_timestamp"
OUTPUT_TEXT_COLUMN: str = "text"

PLATFORM_RECORD_COLUMNS: dict[str, tuple[str, str]] = {
    "bluesky": ("uri", "text"),
    "twitter": ("tweet_id", "text"),
    "reddit": ("comment_fullname", "body"),
}

LABEL_COLUMNS: dict[str, tuple[str, ...]] = {
    "is_likely_spam": ("is_likely_spam",),
    "is_news_or_opinion": ("category",),
    "is_political": ("is_political",),
    "is_self_contained": ("is_self_contained",),
    "is_structurally_complete": ("is_structurally_complete",),
    "is_toxic_tiered": ("toxicity_prob", "toxicity_tier"),
    "political_stance": ("political_stance",),
}
