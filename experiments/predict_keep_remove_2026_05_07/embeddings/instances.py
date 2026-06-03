"""Build one row per (post_id, text_role, text) for embedding and joins."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_2026_05_07.embeddings.text_hash import (
    text_hash,
)

TEXT_ROLE_ORIGINAL = "original_text"
TEXT_ROLE_MIRROR = "mirror_text"


def build_text_instances_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return unique text instances needed to cover every training row.

    ``post_id`` alone is not unique in linked-fate data: the same post can appear
    with different ``mirror_text`` strings. Keys are
    ``(post_id, text_role, text_hash)``.
    """
    required = {"post_id", "original_text", "mirror_text"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"DataFrame missing columns for text instances: {sorted(missing)}")

    base = df[list(required)].copy()
    base["post_id"] = base["post_id"].astype(str)

    orig = base[["post_id", "original_text"]].copy()
    orig = orig.rename(columns={"original_text": "text"})
    orig["text_role"] = TEXT_ROLE_ORIGINAL

    mirr = base[["post_id", "mirror_text"]].copy()
    mirr = mirr.rename(columns={"mirror_text": "text"})
    mirr["text_role"] = TEXT_ROLE_MIRROR

    out = pd.concat([orig, mirr], ignore_index=True)
    out["text"] = out["text"].fillna("").astype(str)
    out["text_hash"] = out["text"].map(text_hash)
    out = out.drop_duplicates(subset=["post_id", "text_role", "text_hash"], keep="first")
    out = out.reset_index(drop=True)
    return out


def add_text_hash_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``original_text_hash`` and ``mirror_text_hash`` for embedding joins."""
    out = df.copy()
    if "original_text" not in out.columns or "mirror_text" not in out.columns:
        raise KeyError("DataFrame must include 'original_text' and 'mirror_text'")
    out["original_text_hash"] = (
        out["original_text"].fillna("").astype(str).map(text_hash)
    )
    out["mirror_text_hash"] = (
        out["mirror_text"].fillna("").astype(str).map(text_hash)
    )
    return out
