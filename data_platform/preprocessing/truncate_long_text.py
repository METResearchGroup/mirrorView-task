"""Truncate long social-post text at a complete-sentence boundary.

Platform preprocess specs plug ``truncate_long_text`` into ``text_transforms``
the same way Twitter plugs ``strip_tco_links``.

    from data_platform.preprocessing.truncate_long_text import truncate_long_text
"""

from __future__ import annotations

MAX_CHARS: int = 300
SENTENCE_OVERFLOW: int = 20


def truncate_long_text(text: str) -> str:
    """Return text cut to the longest complete sentence within the soft char cap.

    The cap is ``MAX_CHARS``, with ``SENTENCE_OVERFLOW`` extra characters allowed
    so a sentence that overruns the cap slightly can still be kept whole.
    Leading and trailing whitespace is stripped. Empty input stays empty.
    Short text that already ends on a complete sentence is returned unchanged.

    Parameters
    ----------
    text
        Standardized post or comment text.

    Returns
    -------
    str
        Truncated text. When no complete sentence or line boundary fits in the
        window, the function falls back to a word cut at ``MAX_CHARS``, then to
        a hard cut.
    """
    raise NotImplementedError
