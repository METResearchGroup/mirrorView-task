"""Select, sample, and clone mixed 10 left and 10 right assignment rows.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow


def select_mixed_rows(
    rows: list[AssignmentRow], stance_by_post: dict[str, str]
) -> list[AssignmentRow]:
    raise NotImplementedError


def sample_mixed_feeds(
    mixed_rows: list[AssignmentRow], count: int, seed: int
) -> list[AssignmentRow]:
    raise NotImplementedError


def clone_mixed_feeds(
    sampled_rows: list[AssignmentRow], first_user_id: int, created_at: str
) -> list[AssignmentRow]:
    raise NotImplementedError


def concat_source_rows(
    base_rows: list[AssignmentRow], extra_rows: list[AssignmentRow]
) -> list[AssignmentRow]:
    raise NotImplementedError
