"""Truncate long social-post text at a complete-sentence boundary.

Platform preprocess specs plug ``truncate_long_text`` into ``text_transforms``
the same way Twitter plugs ``strip_tco_links``.

    from data_platform.preprocessing.truncate_long_text import truncate_long_text
"""

from __future__ import annotations

MAX_CHARS: int = 300
SENTENCE_OVERFLOW: int = 20


def truncate_long_text(text: str) -> str:
    raise NotImplementedError
