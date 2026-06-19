from __future__ import annotations

import re

MAX_CHARS = 300
MIN_KEEP_RATIO = 0.75

# Zero-width match immediately after sentence-ending punctuation.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?=\s|$)")


def _is_false_positive_period(window: str, period_index: int) -> bool:
    """Return True when ``period_index`` is not a real sentence boundary."""
    if window[period_index] != ".":
        return False
    if period_index > 0 and window[period_index - 1] == ".":
        return True
    if period_index + 1 < len(window) and window[period_index + 1] == ".":
        return True
    if (
        period_index > 0
        and period_index + 1 < len(window)
        and window[period_index - 1].isdigit()
        and window[period_index + 1].isdigit()
    ):
        return True
    return False


def _valid_cut_positions(window: str, min_pos: int) -> list[int]:
    """Collect candidate cut positions inside ``window`` at or after ``min_pos``."""
    positions: list[int] = []

    for sep in ("\n\n", "\n"):
        start = len(window)
        while start > min_pos:
            idx = window.rfind(sep, 0, start)
            if idx < 0:
                break
            if idx >= min_pos:
                positions.append(idx)
            start = idx

    for match in _SENTENCE_BOUNDARY.finditer(window):
        punct_index = match.start() - 1
        if punct_index < min_pos:
            continue
        if window[punct_index] == "." and _is_false_positive_period(window, punct_index):
            continue
        positions.append(match.start())

    for clause_char in (";", ":"):
        start = len(window)
        while start > min_pos:
            idx = window.rfind(clause_char, 0, start)
            if idx < 0:
                break
            positions.append(idx + 1)
            start = idx

    space = window.rfind(" ", min_pos, len(window))
    if space >= min_pos:
        positions.append(space)

    return positions


def truncate_social_post(
    text: str,
    max_chars: int = MAX_CHARS,
    *,
    min_keep_ratio: float = MIN_KEEP_RATIO,
) -> str:
    """Truncate using a boundary cascade and minimum retained fraction."""
    text = text.strip()
    if len(text) <= max_chars:
        return text

    window = text[:max_chars]
    min_pos = int(max_chars * min_keep_ratio)
    positions = _valid_cut_positions(window, min_pos)
    if positions:
        return window[: max(positions)].rstrip()

    return window.rstrip()


def truncate_pair(
    original: str,
    mirror: str,
    max_chars: int = MAX_CHARS,
    *,
    min_keep_ratio: float = MIN_KEEP_RATIO,
) -> tuple[str, str]:
    """Truncate original, then truncate mirror to the original's post-cut length."""
    original_truncated = truncate_social_post(
        original, max_chars, min_keep_ratio=min_keep_ratio
    )
    target_len = len(original_truncated)
    mirror_truncated = truncate_social_post(
        mirror, target_len, min_keep_ratio=min_keep_ratio
    )
    return original_truncated, mirror_truncated
