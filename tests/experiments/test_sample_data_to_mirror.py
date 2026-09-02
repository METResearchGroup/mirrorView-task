"""Tests for sample_data_to_mirror.normalize_mirrorview_df."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror import (
    normalize_mirrorview_df,
)

REDDIT_TEXT = "Reddit preprocess text for sampling."
TWITTER_TEXT = "Twitter preprocess text for sampling."
BLUESKY_TEXT = "Bluesky preprocess text for sampling."
REDDIT_BODY = "Raw Reddit body that must not be used."


def _reddit_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "post_reddit_id": "abc123",
        "comment_id": "xyz789",
        "text": REDDIT_TEXT,
        "toxicity_tier": "low",
        "political_stance": "left",
    }
    row.update(overrides)
    return row


def _twitter_row() -> dict[str, object]:
    return {
        "tweet_id": "123",
        "text": TWITTER_TEXT,
        "toxicity_tier": "low",
        "political_stance": "right",
    }


def _bluesky_row() -> dict[str, object]:
    return {
        "uri": "at://did:plc:ex/app.bsky.feed.post/a1",
        "text": BLUESKY_TEXT,
        "toxicity_tier": "medium",
        "political_stance": "left",
    }


class TestNormalizeMirrorviewDf:
    """Tests for normalize_mirrorview_df()."""

    def test_reddit_uses_preprocess_text_without_body(self) -> None:
        """Reddit original_text comes from text even when body is absent."""
        df_raw = pd.DataFrame([_reddit_row()])

        result = normalize_mirrorview_df(df_raw, integration="reddit")

        assert result.iloc[0]["original_text"] == REDDIT_TEXT
        assert result.iloc[0]["unique_reddit_id"] == "reddit_abc123_xyz789"

    def test_reddit_raises_when_text_is_missing_even_if_body_is_present(self) -> None:
        """Reddit does not fall back to body when text is missing."""
        row = _reddit_row(body=REDDIT_BODY)
        del row["text"]
        df_raw = pd.DataFrame([row])

        with pytest.raises(ValueError, match="missing required column `text`"):
            normalize_mirrorview_df(df_raw, integration="reddit")

    def test_reddit_prefers_text_when_body_differs(self) -> None:
        """Reddit original_text uses text, not a different body on the same row."""
        df_raw = pd.DataFrame([_reddit_row(body=REDDIT_BODY)])

        result = normalize_mirrorview_df(df_raw, integration="reddit")

        assert result.iloc[0]["original_text"] == REDDIT_TEXT
        assert result.iloc[0]["original_text"] != REDDIT_BODY

    def test_twitter_uses_preprocess_text(self) -> None:
        """Twitter original_text still comes from text."""
        df_raw = pd.DataFrame([_twitter_row()])

        result = normalize_mirrorview_df(df_raw, integration="twitter")

        assert result.iloc[0]["original_text"] == TWITTER_TEXT

    def test_bluesky_uses_preprocess_text(self) -> None:
        """Bluesky original_text still comes from text."""
        df_raw = pd.DataFrame([_bluesky_row()])

        result = normalize_mirrorview_df(df_raw, integration="bluesky")

        assert result.iloc[0]["original_text"] == BLUESKY_TEXT
