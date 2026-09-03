"""Per-platform record column names shared across preprocessing, features, and curation."""

from __future__ import annotations

from dataclasses import dataclass

CANONICAL_TEXT_COLUMN = "text"
CANONICAL_AUTHOR_HANDLE_COLUMN = "author_handle"
CANONICAL_SOURCE_RECORD_ID_COLUMN = "source_record_id"
CANONICAL_RECORD_ID_COLUMN = "record_id"
REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN = "body"


@dataclass(frozen=True)
class PlatformSpecificColumns:
    """Column names and record-file key for one social platform.

    Shared preprocessing, feature, and curation runners are platform-agnostic.
    Each platform CLI attaches one of the module-level constants
    (``BLUESKY_COLUMNS``, ``REDDIT_COLUMNS``, ``TWITTER_COLUMNS``) so those
    runners can resolve:

    - ``records_id_column``: original platform unique id on the record CSV (dedupe / joins)
    - ``text_column``: shared body text (``text``) to validate, transform, and embed
    - ``feature_file_id_column``: id column written in feature files (``source_record_id``)
    - ``records_file_key``: metadata / log noun for the file (``posts`` vs ``comments``)
    """

    records_id_column: str
    text_column: str
    feature_file_id_column: str = CANONICAL_SOURCE_RECORD_ID_COLUMN
    records_file_key: str = "posts"


BLUESKY_COLUMNS = PlatformSpecificColumns(
    records_id_column="uri",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column=CANONICAL_SOURCE_RECORD_ID_COLUMN,
    records_file_key="posts",
)

REDDIT_COLUMNS = PlatformSpecificColumns(
    records_id_column="comment_fullname",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column=CANONICAL_SOURCE_RECORD_ID_COLUMN,
    records_file_key="comments",
)

TWITTER_COLUMNS = PlatformSpecificColumns(
    records_id_column="tweet_id",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column=CANONICAL_SOURCE_RECORD_ID_COLUMN,
    records_file_key="posts",
)
