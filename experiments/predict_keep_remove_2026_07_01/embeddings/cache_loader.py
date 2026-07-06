"""Local-cached embedding loader with progress bars.

We load embeddings for the (original_text, mirror_text) pair by:
  1) computing an embedding identity hash (text + model_id + dims + normalize)
  2) looking up the S3 key via DynamoDB (embedding_id -> s3_key)
  3) downloading the embedding vector from S3 if not present in a local cache

The cache is stored on disk keyed by `embedding_id`, so repeated training runs
avoid re-downloading embeddings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from tqdm import tqdm

from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    AWS_REGION as BEDROCK_AWS_REGION,
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
)
from experiments.simplified_predict_remove_2026_05_13.generate_embeddings import (
    TEXT_ROLE_MIRROR,
    TEXT_ROLE_ORIGINAL,
    validate_post_ids_unique,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3


TextRole = Literal["original_text", "mirror_text"]


@dataclass(frozen=True)
class EmbeddingCacheStats:
    total_embedding_instances: int
    cache_hits: int
    cache_misses: int


def _cache_path(cache_dir: Path, embedding_id: str) -> Path:
    # Store numpy arrays for fast loading.
    return cache_dir / "embeddings" / f"{embedding_id}.npy"


def load_embeddings_via_dynamodb_and_s3_with_cache(
    df,
    *,
    bucket: str | None = None,
    table: str | None = None,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
    cache_dir: str | Path | None = None,
) -> tuple[dict[tuple[str, str], list[float]], EmbeddingCacheStats]:
    """Return mapping (post_id, text_role) -> embedding_vector.

    Also returns cache hit/miss stats for logging.
    """

    bucket_name = (bucket or S3_BUCKET).strip()
    table_name = (table or DYNAMODB_TABLE_NAME).strip()
    if not bucket_name or not table_name:
        raise ValueError("S3 bucket and DynamoDB table must be non-empty.")

    # Validate required columns (mirrors simplified loader).
    validate_post_ids_unique(df)
    for c in ("original_text", "mirror_text"):
        if c not in df.columns:
            raise KeyError(c)

    cache_root = Path(cache_dir) if cache_dir is not None else None
    if cache_root is None:
        raise ValueError("cache_dir is required so embeddings can be cached locally.")
    cache_root.mkdir(parents=True, exist_ok=True)

    # Clients (kept outside the inner loop).
    s3 = S3(bucket_name, region_name=BEDROCK_AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(table_name, region_name=BEDROCK_AWS_REGION)

    # Pre-materialize tasks so tqdm knows the total.
    tasks: list[tuple[str, TextRole, str, str]] = []
    for _, r in df.iterrows():
        pid = str(r["post_id"])
        ot = str(r["original_text"])
        mt = str(r["mirror_text"])

        eid_o = embedding_identity_sha256(
            ot, model_id=model_id, dimensions=dimensions, normalize=normalize
        )
        eid_m = embedding_identity_sha256(
            mt, model_id=model_id, dimensions=dimensions, normalize=normalize
        )

        tasks.append((pid, TEXT_ROLE_ORIGINAL, ot, eid_o))
        tasks.append((pid, TEXT_ROLE_MIRROR, mt, eid_m))

    lookup: dict[tuple[str, str], list[float]] = {}
    cache_hits = 0
    cache_misses = 0

    # In-memory dedupe to avoid repeated disk reads/downloads for repeated text.
    embedding_id_to_vec: dict[str, np.ndarray] = {}

    for pid, role, _text, embedding_id in tqdm(
        tasks,
        desc="Loading embeddings (cached)",
        unit="embedding_instance",
    ):
        key = (pid, str(role))
        if key in lookup:
            continue

        cached = _cache_path(cache_root, embedding_id)
        if embedding_id in embedding_id_to_vec:
            vec = embedding_id_to_vec[embedding_id]
            cache_hits += 1
        elif cached.exists():
            vec = np.load(cached)
            embedding_id_to_vec[embedding_id] = vec
            cache_hits += 1
        else:
            # Pointer row: embedding_id -> s3_key
            d_row = ddb.get_item(embedding_id)
            if d_row is None:
                raise KeyError(f"No DynamoDB embedding row for embedding_id={embedding_id!r}")
            s3_key = str(d_row.get("s3_key", ""))
            if not s3_key.strip():
                raise KeyError(f"s3_key missing from DynamoDB row {embedding_id!r}")

            raw = s3.get_bytes(s3_key)
            parsed = json.loads(raw.decode("utf-8"))
            emb = parsed.get("embedding")
            if emb is None or not isinstance(emb, list):
                raise RuntimeError(f"S3 embedding invalid for embedding_id={embedding_id!r}")

            vec = np.asarray([float(x) for x in emb], dtype=np.float64)
            cached.parent.mkdir(parents=True, exist_ok=True)
            np.save(cached, vec)
            embedding_id_to_vec[embedding_id] = vec
            cache_misses += 1

        lookup[key] = [float(x) for x in vec.ravel().tolist()]

    stats = EmbeddingCacheStats(
        total_embedding_instances=len(tasks),
        cache_hits=cache_hits,
        cache_misses=cache_misses,
    )
    return lookup, stats
