"""Attach precomputed embeddings to a trial-level training DataFrame."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.predict_keep_remove_2026_05_07.embeddings.instances import (
    TEXT_ROLE_MIRROR,
    TEXT_ROLE_ORIGINAL,
    add_text_hash_columns,
)


def join_embeddings_to_dataframe(
    df: pd.DataFrame,
    embeddings_parquet: Path | str,
    *,
    orig_vector_column: str = "embedding_original_text",
    mirr_vector_column: str = "embedding_mirror_text",
) -> pd.DataFrame:
    """Left-join embedding vectors using ``(post_id, text_role, text_hash)``.

    ``embeddings_parquet`` must be the long table produced by the compute job
    (columns include ``post_id``, ``text_role``, ``text_hash``, ``embedding``).
    """
    path = Path(embeddings_parquet)
    if not path.is_file():
        raise FileNotFoundError(f"Embeddings parquet not found: {path}")

    inst = pd.read_parquet(path)
    required = {"post_id", "text_role", "text_hash", "embedding"}
    missing = required - set(inst.columns)
    if missing:
        raise KeyError(f"Embeddings table missing columns: {sorted(missing)}")

    inst = inst.copy()
    inst["post_id"] = inst["post_id"].astype(str)

    orig = inst.loc[inst["text_role"] == TEXT_ROLE_ORIGINAL, list(required)].copy()
    orig = orig.rename(
        columns={
            "text_hash": "original_text_hash",
            "embedding": orig_vector_column,
        }
    ).drop(columns=["text_role"])

    mirr = inst.loc[inst["text_role"] == TEXT_ROLE_MIRROR, list(required)].copy()
    mirr = mirr.rename(
        columns={
            "text_hash": "mirror_text_hash",
            "embedding": mirr_vector_column,
        }
    ).drop(columns=["text_role"])

    out = add_text_hash_columns(df)
    out["post_id"] = out["post_id"].astype(str)

    out = out.merge(orig, on=["post_id", "original_text_hash"], how="left")
    out = out.merge(mirr, on=["post_id", "mirror_text_hash"], how="left")
    return out
