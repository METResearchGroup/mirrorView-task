"""Per-platform record column names shared across preprocessing, features, and curation."""

from __future__ import annotations

from dataclasses import dataclass

CANONICAL_TEXT_COLUMN = "text"
REDDIT_NATIVE_TEXT_COLUMN = "body"


@dataclass(frozen=True)
class PlatformSpecificColumns:
    """Column names and record-file key for one social platform.

    Shared preprocessing, feature, and curation runners are platform-agnostic.
    Each platform CLI attaches one of the module-level constants
    (``BLUESKY_COLUMNS``, ``REDDIT_COLUMNS``, ``TWITTER_COLUMNS``) so those
    runners can resolve:

    - ``records_id_column``: native unique id on the record CSV (dedupe / joins)
    - ``text_column``: shared body text (``text``) to validate, transform, and embed
    - ``feature_file_id_column``: id column written in feature files (often ``uri``)
    - ``records_file_key``: metadata / log noun for the file (``posts`` vs ``comments``)
    """

    records_id_column: str
    text_column: str
    feature_file_id_column: str = "uri"
    records_file_key: str = "posts"


BLUESKY_COLUMNS = PlatformSpecificColumns(
    records_id_column="uri",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column="uri",
    records_file_key="posts",
)

REDDIT_COLUMNS = PlatformSpecificColumns(
    records_id_column="comment_fullname",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column="uri",
    records_file_key="comments",
)

TWITTER_COLUMNS = PlatformSpecificColumns(
    records_id_column="tweet_id",
    text_column=CANONICAL_TEXT_COLUMN,
    feature_file_id_column="uri",
    records_file_key="posts",
)
