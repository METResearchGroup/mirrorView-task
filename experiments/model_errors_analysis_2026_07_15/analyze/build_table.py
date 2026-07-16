"""Build analysis table: Qwen labels + only_original Titan embeddings.

Loads original-post embeddings from the local embedding cache (prefer cache hits;
does not call Bedrock embed / Converse / api_baselines train). Falls back to
DynamoDB→S3 via cache_loader only if a local miss is unavoidable.

Run from repo root::

    PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/build_table.py
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
    ANALYSIS_META_PATH,
    ANALYSIS_TABLE_PATH,
    EMBEDDING_DIM,
    EMBEDDING_MATRIX_PATH,
    FEATURE_SET,
    LABELS_CSV_PATH,
    MAIN_REPO_EMBEDDING_CACHE,
    PRIMARY_CLASSIFIER_ID,
    PROGRESS_UPDATES_PATH,
    ANALYSIS_DIR,
    WORKTREE_EMBEDDING_CACHE,
)
from experiments.predict_keep_remove_2026_07_01.embeddings.features.only_original import (  # noqa: E402
    OnlyOriginalEmbeddingFeatureBuilder,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (  # noqa: E402
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from experiments.simplified_predict_remove_2026_05_13.features import (  # noqa: E402
    JOIN_COL_ORIGINAL,
)
from experiments.simplified_predict_remove_2026_05_13.generate_embeddings import (  # noqa: E402
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


def load_only_original_from_local_cache(
    df: pd.DataFrame,
    *,
    cache_dir: Path,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
) -> tuple[dict[tuple[str, str], list[float]], dict[str, int]]:
    """Load original-post vectors from local ``embeddings/*.npy`` only (no AWS).

    Returns lookup keyed by ``(post_id, text_role)`` and hit/miss stats.
    Raises ``FileNotFoundError`` if any original embedding is missing locally.
    """
    if "post_id" not in df.columns or "original_text" not in df.columns:
        raise KeyError("df must include post_id and original_text")

    lookup: dict[tuple[str, str], list[float]] = {}
    hits = 0
    misses: list[str] = []
    id_to_vec: dict[str, np.ndarray] = {}

    for _, row in df.iterrows():
        pid = str(row["post_id"])
        text = str(row["original_text"])
        eid = embedding_identity_sha256(
            text, model_id=model_id, dimensions=dimensions, normalize=normalize
        )
        key = (pid, TEXT_ROLE_ORIGINAL)
        if key in lookup:
            continue

        if eid in id_to_vec:
            vec = id_to_vec[eid]
            hits += 1
        else:
            path = _cache_npy_path(cache_dir, eid)
            if not path.exists():
                misses.append(pid)
                continue
            vec = np.load(path)
            id_to_vec[eid] = vec
            hits += 1

        arr = np.asarray(vec, dtype=np.float64).ravel()
        if arr.shape[0] != dimensions:
            raise ValueError(
                f"Unexpected embedding dim for post_id={pid}: {arr.shape[0]} != {dimensions}"
            )
        lookup[key] = [float(x) for x in arr.tolist()]

    stats = {
        "total_posts": int(df["post_id"].nunique()),
        "cache_hits": hits,
        "cache_misses": len(misses),
        "miss_post_ids_sample": misses[:10],
    }
    if misses:
        raise FileNotFoundError(
            f"Local embedding cache missing {len(misses)} original vectors. "
            f"sample_post_ids={misses[:5]} cache_dir={cache_dir}"
        )
    return lookup, stats


def join_only_original(
    df: pd.DataFrame,
    lookup: dict[tuple[str, str], list[float]],
) -> pd.DataFrame:
    """Attach ``JOIN_COL_ORIGINAL`` from an original-only lookup (no mirror required)."""
    out = df.copy()
    oid: list[np.ndarray] = []
    missing: list[str] = []
    for _, row in out.iterrows():
        pid = str(row["post_id"])
        vo = lookup.get((pid, TEXT_ROLE_ORIGINAL))
        if vo is None:
            missing.append(pid)
            continue
        oid.append(np.asarray(vo, dtype=np.float64))
    if missing:
        raise KeyError(
            f"Missing original embeddings for {len(missing)} posts; sample={missing[:5]}"
        )
    out[JOIN_COL_ORIGINAL] = oid
    return out


def load_labels() -> pd.DataFrame:
    if not LABELS_CSV_PATH.is_file():
        raise FileNotFoundError(f"Missing labels CSV: {LABELS_CSV_PATH}")
    df = pd.read_csv(LABELS_CSV_PATH)
    required = {"post_id", "original_text", "label", "classifier_id", "is_correct"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise KeyError(f"labels CSV missing columns: {sorted(missing_cols)}")

    df = df.copy()
    df["post_id"] = df["post_id"].astype(str)
    bad_clf = df["classifier_id"] != PRIMARY_CLASSIFIER_ID
    if bad_clf.any():
        raise ValueError(
            f"Expected only {PRIMARY_CLASSIFIER_ID!r}; "
            f"found extras={df.loc[bad_clf, 'classifier_id'].unique().tolist()}"
        )
    if df["post_id"].duplicated().any():
        n = int(df["post_id"].duplicated().sum())
        raise ValueError(f"Duplicate post_id rows in labels CSV: {n}")

    df["label"] = df["label"].astype(int)
    df["is_correct"] = df["is_correct"].astype(int)
    df["is_error"] = (1 - df["is_correct"]).astype(int)
    return df


def build_analysis_table(
    labels: pd.DataFrame,
    *,
    cache_dir: Path,
) -> tuple[pd.DataFrame, np.ndarray, dict]:
    lookup, cache_stats = load_only_original_from_local_cache(labels, cache_dir=cache_dir)
    joined = join_only_original(labels, lookup)

    builder = OnlyOriginalEmbeddingFeatureBuilder().fit(joined)
    X, feature_names = builder.transform(joined)
    if X.shape != (len(joined), EMBEDDING_DIM):
        raise ValueError(f"Unexpected X shape {X.shape}; expected ({len(joined)}, {EMBEDDING_DIM})")
    if builder.embedding_dim != EMBEDDING_DIM:
        raise ValueError(f"embedding_dim={builder.embedding_dim} != {EMBEDDING_DIM}")

    table = pd.DataFrame(
        {
            "post_id": joined["post_id"].astype(str).values,
            "label": joined["label"].astype(int).values,
            "is_correct": joined["is_correct"].astype(int).values,
            "is_error": joined["is_error"].astype(int).values,
            "embedding": [row.astype(np.float64) for row in X],
        }
    )
    meta = {
        "n_rows": int(len(table)),
        "embedding_dim": EMBEDDING_DIM,
        "feature_set": FEATURE_SET,
        "classifier_id": PRIMARY_CLASSIFIER_ID,
        "feature_names": feature_names,
        "cache_dir": str(cache_dir),
        "cache_stats": cache_stats,
        "model_id": BEDROCK_MODEL_ID,
        "normalize": True,
        "is_error_rate": float(table["is_error"].mean()),
        "is_error_counts": {
            "0": int((table["is_error"] == 0).sum()),
            "1": int((table["is_error"] == 1).sum()),
        },
        "aws_called": False,
        "loader": "local_npy_cache_only_original",
    }
    return table, X, meta


def write_artifacts(table: pd.DataFrame, X: np.ndarray, meta: dict) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    table.to_parquet(ANALYSIS_TABLE_PATH, index=False)
    np.save(EMBEDDING_MATRIX_PATH, X.astype(np.float64, copy=False))
    table[["post_id", "label", "is_correct", "is_error"]].to_csv(ANALYSIS_META_PATH, index=False)
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
    print(f"Loading labels from {LABELS_CSV_PATH} ...")
    labels = load_labels()
    print(f"  rows={len(labels)} is_error={int(labels['is_error'].sum())}")

    cache_dir = resolve_embedding_cache_dir()
    print(f"Using embedding cache: {cache_dir}")

    table, X, meta = build_analysis_table(labels, cache_dir=cache_dir)
    write_artifacts(table, X, meta)

    print(f"Wrote {ANALYSIS_TABLE_PATH} rows={len(table)} embedding_list_len={EMBEDDING_DIM}")
    print(f"Wrote {EMBEDDING_MATRIX_PATH} shape={X.shape}")
    print(f"Wrote {ANALYSIS_META_PATH}")
    print(f"Cache stats: {meta['cache_stats']}")

    append_progress(
        [
            "## Build analysis table",
            "",
            f"- Labels: `{LABELS_CSV_PATH}` ({len(labels)} rows, `{PRIMARY_CLASSIFIER_ID}` only)",
            f"- Feature set: `{FEATURE_SET}` / Titan `{BEDROCK_MODEL_ID}` dims={EMBEDDING_DIM}",
            f"- Embedding cache: `{cache_dir}` (local `.npy` only; AWS not called)",
            f"- Cache hits={meta['cache_stats']['cache_hits']} misses={meta['cache_stats']['cache_misses']}",
            f"- Artifacts:",
            f"  - `{ANALYSIS_TABLE_PATH}` — columns `post_id,label,is_correct,is_error,embedding`; "
            f"`embedding` is length-{EMBEDDING_DIM} float64; rows={len(table)}",
            f"  - `{EMBEDDING_MATRIX_PATH}` — shape `{tuple(X.shape)}`",
            f"  - `{ANALYSIS_META_PATH}` — scalar columns only",
            f"  - `{ANALYSIS_DIR / 'analysis_table_meta.json'}` — loader / cache metadata",
            f"- is_error rate: {meta['is_error_rate']:.4f} "
            f"(correct={meta['is_error_counts']['0']}, error={meta['is_error_counts']['1']})",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
