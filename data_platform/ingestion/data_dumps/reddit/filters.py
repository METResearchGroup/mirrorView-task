"""Keep dump comments that are not deleted or removed."""

from __future__ import annotations

from data_platform.ingestion.data_dumps.reddit.models import DumpCommentRaw

DELETED_BODY_OR_AUTHOR_TOKENS = frozenset({"[deleted]", "[removed]"})


def keep_dump_comment(comment: DumpCommentRaw) -> bool:
    """Return True when author and body are not deleted or removed tokens.

    Parameters
    ----------
    comment
        One dump comment.

    Returns
    -------
    bool
        False when author or body, after stripping, is ``[deleted]`` or
        ``[removed]``. True otherwise.
    """
    author = comment.author.strip()
    body = comment.body.strip()
    if author in DELETED_BODY_OR_AUTHOR_TOKENS:
        return False
    if body in DELETED_BODY_OR_AUTHOR_TOKENS:
        return False
    return True
