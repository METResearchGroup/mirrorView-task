"""Build analysis matrices: human labels + original/mirrored Titan embeddings.

Loads both original-post and mirrored-post embeddings from the local Titan
embedding cache (prefer cache hits; does not call Bedrock).

Run from repo root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_labels_2026_07_22/analyze/build_table.py
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
    ANALYSIS_TABLE_META_PATH,
    EMBEDDING_DIM,
    LABELS_CSV_PATH,
    MAIN_REPO_EMBEDDING_CACHE,
    WORKTREE_EMBEDDING_CACHE,
    X_MIRRORED_PATH,
    X_ORIGINAL_PATH,
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
    """Prefer worktree cache, then main-repo populated cache."""
    for candidate in (WORKTREE_EMBEDDING_CACHE, MAIN_REPO_EMBEDDING_CACHE):
        emb_dir = candidate / "embeddings"
        if emb_dir.is_dir() and any(emb_dir.glob("*.npy")):
            return candidate
    raise FileNotFoundError(
        "No populated embedding_cache found. Expected one of:\n"
        f"  {WORKTREE_EMBEDDING_CACHE}\n"
        f"  {MAIN_REPO_EMBEDDING_CACHE}\n"
        "Populate via parent-study train scripts / generate.py, or pass a populated cache."
    )


def _cache_npy_path(cache_dir: Path, embedding_id: str) -> Path:
    return cache_dir / "embeddings" / f"{embedding_id}.npy"


def load_original_and_mirror_from_local_cache(
    df: pd.DataFrame,
    *,
    cache_dir: Path,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
) -> tuple[dict[tuple[str, str], list[float]], dict[str, object]]:
    """Load original + mirrored vectors from local ``embeddings/*.npy`` only (no AWS).

    Returns lookup keyed by ``(post_id, text_role)`` and hit/miss stats.
    Raises ``FileNotFoundError`` if any required embedding is missing locally.
    """
    required_cols = {"post_id", "original_text", "mirrored_text"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise KeyError(f"df must include {sorted(required_cols)}; missing={sorted(missing_cols)}")

    lookup: dict[tuple[str, str], list[float]] = {}
    hits = 0
    miss_original: list[str] = []
    miss_mirrored: list[str] = []
    id_to_vec: dict[str, np.ndarray] = {}

    def _load_one(pid: str, text: str, role: str, miss_list: list[str]) -> None:
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
                miss_list.append(pid)
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
        _load_one(pid, str(row["original_text"]), TEXT_ROLE_ORIGINAL, miss_original)
        _load_one(pid, str(row["mirrored_text"]), TEXT_ROLE_MIRROR, miss_mirrored)

    stats: dict[str, object] = {
        "total_posts": int(df["post_id"].nunique()),
        "cache_hits": hits,
        "cache_misses_original": len(miss_original),
        "cache_misses_mirrored": len(miss_mirrored),
        "miss_original_post_ids_sample": miss_original[:10],
        "miss_mirrored_post_ids_sample": miss_mirrored[:10],
    }
    if miss_original or miss_mirrored:
        raise FileNotFoundError(
            f"Local embedding cache missing vectors: "
            f"original={len(miss_original)} mirrored={len(miss_mirrored)}. "
            f"sample_original={miss_original[:5]} sample_mirrored={miss_mirrored[:5]} "
            f"cache_dir={cache_dir}"
        )
    return lookup, stats


def load_labels() -> pd.DataFrame:
    if not LABELS_CSV_PATH.is_file():
        raise FileNotFoundError(f"Missing labels CSV: {LABELS_CSV_PATH}")
    df = pd.read_csv(LABELS_CSV_PATH)
    required = {"post_id", "original_text", "mirrored_text", "label"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise KeyError(f"labels CSV missing columns: {sorted(missing_cols)}")

    df = df.copy()
    df["post_id"] = df["post_id"].astype(str)
    if df["post_id"].duplicated().any():
        n = int(df["post_id"].duplicated().sum())
        raise ValueError(f"Duplicate post_id rows in labels CSV: {n}")

    df["label"] = df["label"].astype(int)
    bad = ~df["label"].isin([0, 1])
    if bad.any():
        raise ValueError(f"label must be 0/1; found extras={df.loc[bad, 'label'].unique().tolist()}")
    return df


def build_matrices(
    labels: pd.DataFrame,
    *,
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame, dict]:
    lookup, cache_stats = load_original_and_mirror_from_local_cache(labels, cache_dir=cache_dir)

    X_orig = np.empty((len(labels), EMBEDDING_DIM), dtype=np.float64)
    X_mir = np.empty((len(labels), EMBEDDING_DIM), dtype=np.float64)
    post_ids: list[str] = []
    y_label: list[int] = []

    for i, row in enumerate(labels.itertuples(index=False)):
        pid = str(row.post_id)
        vo = lookup.get((pid, TEXT_ROLE_ORIGINAL))
        vm = lookup.get((pid, TEXT_ROLE_MIRROR))
        if vo is None or vm is None:
            raise KeyError(f"Missing embedding for post_id={pid}")
        X_orig[i] = np.asarray(vo, dtype=np.float64)
        X_mir[i] = np.asarray(vm, dtype=np.float64)
        post_ids.append(pid)
        y_label.append(int(row.label))

    meta = pd.DataFrame({"post_id": post_ids, "label": y_label})
    table_meta = {
        "n_rows": int(len(meta)),
        "embedding_dim": EMBEDDING_DIM,
        "label_counts": {
            "0": int((meta["label"] == 0).sum()),
            "1": int((meta["label"] == 1).sum()),
        },
        "cache_dir": str(cache_dir),
        "cache_stats": cache_stats,
        "model_id": BEDROCK_MODEL_ID,
        "normalize": True,
        "aws_called": False,
        "loader": "local_npy_cache_original_and_mirror",
        "fit_regime": "full_data_exploratory",
        "labels_csv": str(LABELS_CSV_PATH),
        "X_original_shape": list(X_orig.shape),
        "X_mirrored_shape": list(X_mir.shape),
    }
    return X_orig, X_mir, meta, table_meta


def write_artifacts(
    X_orig: np.ndarray,
    X_mir: np.ndarray,
    meta: pd.DataFrame,
    table_meta: dict,
) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    np.save(X_ORIGINAL_PATH, X_orig.astype(np.float64, copy=False))
    np.save(X_MIRRORED_PATH, X_mir.astype(np.float64, copy=False))
    meta.to_csv(ANALYSIS_META_PATH, index=False)
    ANALYSIS_TABLE_META_PATH.write_text(json.dumps(table_meta, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    print(f"Loading labels from {LABELS_CSV_PATH} ...")
    labels = load_labels()
    print(
        f"  rows={len(labels)} keep={int((labels['label'] == 0).sum())} "
        f"remove={int((labels['label'] == 1).sum())}"
    )

    cache_dir = resolve_embedding_cache_dir()
    print(f"Using embedding cache: {cache_dir}")

    X_orig, X_mir, meta, table_meta = build_matrices(labels, cache_dir=cache_dir)
    write_artifacts(X_orig, X_mir, meta, table_meta)

    print(f"Wrote {X_ORIGINAL_PATH} shape={X_orig.shape}")
    print(f"Wrote {X_MIRRORED_PATH} shape={X_mir.shape}")
    print(f"Wrote {ANALYSIS_META_PATH} rows={len(meta)}")
    print(f"Wrote {ANALYSIS_TABLE_META_PATH}")
    print(f"Cache stats: {table_meta['cache_stats']}")
    print(f"aws_called={table_meta['aws_called']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
