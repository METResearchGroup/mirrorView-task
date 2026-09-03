"""Convert dump comments into the same fields used by Reddit comment ingest."""

from __future__ import annotations

from datetime import datetime, timezone

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw
from data_platform.ingestion.generate_record_id import (
    INTEGRATION_REDDIT,
    attach_record_id,
)

COMMENT_FULLNAME_PREFIX = "t1_"


def _created_at_from_unix(created_utc: int) -> str:
    return datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()


def dump_comment_to_sync_row(
    comment: DumpCommentRaw,
    sync_timestamp: str,
) -> dict[str, object]:
    """Return a Reddit ingest comment row for one dump comment.

    The row includes ``record_id`` and UTC ISO-8601 ``created_at``. It does
    not include ``created_utc``. Only fields on ``SyncRedditCommentModel``
    are written.

    Parameters
    ----------
    comment
        One dump comment that already passed the deleted-or-removed check.
    sync_timestamp
        Run timestamp written onto the row.

    Returns
    -------
    dict[str, object]
        A dict that validates as ``SyncRedditCommentModel``.
    """
    row: dict[str, object] = {
        "comment_fullname": f"{COMMENT_FULLNAME_PREFIX}{comment.id}",
        "author": comment.author,
        "body": comment.body,
        "created_at": _created_at_from_unix(comment.created_utc),
        "sync_timestamp": sync_timestamp,
    }
    return attach_record_id(row, INTEGRATION_REDDIT)
