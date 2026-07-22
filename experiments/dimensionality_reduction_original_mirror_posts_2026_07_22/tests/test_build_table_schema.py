"""Long-matrix schema / shape invariants (fixture-only; no Titan cache)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiments.dimensionality_reduction_original_mirror_posts_2026_07_22.analyze.split_lib import (
    assert_long_table_schema,
)


def test_matrix_shape_2n_by_256() -> None:
    n_posts = 5
    meta_rows = []
    for i in range(n_posts):
        for role, is_m in (("original_text", 0), ("mirror_text", 1)):
            meta_rows.append(
                {
                    "post_id": f"x{i}",
                    "text_role": role,
                    "is_mirrored": is_m,
                    "label": i % 2,
                }
            )
    meta = pd.DataFrame(meta_rows)
    assert_long_table_schema(meta)
    X = np.zeros((len(meta), 256), dtype=np.float64)
    assert X.shape == (2 * n_posts, 256)
    assert len(meta) == 2 * meta["post_id"].nunique()
    assert set(meta["is_mirrored"]) == {0, 1}


def test_lda_target_values_are_01() -> None:
    meta = pd.DataFrame(
        {
            "post_id": ["a", "a", "b", "b"],
            "text_role": [
                "original_text",
                "mirror_text",
                "original_text",
                "mirror_text",
            ],
            "is_mirrored": [0, 1, 0, 1],
            "label": [0, 0, 1, 1],
        }
    )
    assert_long_table_schema(meta)
    y = meta["is_mirrored"].to_numpy()
    assert set(y.tolist()) == {0, 1}


def test_wrong_row_count_per_post_fails() -> None:
    meta = pd.DataFrame(
        {
            "post_id": ["a", "a", "a"],
            "text_role": ["original_text", "mirror_text", "mirror_text"],
            "is_mirrored": [0, 1, 1],
            "label": [0, 0, 0],
        }
    )
    with pytest.raises(AssertionError, match="exactly 2 rows"):
        assert_long_table_schema(meta)
