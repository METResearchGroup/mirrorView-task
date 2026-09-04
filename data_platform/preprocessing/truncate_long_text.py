"""Truncate long social-post text at a complete-sentence boundary.

Platform preprocess specs plug ``truncate_long_text`` into ``text_transforms``
the same way Twitter plugs ``strip_tco_links``.

    from data_platform.preprocessing.truncate_long_text import truncate_long_text
"""

from __future__ import annotations

import re

MAX_CHARS: int = 300
SENTENCE_OVERFLOW: int = 20

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?=\s|$)")
_WORD_RE = re.compile(r"\w+(?:'\w+)?")
_TERMINAL_PUNCTUATION = ".!?"
_INCOMPLETE_TRAILING_MARKS = ",:;-"
_ELLIPSIS = "..."
_CLOSING_QUOTES = "\"')]}»"
_LINE_SEPARATORS = ("\n\n", "\n")

DANGLING_TAILS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "because",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "if",
        "in",
        "is",
        "it",
        "its",
        "just",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "she",
        "so",
        "that",
        "the",
        "their",
        "they",
        "this",
        "to",
        "was",
        "we",
        "were",
        "when",
        "with",
        "your",
    }
)


def _is_false_positive_period(text: str, period_index: int) -> bool:
    if text[period_index] != ".":
        return False
    if period_index > 0 and text[period_index - 1] == ".":
        return True
    if period_index + 1 < len(text) and text[period_index + 1] == ".":
        return True
    previous_is_digit = period_index > 0 and text[period_index - 1].isdigit()
    next_is_digit = period_index + 1 < len(text) and text[period_index + 1].isdigit()
    return previous_is_digit and next_is_digit


def _last_word(text: str) -> str:
    words = _WORD_RE.findall(text)
    return words[-1].lower() if words else ""


def _is_complete_sentence(text: str) -> bool:
    text = text.rstrip()
    if not text:
        return False
    if text[-1] in _INCOMPLETE_TRAILING_MARKS or text.endswith(_ELLIPSIS):
        return False
    core = text.rstrip(_CLOSING_QUOTES)
    if not core or core[-1] not in _TERMINAL_PUNCTUATION:
        return False
    return _last_word(core) not in DANGLING_TAILS


def _sentence_cut_positions(text: str) -> list[int]:
    positions: list[int] = []
    for match in _SENTENCE_BOUNDARY.finditer(text):
        punct_index = match.start() - 1
        if text[punct_index] == "." and _is_false_positive_period(text, punct_index):
            continue
        cut = match.start()
        if _is_complete_sentence(text[:cut]):
            positions.append(cut)
    return positions


def _line_cut_positions(text: str) -> list[int]:
    positions: list[int] = []
    for sep in _LINE_SEPARATORS:
        start = len(text)
        while start > 0:
            idx = text.rfind(sep, 0, start)
            if idx < 0:
                break
            candidate = text[:idx].rstrip()
            if candidate and _is_complete_sentence(candidate):
                positions.append(len(candidate))
            start = idx
    return positions


def _cut_at_complete_boundary(window: str, hard_limit: int) -> str | None:
    sentence_cuts = [cut for cut in _sentence_cut_positions(window) if cut <= hard_limit]
    if sentence_cuts:
        return window[: max(sentence_cuts)].rstrip()
    line_cuts = [cut for cut in _line_cut_positions(window) if cut <= hard_limit]
    if line_cuts:
        return window[: max(line_cuts)].rstrip()
    return None


def _cut_at_word(text: str, max_chars: int) -> str:
    word_window = text[:max_chars]
    space = word_window.rfind(" ")
    if space > 0:
        return word_window[:space].rstrip()
    return word_window.rstrip()


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
    text = text.strip()
    if not text:
        return text
    hard_limit = MAX_CHARS + SENTENCE_OVERFLOW
    if len(text) <= MAX_CHARS and _is_complete_sentence(text):
        return text
    boundary_cut = _cut_at_complete_boundary(text[:hard_limit], hard_limit)
    if boundary_cut is not None:
        return boundary_cut
    if len(text) <= MAX_CHARS:
        return text
    return _cut_at_word(text, MAX_CHARS)
