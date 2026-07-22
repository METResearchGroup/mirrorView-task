"""Pure helpers for post-level split expansion and long-table schema checks."""

from __future__ import annotations

import pandas as pd


def assert_long_table_schema(meta: pd.DataFrame) -> None:
    """Raise if long original/mirror meta violates frozen contracts."""
    required = {"post_id", "text_role", "is_mirrored", "label"}
    missing = required - set(meta.columns)
    if missing:
        raise KeyError(f"meta missing columns: {sorted(missing)}")

    df = meta.copy()
    df["post_id"] = df["post_id"].astype(str)
    df["text_role"] = df["text_role"].astype(str)
    df["is_mirrored"] = df["is_mirrored"].astype(int)
    df["label"] = df["label"].astype(int)

    counts = df.groupby("post_id").size()
    bad_counts = counts[counts != 2]
    if len(bad_counts):
        sample = bad_counts.index[:5].tolist()
        raise AssertionError(
            f"Expected exactly 2 rows per post_id; bad_count={len(bad_counts)} sample={sample}"
        )

    roles = set(df["text_role"].unique())
    if roles != {"original_text", "mirror_text"}:
        raise AssertionError(f"Unexpected text_role values: {sorted(roles)}")

    if set(df["is_mirrored"].unique()) != {0, 1}:
        raise AssertionError(f"is_mirrored must be {{0,1}}; got {sorted(df['is_mirrored'].unique())}")

    orig_ok = ((df["text_role"] == "original_text") & (df["is_mirrored"] == 0)).sum()
    mir_ok = ((df["text_role"] == "mirror_text") & (df["is_mirrored"] == 1)).sum()
    if int(orig_ok) != int((df["text_role"] == "original_text").sum()):
        raise AssertionError("is_mirrored must be 0 iff text_role==original_text")
    if int(mir_ok) != int((df["text_role"] == "mirror_text").sum()):
        raise AssertionError("is_mirrored must be 1 iff text_role==mirror_text")

    label_nunique = df.groupby("post_id")["label"].nunique()
    if (label_nunique != 1).any():
        bad = label_nunique[label_nunique != 1].index[:5].tolist()
        raise AssertionError(f"label must be identical on both rows of a post; sample={bad}")


def expand_post_split_to_row_masks(
    meta: pd.DataFrame,
    train_post_ids: list[str] | set[str],
    test_post_ids: list[str] | set[str],
) -> tuple[pd.Series, pd.Series]:
    """Expand post-level IDs to boolean row masks (both roles included).

    Returns ``(train_mask, test_mask)`` aligned to ``meta`` rows.
    """
    assert_long_table_schema(meta)
    train_set = {str(x) for x in train_post_ids}
    test_set = {str(x) for x in test_post_ids}

    if train_set & test_set:
        raise AssertionError(
            f"pair leakage: train∩test post_ids non-empty "
            f"(n={len(train_set & test_set)})"
        )

    post_ids = meta["post_id"].astype(str)
    all_ids = set(post_ids.unique())
    if train_set | test_set != all_ids:
        missing = all_ids - (train_set | test_set)
        extra = (train_set | test_set) - all_ids
        raise AssertionError(
            f"split coverage failure missing={len(missing)} extra={len(extra)}"
        )

    train_mask = post_ids.isin(train_set)
    test_mask = post_ids.isin(test_set)

    if bool((train_mask & test_mask).any()):
        raise AssertionError("row masks overlap — pair leakage")

    n_train_posts = len(train_set)
    n_test_posts = len(test_set)
    if int(train_mask.sum()) != 2 * n_train_posts:
        raise AssertionError(
            f"n_rows_train={int(train_mask.sum())} != 2*n_train_posts={2 * n_train_posts}"
        )
    if int(test_mask.sum()) != 2 * n_test_posts:
        raise AssertionError(
            f"n_rows_test={int(test_mask.sum())} != 2*n_test_posts={2 * n_test_posts}"
        )

    # No post has rows in both splits (redundant with set disjointness + expand, but explicit).
    train_posts_in_rows = set(post_ids[train_mask].unique())
    test_posts_in_rows = set(post_ids[test_mask].unique())
    if train_posts_in_rows & test_posts_in_rows:
        raise AssertionError("post appears in both row masks")

    return train_mask, test_mask


def assert_no_pair_leakage(
    meta: pd.DataFrame,
    train_mask: pd.Series | list[bool],
    test_mask: pd.Series | list[bool],
) -> None:
    """Detect if any post_id has rows on both sides of a split."""
    train_m = pd.Series(train_mask, index=meta.index).astype(bool)
    test_m = pd.Series(test_mask, index=meta.index).astype(bool)
    post_ids = meta["post_id"].astype(str)
    train_posts = set(post_ids[train_m].unique())
    test_posts = set(post_ids[test_m].unique())
    overlap = train_posts & test_posts
    if overlap:
        raise AssertionError(
            f"pair leakage: {len(overlap)} post_ids have rows in both splits; "
            f"sample={sorted(overlap)[:5]}"
        )
