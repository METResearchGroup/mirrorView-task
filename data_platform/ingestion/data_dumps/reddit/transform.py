"""Map dump comments onto the Reddit comment ingest row shape."""

from __future__ import annotations

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw


def dump_comment_to_sync_row(
    comment: DumpCommentRaw,
    sync_timestamp: str,
) -> dict[str, object]:
    """Return a Reddit ingest comment row for one dump comment.

    The row includes ``record_id`` and UTC ISO-8601 ``created_at``. It does
    not include ``created_utc``. Top-level comments have depth 0. Nested
    comments have depth 1.

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
    raise NotImplementedError
