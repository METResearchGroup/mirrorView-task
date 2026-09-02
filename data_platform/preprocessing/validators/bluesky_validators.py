from __future__ import annotations

from data_platform.preprocessing.content_filter_policy import (
    BLUESKY_POST_MAX_LENGTH,
    BLUESKY_POST_MIN_LENGTH,
)


def check_if_valid_post_length(text: str) -> bool:
    """Return True when Bluesky post text is within the preprocess length bounds."""
    return BLUESKY_POST_MIN_LENGTH <= len(text) <= BLUESKY_POST_MAX_LENGTH
