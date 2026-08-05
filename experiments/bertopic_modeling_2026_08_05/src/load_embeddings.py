"""Stage 1: resolve Titan original-text embeddings into the local cache.

Default path loads a complete ``outputs/embeddings/original/`` cache with no AWS
calls. Refresh pulls from the keep/remove DynamoDB+S3 identity cache. Optional
``--backfill`` fills residuals via ``shared.embeddings.bedrock.create_embedding``.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py \\
      --refresh-from-identity-cache
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from experiments.bertopic_modeling_2026_08_05.src import data as data_mod
from experiments.bertopic_modeling_2026_08_05.src import paths
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    AWS_REGION as BEDROCK_AWS_REGION,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3
from shared.embeddings.bedrock import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    create_embedding,
)

TEXT_ROLE = paths.TEXT_ROLE_V1
DISK_CACHE_DIRNAME = ".identity_disk_cache"
METADATA_FILENAME = "metadata.json"
EMBEDDINGS_FILENAME = "embeddings.npy"
INDEX_FILENAME = "index.parquet"
SOURCE_LOCAL = "local_cache"
SOURCE_IDENTITY = "identity_cache"
SOURCE_MIXED = "mixed_identity_and_bedrock"


@dataclass(frozen=True)
class EmbeddingCacheResult:
    """Summary of a Stage-1 cache load/write."""

    cache_dir: Path
    n_rows: int
    n_dropped: int
    n_backfilled: int
    source: str


def _cache_paths(cache_dir: Path) -> tuple[Path, Path, Path]:
    return (
        cache_dir / EMBEDDINGS_FILENAME,
        cache_dir / INDEX_FILENAME,
        cache_dir / METADATA_FILENAME,
    )


def _disk_cache_path(disk_cache_root: Path, embedding_id: str) -> Path:
    return disk_cache_root / "embeddings" / f"{embedding_id}.npy"


def _local_cache_is_complete(
    cache_dir: Path,
    message_ids: set[str],
) -> bool:
    """Return True when local cache accounts for all modal message_ids."""
    emb_path, index_path, meta_path = _cache_paths(cache_dir)
    if not (emb_path.is_file() and index_path.is_file() and meta_path.is_file()):
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("model_id") != BEDROCK_MODEL_ID:
        return False
    if int(meta.get("dimensions", -1)) != EMBEDDING_DIMENSIONS:
        return False
    if meta.get("normalize") is not True:
        return False
    if meta.get("text_role") != TEXT_ROLE:
        return False
    index = pd.read_parquet(index_path)
    embeddings = np.load(emb_path)
    if embeddings.shape != (len(index), EMBEDDING_DIMENSIONS):
        return False
    cached_ids = set(index["message_id"].astype(str))
    dropped_ids = {str(x) for x in meta.get("dropped_message_ids", [])}
    return message_ids.issubset(cached_ids | dropped_ids)


def _write_cache_atomic(
    cache_dir: Path,
    embeddings: np.ndarray,
    index: pd.DataFrame,
    metadata: dict,
) -> None:
    """Write embeddings, index, and metadata via a temp directory replace."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(cache_dir)) as tmp:
        tmp_dir = Path(tmp)
        emb_tmp = tmp_dir / EMBEDDINGS_FILENAME
        index_tmp = tmp_dir / INDEX_FILENAME
        meta_tmp = tmp_dir / METADATA_FILENAME
        with emb_tmp.open("wb") as handle:
            np.save(handle, embeddings)
        index.to_parquet(index_tmp, index=False)
        meta_tmp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

        emb_path, index_path, meta_path = _cache_paths(cache_dir)
        emb_tmp.replace(emb_path)
        index_tmp.replace(index_path)
        meta_tmp.replace(meta_path)


