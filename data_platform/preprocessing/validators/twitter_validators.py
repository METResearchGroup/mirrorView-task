from __future__ import annotations

import re

from data_platform.preprocessing.content_filter_policy import (
    TWITTER_POST_MAX_LENGTH,
    TWITTER_POST_MIN_LENGTH,
)
from data_platform.preprocessing.validators.validators import check_if_post_has_no_urls

_TCO_URL_PATTERN = re.compile(r"https?://t\.co/\S+")


def strip_tco_links(text: str) -> str:
    return _TCO_URL_PATTERN.sub("", text)


def has_tco_links(text: str) -> bool:
    return _TCO_URL_PATTERN.search(text) is not None


def check_if_valid_twitter_post_length(text: str) -> bool:
    return TWITTER_POST_MIN_LENGTH <= len(text) <= TWITTER_POST_MAX_LENGTH


def check_if_twitter_text_has_no_external_urls(text: str) -> bool:
    return check_if_post_has_no_urls(strip_tco_links(text))
