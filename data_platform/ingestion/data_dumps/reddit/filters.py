"""Keep dump comments that are not deleted or removed."""

from __future__ import annotations

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw

DELETED_BODY_OR_AUTHOR_TOKENS = frozenset({"[deleted]", "[removed]"})


def keep_dump_comment(comment: DumpCommentRaw) -> bool:
    """Return True when author and body are not the strings ``[deleted]`` or ``[removed]``.

    Parameters
    ----------
    comment
        One dump comment.

    Returns
    -------
    bool
        False when author or body, after leading and trailing spaces are
        removed, is ``[deleted]`` or ``[removed]``. True in every other case.
    """
    author = comment.author.strip()
    body = comment.body.strip()
    if author in DELETED_BODY_OR_AUTHOR_TOKENS:
        return False
    if body in DELETED_BODY_OR_AUTHOR_TOKENS:
        return False
    return True
