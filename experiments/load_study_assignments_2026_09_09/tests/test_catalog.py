"""Tests for build_assigned_catalog()."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments.load_study_assignments_2026_09_09.catalog import build_assigned_catalog
from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CATALOG_COLUMNS,
    CONDITION,
    EMPTY_POLITICAL_PARTY,
    MIRROR_TEXT_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    POSTS_PER_FEED,
    POST_ID_COLUMN,
    STANCE_COLUMN,
    STANCE_LEFT,
    STANCE_RIGHT,
    TOXICITY_COLUMN,
)

CREATED_AT = "2026_09_04-14:27:30"
TOXICITY_LOW = "sample_low_toxicity"


def _catalog_row(
    post_id: str,
    stance: str,
    original_text: str = "original",
    mirrored_text: str = "mirror",
) -> dict[str, str]:
    return {
        POST_ID_COLUMN: post_id,
        ORIGINAL_TEXT_COLUMN: original_text,
        TOXICITY_COLUMN: TOXICITY_LOW,
        STANCE_COLUMN: stance,
        MIRROR_TEXT_COLUMN: mirrored_text,
    }


def _catalog_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(CATALOG_COLUMNS))


def _assignment(post_ids: list[str]) -> AssignmentRow:
    return AssignmentRow(
        id="democrat-training_assisted-0001",
        assigned_post_ids=json.dumps(post_ids),
        political_party="democrat",
        condition=CONDITION,
        created_at=CREATED_AT,
    )


def _twenty_ids(prefix: str) -> list[str]:
    return [f"{prefix}-{index}" for index in range(POSTS_PER_FEED)]


class TestBuildAssignedCatalog:
    """Tests for build_assigned_catalog()."""

    def test_raises_when_assigned_id_is_absent(self) -> None:
        """Verifies an assigned id missing from both catalogs is rejected."""
        old_catalog = _catalog_frame([_catalog_row("old-1", STANCE_LEFT)])
        new_catalog = _catalog_frame([_catalog_row("new-1", STANCE_RIGHT)])
        rows = [_assignment(["missing"] * POSTS_PER_FEED)]

        with pytest.raises(ValueError, match="missing catalog id"):
            build_assigned_catalog(old_catalog, new_catalog, rows)

    def test_raises_when_id_is_duplicated_across_catalogs(self) -> None:
        """Verifies a post id present in both catalogs is rejected."""
        shared = _catalog_row("shared", STANCE_LEFT)
        old_catalog = _catalog_frame([shared])
        new_catalog = _catalog_frame([shared])
        rows = [_assignment(["shared"] * POSTS_PER_FEED)]

        with pytest.raises(ValueError, match="duplicate catalog id"):
            build_assigned_catalog(old_catalog, new_catalog, rows)

    def test_raises_when_mirror_text_is_empty(self) -> None:
        """Verifies assigned rows with empty mirrored_text are rejected."""
        post_ids = _twenty_ids("post")
        old_rows = [
            _catalog_row(post_id, STANCE_LEFT, mirrored_text="") for post_id in post_ids
        ]
        old_catalog = _catalog_frame(old_rows)
        new_catalog = _catalog_frame([])
        rows = [_assignment(post_ids)]

        with pytest.raises(ValueError, match="empty mirrored_text"):
            build_assigned_catalog(old_catalog, new_catalog, rows)

    def test_returns_only_assigned_ids_sorted_by_post_id(self) -> None:
        """Verifies unused catalog rows are dropped and assigned ids are sorted."""
        post_ids = _twenty_ids("keep")
        old_rows = [_catalog_row(post_id, STANCE_LEFT) for post_id in post_ids]
        old_rows.append(_catalog_row("unused", STANCE_RIGHT))
        old_catalog = _catalog_frame(old_rows)
        new_catalog = _catalog_frame([])
        result = build_assigned_catalog(old_catalog, new_catalog, [_assignment(post_ids)])

        assert result[POST_ID_COLUMN].tolist() == sorted(post_ids)
        assert "unused" not in set(result[POST_ID_COLUMN])
        assert list(result.columns) == list(CATALOG_COLUMNS)
