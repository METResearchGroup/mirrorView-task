"""Assign remaining labels to 20-post study feeds.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import pandas as pd


def count_feed_kinds(left_remaining: int, right_remaining: int) -> object:
    raise NotImplementedError


def preferred_cell_counts(feed_kind: object, index_within_kind: int) -> tuple[int, ...]:
    raise NotImplementedError


def assign_feeds(joined: pd.DataFrame) -> list[object]:
    raise NotImplementedError


def shuffle_feed(post_ids: list[str], user_id: int) -> list[str]:
    raise NotImplementedError
