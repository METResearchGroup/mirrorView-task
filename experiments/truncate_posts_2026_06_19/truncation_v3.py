from __future__ import annotations

import re

MAX_CHARS = 300
SENTENCE_OVERFLOW = 20

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?=\s|$)")
_WORD_RE = re.compile(r"\w+(?:'\w+)?")

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
    if (
        period_index > 0
        and period_index + 1 < len(text)
        and text[period_index - 1].isdigit()
        and text[period_index + 1].isdigit()
    ):
        return True
    return False


def _last_word(text: str) -> str:
    words = _WORD_RE.findall(text)
    return words[-1].lower() if words else ""


def is_complete_sentence(text: str) -> bool:
    """Return True when ``text`` ends on a plausible complete sentence."""
    text = text.rstrip()
    if not text:
        return False
    if text[-1] in ",:;-" or text.endswith("..."):
        return False

    core = text.rstrip("\"')]}»")
    if not core or core[-1] not in ".!?":
        return False
    if _last_word(core) in DANGLING_TAILS:
        return False
    return True


def _sentence_cut_positions(text: str) -> list[int]:
    positions: list[int] = []
    for match in _SENTENCE_BOUNDARY.finditer(text):
        punct_index = match.start() - 1
        if text[punct_index] == "." and _is_false_positive_period(text, punct_index):
            continue
        cut = match.start()
        if is_complete_sentence(text[:cut]):
            positions.append(cut)
    return positions


def _line_cut_positions(text: str) -> list[int]:
    positions: list[int] = []
    for sep in ("\n\n", "\n"):
        start = len(text)
        while start > 0:
            idx = text.rfind(sep, 0, start)
            if idx < 0:
                break
            candidate = text[:idx].rstrip()
            if candidate and is_complete_sentence(candidate):
                positions.append(len(candidate))
            start = idx
    return positions


def truncate_social_post(
    text: str,
    max_chars: int = MAX_CHARS,
    *,
    sentence_overflow: int = SENTENCE_OVERFLOW,
) -> str:
    """Truncate to the longest complete sentence within a soft char cap."""
    text = text.strip()
    if not text:
        return text

    hard_limit = max_chars + sentence_overflow
    if len(text) <= max_chars and is_complete_sentence(text):
        return text

    window = text[:hard_limit]
    sentence_cuts = [cut for cut in _sentence_cut_positions(window) if cut <= hard_limit]
    if sentence_cuts:
        return window[: max(sentence_cuts)].rstrip()

    line_cuts = [cut for cut in _line_cut_positions(window) if cut <= hard_limit]
    if line_cuts:
        return window[: max(line_cuts)].rstrip()

    if len(text) <= max_chars:
        return text

    word_window = text[:max_chars]
    space = word_window.rfind(" ")
    if space > 0:
        return word_window[:space].rstrip()
    return word_window.rstrip()


def truncate_pair(
    original: str,
    mirror: str,
    max_chars: int = MAX_CHARS,
    *,
    sentence_overflow: int = SENTENCE_OVERFLOW,
) -> tuple[str, str]:
    """Truncate original and mirror independently to complete sentences."""
    return (
        truncate_social_post(
            original, max_chars, sentence_overflow=sentence_overflow
        ),
        truncate_social_post(mirror, max_chars, sentence_overflow=sentence_overflow),
    )
