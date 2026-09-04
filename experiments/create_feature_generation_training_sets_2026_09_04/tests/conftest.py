"""Shared pytest fixtures for training-set join tests."""

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def bluesky_dataset_dir(tmp_path: Path) -> Path:
    """Build a minimal Bluesky dataset with one preprocessed run."""
    dataset_dir = tmp_path / "bluesky_sample"
    run_dir = dataset_dir / "preprocessed" / "2026_09_04-10:00:00"
    run_dir.mkdir(parents=True)
    posts = pd.DataFrame(
        {
            "uri": ["at://did:plc:abc/app.bsky.feed.post/1"],
            "text": ["hello bluesky"],
        }
    )
    posts.to_csv(run_dir / "posts.csv", index=False)
    return dataset_dir


@pytest.fixture
def twitter_dataset_dir(tmp_path: Path) -> Path:
    """Build a minimal Twitter dataset with tweet_id keyed records."""
    dataset_dir = tmp_path / "twitter_sample"
    run_dir = dataset_dir / "preprocessed" / "2026_09_04-10:00:00"
    run_dir.mkdir(parents=True)
    posts = pd.DataFrame(
        {
            "tweet_id": [123456789],
            "text": ["hello twitter"],
        }
    )
    posts.to_csv(run_dir / "posts.csv", index=False)
    return dataset_dir


@pytest.fixture
def reddit_dataset_dir(tmp_path: Path) -> Path:
    """Build a minimal Reddit dataset with comment_fullname and body."""
    dataset_dir = tmp_path / "reddit_sample"
    run_dir = dataset_dir / "preprocessed" / "2026_09_04-10:00:00"
    run_dir.mkdir(parents=True)
    comments = pd.DataFrame(
        {
            "comment_fullname": ["t1_abc123"],
            "body": ["hello reddit"],
        }
    )
    comments.to_csv(run_dir / "comments.csv", index=False)
    return dataset_dir
