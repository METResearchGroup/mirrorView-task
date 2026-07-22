"""Long-table schema checks for original/mirror analysis meta."""

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
