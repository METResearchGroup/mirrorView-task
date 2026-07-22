"""Build long analysis table: original + mirror Titan embeddings (2N × 256).

Loads both text roles from the local embedding cache only (prefer worktree cache;
optional Documents backup). Does **not** call Bedrock / S3 / DynamoDB.

Run from repo root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/build_table.py

Label convention (from PKR dataloader): ``label`` / ``keep_remove_label`` is
``0=keep``, ``1=remove`` (modal decision; ties → remove). Dataloader exposes
``message_id``; this script renames it to ``post_id``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    ANALYSIS_DIR,
    ANALYSIS_META_PATH,
    ANALYSIS_TABLE_PATH,
    EMBEDDING_DIM,
    EMBEDDING_MATRIX_PATH,
    FEATURE_SET,
    MAIN_REPO_EMBEDDING_CACHE,
    PROGRESS_UPDATES_PATH,
    WORKTREE_EMBEDDING_CACHE,
)
from analyze.split_lib import assert_long_table_schema  # noqa: E402
from experiments.predict_keep_remove_2026_07_01.data.dataloader import (  # noqa: E402
    Dataloader,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (  # noqa: E402
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from experiments.simplified_predict_remove_2026_05_13.generate_embeddings import (  # noqa: E402
    TEXT_ROLE_MIRROR,
    TEXT_ROLE_ORIGINAL,
)
from lib.aws.embedding_identity import embedding_identity_sha256  # noqa: E402


def resolve_embedding_cache_dir() -> Path:
    """Prefer worktree cache, then optional main-repo backup. Fail loud if neither."""
    for candidate in (WORKTREE_EMBEDDING_CACHE, MAIN_REPO_EMBEDDING_CACHE):
        emb_dir = candidate / "embeddings"
        if emb_dir.is_dir() and any(emb_dir.glob("*.npy")):
            return candidate
    raise FileNotFoundError(
        "No populated embedding_cache found. Expected one of:\n"
        f"  {WORKTREE_EMBEDDING_CACHE}\n"
        f"  {MAIN_REPO_EMBEDDING_CACHE}\n"
        "Populate via local filesystem copy of Titan .npy files "
        "(no S3 / DynamoDB / Bedrock in this experiment)."
    )


def _cache_npy_path(cache_dir: Path, embedding_id: str) -> Path:
    return cache_dir / "embeddings" / f"{embedding_id}.npy"


def load_training_posts() -> pd.DataFrame:
    """One row per post from PKR dataloader; rename to post_id / label."""
    raw = Dataloader().load_training_dataframe()
    if "message_id" not in raw.columns:
        raise KeyError("Expected message_id from Dataloader.load_training_dataframe()")
    required = {"original_text", "mirror_text", "keep_remove_label"}
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"training dataframe missing columns: {sorted(missing)}")

    df = pd.DataFrame(
        {
            "post_id": raw["message_id"].astype(str),
            "original_text": raw["original_text"].astype(str),
            "mirror_text": raw["mirror_text"].astype(str),
            "label": raw["keep_remove_label"].astype(int),
        }
    )
    if df["post_id"].duplicated().any():
        n = int(df["post_id"].duplicated().sum())
        raise ValueError(f"Duplicate post_id in training dataframe: {n}")
    return df


def load_original_and_mirror_from_local_cache(
    df: pd.DataFrame,
    *,
    cache_dir: Path,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
) -> tuple[dict[tuple[str, str], list[float]], dict[str, int | list[str]]]:
    """Load original + mirror vectors from local ``embeddings/*.npy`` only (no AWS).

    Returns lookup keyed by ``(post_id, text_role)`` and hit/miss stats.
    Raises ``FileNotFoundError`` if any role embedding is missing locally.
    """
    if not {"post_id", "original_text", "mirror_text"}.issubset(df.columns):
        raise KeyError("df must include post_id, original_text, mirror_text")

    lookup: dict[tuple[str, str], list[float]] = {}
    hits = 0
    misses: list[str] = []
    id_to_vec: dict[str, np.ndarray] = {}

    def _load_one(pid: str, text: str, role: str) -> None:
        nonlocal hits
        key = (pid, role)
        if key in lookup:
            return
        eid = embedding_identity_sha256(
            text, model_id=model_id, dimensions=dimensions, normalize=normalize
        )
        if eid in id_to_vec:
            vec = id_to_vec[eid]
            hits += 1
        else:
            path = _cache_npy_path(cache_dir, eid)
            if not path.exists():
                misses.append(f"{pid}:{role}")
                return
            vec = np.load(path)
            id_to_vec[eid] = vec
            hits += 1
        arr = np.asarray(vec, dtype=np.float64).ravel()
        if arr.shape[0] != dimensions:
            raise ValueError(
                f"Unexpected embedding dim for post_id={pid} role={role}: "
                f"{arr.shape[0]} != {dimensions}"
            )
        lookup[key] = [float(x) for x in arr.tolist()]

    for _, row in df.iterrows():
        pid = str(row["post_id"])
        _load_one(pid, str(row["original_text"]), TEXT_ROLE_ORIGINAL)
        _load_one(pid, str(row["mirror_text"]), TEXT_ROLE_MIRROR)

    stats: dict[str, int | list[str]] = {
        "total_posts": int(df["post_id"].nunique()),
        "cache_hits": hits,
        "cache_misses": len(misses),
        "miss_sample": misses[:10],
    }
    if misses:
        raise FileNotFoundError(
            f"Local embedding cache missing {len(misses)} vectors "
            f"(original and/or mirror). sample={misses[:5]} cache_dir={cache_dir}"
        )
    return lookup, stats


def build_long_table(
    posts: pd.DataFrame,
    lookup: dict[tuple[str, str], list[float]],
) -> tuple[pd.DataFrame, np.ndarray]:
    """Stack original then mirror rows; stable sort by (post_id, is_mirrored)."""
    rows: list[dict] = []
    for _, post in posts.iterrows():
        pid = str(post["post_id"])
        label = int(post["label"])
        for role, is_mirrored in (
            (TEXT_ROLE_ORIGINAL, 0),
            (TEXT_ROLE_MIRROR, 1),
        ):
            vec = lookup.get((pid, role))
            if vec is None:
                raise KeyError(f"Missing embedding for post_id={pid} role={role}")
            rows.append(
                {
                    "post_id": pid,
                    "text_role": role,
                    "is_mirrored": is_mirrored,
                    "label": label,
                    "embedding": np.asarray(vec, dtype=np.float64),
                }
            )

    table = pd.DataFrame(rows)
    table = table.sort_values(["post_id", "is_mirrored"], kind="mergesort").reset_index(
        drop=True
    )
    assert_long_table_schema(table)
    X = np.vstack(table["embedding"].to_list()).astype(np.float64, copy=False)
    if X.shape != (len(table), EMBEDDING_DIM):
        raise ValueError(f"Unexpected X shape {X.shape}; expected ({len(table)}, {EMBEDDING_DIM})")
    return table, X


def write_artifacts(table: pd.DataFrame, X: np.ndarray, meta: dict) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(ANALYSIS_TABLE_PATH, index=False)
    np.save(EMBEDDING_MATRIX_PATH, X.astype(np.float64, copy=False))
    table[["post_id", "text_role", "is_mirrored", "label"]].to_csv(
        ANALYSIS_META_PATH, index=False
    )
    meta_path = ANALYSIS_DIR / "analysis_table_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def append_progress(lines: list[str]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PROGRESS_UPDATES_PATH.is_file():
        existing = PROGRESS_UPDATES_PATH.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    PROGRESS_UPDATES_PATH.write_text(existing + block, encoding="utf-8")


def main() -> int:
    print("Loading training posts via Dataloader()...")
    posts = load_training_posts()
    n_posts = len(posts)
    print(f"  n_posts={n_posts}")

    cache_dir = resolve_embedding_cache_dir()
    print(f"Using embedding cache: {cache_dir}")

    lookup, cache_stats = load_original_and_mirror_from_local_cache(
        posts, cache_dir=cache_dir
    )
    table, X = build_long_table(posts, lookup)

    meta = {
        "n_posts": n_posts,
        "n_rows": int(len(table)),
        "embedding_dim": EMBEDDING_DIM,
        "feature_set": FEATURE_SET,
        "cache_dir": str(cache_dir),
        "cache_stats": cache_stats,
        "model_id": BEDROCK_MODEL_ID,
        "normalize": True,
        "aws_called": False,
        "loader": "local_npy_cache_original_and_mirror",
        "label_convention": "0=keep, 1=remove (modal; ties→remove)",
    }
    write_artifacts(table, X, meta)

    print(
        f"n_posts={n_posts} n_rows={len(table)} "
        f"cache_hits={cache_stats['cache_hits']} cache_misses={cache_stats['cache_misses']}"
    )
    print(f"Wrote {ANALYSIS_TABLE_PATH}")
    print(f"Wrote {EMBEDDING_MATRIX_PATH} shape={X.shape}")
    print(f"Wrote {ANALYSIS_META_PATH}")

    append_progress(
        [
            "## Build analysis table (original + mirror long)",
            "",
            f"- Posts: `{n_posts}` from PKR `Dataloader().load_training_dataframe()`",
            f"- Feature set: `{FEATURE_SET}` / Titan `{BEDROCK_MODEL_ID}` dims={EMBEDDING_DIM}",
            f"- Embedding cache: `{cache_dir}` (local `.npy` only; AWS not called)",
            f"- Cache hits={cache_stats['cache_hits']} misses={cache_stats['cache_misses']}",
            f"- Artifacts:",
            f"  - `{ANALYSIS_TABLE_PATH}` — scalars + `embedding` list; rows={len(table)}",
            f"  - `{EMBEDDING_MATRIX_PATH}` — shape `{tuple(X.shape)}`",
            f"  - `{ANALYSIS_META_PATH}` — `post_id,text_role,is_mirrored,label`",
            f"  - `{ANALYSIS_DIR / 'analysis_table_meta.json'}`",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
