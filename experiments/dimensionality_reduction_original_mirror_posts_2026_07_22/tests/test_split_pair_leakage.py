"""Pair-leakage and post-level split expansion tests (no embedding cache required).

Helpers under test: ``analyze.split_lib.expand_post_split_to_row_masks``,
``assert_long_table_schema``, ``assert_no_pair_leakage``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.dimensionality_reduction_original_mirror_posts_2026_07_22.analyze.split_lib import (
    assert_long_table_schema,
    assert_no_pair_leakage,
    expand_post_split_to_row_masks,
)


def _synthetic_meta(n_posts: int = 10) -> pd.DataFrame:
    rows: list[dict] = []
    for i in range(n_posts):
        pid = f"p{i:03d}"
        label = i % 2  # balanced keep/remove
        rows.append(
            {
                "post_id": pid,
                "text_role": "original_text",
                "is_mirrored": 0,
                "label": label,
            }
        )
        rows.append(
            {
                "post_id": pid,
                "text_role": "mirror_text",
                "is_mirrored": 1,
                "label": label,
            }
        )
    return pd.DataFrame(rows)


def test_long_table_schema_ok() -> None:
    meta = _synthetic_meta(10)
    assert_long_table_schema(meta)


def test_is_mirrored_text_role_consistency_fails() -> None:
    meta = _synthetic_meta(4)
    meta.loc[meta["text_role"] == "mirror_text", "is_mirrored"] = 0
    with pytest.raises(AssertionError, match="is_mirrored"):
        assert_long_table_schema(meta)


def test_post_level_expand_no_leakage() -> None:
    meta = _synthetic_meta(10)
    train_ids = [f"p{i:03d}" for i in range(8)]
    test_ids = [f"p{i:03d}" for i in range(8, 10)]
    train_mask, test_mask = expand_post_split_to_row_masks(meta, train_ids, test_ids)
    assert int(train_mask.sum()) == 16
    assert int(test_mask.sum()) == 4
    assert_no_pair_leakage(meta, train_mask, test_mask)
    # Each post contributes both roles to exactly one side.
    for pid in train_ids:
        rows = meta.loc[meta["post_id"] == pid]
        assert train_mask.loc[rows.index].all()
        assert not test_mask.loc[rows.index].any()


def test_deliberate_row_level_split_detected() -> None:
    """A bad row-level split that puts original on train and mirror on test must fail."""
    meta = _synthetic_meta(4)
    # Put odd rows (mirrors) on test, even (originals) on train — classic pair leak.
    train_mask = (meta["is_mirrored"] == 0)
    test_mask = (meta["is_mirrored"] == 1)
    with pytest.raises(AssertionError, match="pair leakage"):
        assert_no_pair_leakage(meta, train_mask, test_mask)


def test_expand_rejects_overlapping_post_ids() -> None:
    meta = _synthetic_meta(6)
    train_ids = ["p000", "p001", "p002", "p003"]
    test_ids = ["p003", "p004", "p005"]  # p003 overlaps
    with pytest.raises(AssertionError, match="pair leakage|overlap"):
        expand_post_split_to_row_masks(meta, train_ids, test_ids)
