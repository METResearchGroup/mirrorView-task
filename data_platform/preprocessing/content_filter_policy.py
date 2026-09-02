"""Length and language policy for stimuli-ready text at preprocess.

Bluesky posts must be between 100 and 300 characters, and they must be English.
Twitter posts must be between 50 and 280 characters, and they must be English.
Reddit comments must be at least 30 characters, they have no maximum, and they
must be English. English is checked with check_if_text_english on every
platform.

Reddit ingest still has a fetch-time minimum body length. That ingest setting
is not this policy.
"""

from __future__ import annotations

BLUESKY_POST_MIN_LENGTH: int = 100
BLUESKY_POST_MAX_LENGTH: int = 300
TWITTER_POST_MIN_LENGTH: int = 50
TWITTER_POST_MAX_LENGTH: int = 280
REDDIT_COMMENT_MIN_LENGTH: int = 30