def _load_local_cache(cache_dir: Path) -> EmbeddingCacheResult:
    """Load an existing complete local cache (no AWS)."""
    emb_path, index_path, meta_path = _cache_paths(cache_dir)
    embeddings = np.load(emb_path)
    index = pd.read_parquet(index_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if embeddings.shape != (len(index), EMBEDDING_DIMENSIONS):
        raise ValueError(
            f"Cache shape mismatch: embeddings={embeddings.shape} index_rows={len(index)}"
        )
    return EmbeddingCacheResult(
        cache_dir=cache_dir,
        n_rows=len(index),
        n_dropped=len(meta.get("dropped_message_ids", [])),
        n_backfilled=len(meta.get("backfill_message_ids", [])),
        source=SOURCE_LOCAL,
    )


def _fetch_identity_vector(
    text: str,
    ddb: DynamoDBEmbeddingIndex,
    s3: S3,
    disk_cache_root: Path,
    embedding_id_to_vec: dict[str, np.ndarray],
) -> np.ndarray | None:
    """Fetch one Titan vector from disk / DynamoDB+S3. Return None if missing."""
    embedding_id = embedding_identity_sha256(
        text,
        model_id=BEDROCK_MODEL_ID,
        dimensions=EMBEDDING_DIMENSIONS,
        normalize=True,
    )
    if embedding_id in embedding_id_to_vec:
        return embedding_id_to_vec[embedding_id]

    cached = _disk_cache_path(disk_cache_root, embedding_id)
    if cached.exists():
        vec = np.load(cached)
        embedding_id_to_vec[embedding_id] = vec
        return vec

    d_row = ddb.get_item(embedding_id)
    if d_row is None:
        return None
    s3_key = str(d_row.get("s3_key", "")).strip()
    if not s3_key:
        return None

    raw = s3.get_bytes(s3_key)
    parsed = json.loads(raw.decode("utf-8"))
    emb = parsed.get("embedding")
    if emb is None or not isinstance(emb, list):
        return None
    if len(emb) != EMBEDDING_DIMENSIONS:
        return None

    vec = np.asarray([float(x) for x in emb], dtype=np.float64)
    cached.parent.mkdir(parents=True, exist_ok=True)
    np.save(cached, vec)
    embedding_id_to_vec[embedding_id] = vec
    return vec


def _resolve_from_identity_and_optional_backfill(
    posts: pd.DataFrame,
    cache_dir: Path,
    backfill: bool,
) -> EmbeddingCacheResult:
    """Resolve original-text vectors via DynamoDB+S3, optionally Bedrock.

    Missing identity-cache rows are dropped unless ``backfill`` is True.
    Only the original text role is resolved (v1).
    """
    disk_cache = paths.EXPERIMENT_ROOT / "outputs" / "embeddings" / DISK_CACHE_DIRNAME
    disk_cache.mkdir(parents=True, exist_ok=True)

    s3 = S3(S3_BUCKET, region_name=BEDROCK_AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(DYNAMODB_TABLE_NAME, region_name=BEDROCK_AWS_REGION)
    embedding_id_to_vec: dict[str, np.ndarray] = {}

    vectors: list[np.ndarray] = []
    kept_ids: list[str] = []
    dropped_message_ids: list[str] = []
    backfill_message_ids: list[str] = []

    rows = list(posts.itertuples(index=False))
    for row in tqdm(rows, desc="Resolving original Titan vectors", unit="post"):
        message_id = str(row.message_id)
        original_text = str(row.original_text)
        vec = _fetch_identity_vector(
            text=original_text,
            ddb=ddb,
            s3=s3,
            disk_cache_root=disk_cache,
            embedding_id_to_vec=embedding_id_to_vec,
        )
        if vec is not None:
            vectors.append(np.asarray(vec, dtype=np.float64).ravel())
            kept_ids.append(message_id)
            continue

        if not backfill:
            dropped_message_ids.append(message_id)
            continue

        try:
            out = create_embedding(original_text)
            emb = out["embedding"]
            if len(emb) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(f"Unexpected embedding length {len(emb)}")
            vectors.append(np.asarray(emb, dtype=np.float64))
            kept_ids.append(message_id)
            backfill_message_ids.append(message_id)
        except Exception:
            dropped_message_ids.append(message_id)

    if not kept_ids:
        raise RuntimeError("No embeddings resolved for any message_id")

    embeddings = np.vstack(vectors)
    index = pd.DataFrame(
        {
            "row_id": np.arange(len(kept_ids), dtype=np.int64),
            "message_id": kept_ids,
        }
    )
    source = SOURCE_MIXED if backfill_message_ids else SOURCE_IDENTITY
    metadata = {
        "text_role": TEXT_ROLE,
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
        "n_rows": len(kept_ids),
        "source": source,
        "ddb_table": DYNAMODB_TABLE_NAME,
        "dropped_message_ids": dropped_message_ids,
        "backfill_message_ids": backfill_message_ids,
        "unanimous_rule_id": None,
    }
    _write_cache_atomic(cache_dir, embeddings, index, metadata)
    return EmbeddingCacheResult(
        cache_dir=cache_dir,
        n_rows=len(kept_ids),
        n_dropped=len(dropped_message_ids),
        n_backfilled=len(backfill_message_ids),
        source=source,
    )


def run_load_embeddings(
    refresh_from_identity_cache: bool,
    backfill: bool,
) -> EmbeddingCacheResult:
    """Build or load the committed Titan cache for original posts.

    Parameters
    ----------
    refresh_from_identity_cache
        When True, rebuild from DynamoDB+S3 even if a local cache exists.
    backfill
        When True, call Bedrock for ids still missing after identity-cache lookup.

    Returns
    -------
    EmbeddingCacheResult
        Summary of the written/loaded cache.
    """
    posts = data_mod.load_keep_remove_posts()
    message_ids = set(posts["message_id"].astype(str))
    cache_dir = paths.embeddings_dir(TEXT_ROLE)

    if (
        not refresh_from_identity_cache
        and _local_cache_is_complete(cache_dir, message_ids)
    ):
        result = _load_local_cache(cache_dir)
    else:
        result = _resolve_from_identity_and_optional_backfill(
            posts=posts,
            cache_dir=cache_dir,
            backfill=backfill,
        )

    print(
        f"n_rows={result.n_rows} n_dropped={result.n_dropped} "
        f"n_backfilled={result.n_backfilled} source={result.source} "
        f"cache_path={result.cache_dir}"
    )
    return result


def main() -> None:
    """CLI entrypoint for Stage 1."""
    parser = argparse.ArgumentParser(
        description="Resolve Titan original-text embeddings into the local cache."
    )
    parser.add_argument(
        "--refresh-from-identity-cache",
        action="store_true",
        help="Rebuild from DynamoDB+S3 even when a complete local cache exists.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Call Bedrock for message_ids still missing after identity-cache lookup.",
    )
    args = parser.parse_args()
    run_load_embeddings(
        refresh_from_identity_cache=args.refresh_from_identity_cache,
        backfill=args.backfill,
    )


if __name__ == "__main__":
    main()
