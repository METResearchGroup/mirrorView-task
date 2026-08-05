"""Shared embedding utilities."""

from shared.embeddings.bedrock import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    cosine_similarity,
    create_embedding,
    timed_embedding_calls,
)
from shared.embeddings.cache import (
    DEFAULT_DYNAMODB_TABLE_NAME,
    DEFAULT_S3_BUCKET,
    EmbeddingCacheClients,
    load_embedding_by_id,
    load_embedding_by_text,
    make_embedding_cache_clients,
)

__all__ = [
    "AWS_REGION",
    "BEDROCK_MODEL_ID",
    "DEFAULT_DYNAMODB_TABLE_NAME",
    "DEFAULT_S3_BUCKET",
    "EMBEDDING_DIMENSIONS",
    "EmbeddingCacheClients",
    "cosine_similarity",
    "create_embedding",
    "load_embedding_by_id",
    "load_embedding_by_text",
    "make_embedding_cache_clients",
    "timed_embedding_calls",
]
