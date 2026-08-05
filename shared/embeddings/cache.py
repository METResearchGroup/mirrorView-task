"""Read Titan text embeddings from the shared DynamoDB → S3 identity cache.

Looks up vectors by embedding identity (or by text hashed to that identity).
Does not call Bedrock; cache misses return ``None``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3
from shared.embeddings.bedrock import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)

# Same defaults as experiments/simplified_predict_remove_2026_05_13/
# experiment_create_embedding_and_upload.py
DEFAULT_S3_BUCKET = "jspsych-mirror-view-3"
DEFAULT_DYNAMODB_TABLE_NAME = "jspsych-mirror-view-embedding-cache"


@dataclass(frozen=True)
class EmbeddingCacheClients:
    """Bundled S3 and DynamoDB clients for the embedding identity cache.

    Reuse one instance across many lookups to avoid reconnecting per call.
    """

    s3: S3
    ddb: DynamoDBEmbeddingIndex


def make_embedding_cache_clients(
    *,
    bucket: str | None = None,
    table: str | None = None,
    region_name: str | None = None,
) -> EmbeddingCacheClients:
    """Construct clients wired to the embedding identity cache bucket and table.

    Uses the shared default bucket and table when omitted. Region defaults to
    the Bedrock helper's AWS region.

    Raises
    ------
    ValueError
        If the resolved bucket or table name is empty.
    """
    bucket_name = (bucket or DEFAULT_S3_BUCKET).strip()
    table_name = (table or DEFAULT_DYNAMODB_TABLE_NAME).strip()
    if not bucket_name or not table_name:
        raise ValueError("S3 bucket and DynamoDB table must be non-empty.")
    region = region_name if region_name is not None else AWS_REGION
    return EmbeddingCacheClients(
        s3=S3(bucket_name, region_name=region),
        ddb=DynamoDBEmbeddingIndex(table_name, region_name=region),
    )


def _local_cache_path(cache_dir: Path, embedding_id: str) -> Path:
    return cache_dir / "embeddings" / f"{embedding_id}.npy"


def _load_local_npy(path: Path) -> list[float] | None:
    if not path.exists():
        return None
    import numpy as np

    vec = np.load(path)
    return [float(x) for x in vec.ravel().tolist()]


def _save_local_npy(path: Path, embedding: list[float]) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, np.asarray(embedding, dtype=np.float64))


def _parse_s3_embedding_payload(raw: bytes, *, embedding_id: str) -> list[float]:
    parsed: dict[str, Any] = json.loads(raw.decode("utf-8"))
    emb = parsed.get("embedding")
    if emb is None or not isinstance(emb, list):
        raise RuntimeError(f"S3 embedding invalid for embedding_id={embedding_id!r}")
    return [float(x) for x in emb]


def load_embedding_by_id(
    embedding_id: str,
    *,
    clients: EmbeddingCacheClients | None = None,
    bucket: str | None = None,
    table: str | None = None,
    region_name: str | None = None,
    cache_dir: str | Path | None = None,
) -> list[float] | None:
    """Fetch an embedding vector by its identity hash.

    Resolution order: optional local ``.npy`` under ``cache_dir``, then
    DynamoDB pointer → S3 JSON payload. On a successful remote fetch with
    ``cache_dir`` set, writes a local copy for subsequent calls.

    Returns
    -------
    list[float] or None
        The embedding vector, or ``None`` when no DynamoDB pointer or
        ``s3_key`` exists (a true cache miss).

    Raises
    ------
    ValueError
        If ``embedding_id`` is empty.
    RuntimeError
        If the S3 object exists but lacks a valid ``embedding`` list.
    """
    if not embedding_id or not str(embedding_id).strip():
        raise ValueError("embedding_id must be a non-empty string")

    eid = str(embedding_id).strip()
    cache_root = Path(cache_dir) if cache_dir is not None else None
    if cache_root is not None:
        local = _load_local_npy(_local_cache_path(cache_root, eid))
        if local is not None:
            return local

    handle = clients or make_embedding_cache_clients(
        bucket=bucket, table=table, region_name=region_name
    )
    d_row = handle.ddb.get_item(eid)
    if d_row is None:
        return None

    s3_key = str(d_row.get("s3_key", "")).strip()
    if not s3_key:
        return None

    vec = _parse_s3_embedding_payload(handle.s3.get_bytes(s3_key), embedding_id=eid)

    if cache_root is not None:
        _save_local_npy(_local_cache_path(cache_root, eid), vec)

    return vec


def load_embedding_by_text(
    text: str,
    *,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
    clients: EmbeddingCacheClients | None = None,
    bucket: str | None = None,
    table: str | None = None,
    region_name: str | None = None,
    cache_dir: str | Path | None = None,
) -> list[float] | None:
    """Look up a cached embedding for ``text`` without calling Bedrock.

    Hashes ``text`` with the same identity scheme used when writing the cache
    (defaults match :func:`shared.embeddings.bedrock.create_embedding`), then
    delegates to :func:`load_embedding_by_id`. Returns ``None`` on cache miss.

    Raises
    ------
    ValueError
        If ``text`` is empty or whitespace-only.
    """
    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")

    embedding_id = embedding_identity_sha256(
        text,
        model_id=model_id,
        dimensions=dimensions,
        normalize=normalize,
    )
    return load_embedding_by_id(
        embedding_id,
        clients=clients,
        bucket=bucket,
        table=table,
        region_name=region_name,
        cache_dir=cache_dir,
    )
