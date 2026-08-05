"""Amazon Bedrock Titan Text Embeddings V2 helpers.

Region, model id, and embedding size are fixed constants below (256-d Titan v2).

Requires AWS credentials and the ``dev`` dependency group (``boto3``)::

    uv sync --group dev
"""

from __future__ import annotations

import json
import math
import time
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 256

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

P = ParamSpec("P")
R = TypeVar("R")


def timed_embedding_calls(fn: Callable[P, R]) -> Callable[P, R]:
    """Record wall-clock seconds per call on ``fn.embedding_times``."""

    times: list[float] = []

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            times.append(time.perf_counter() - start)

    wrapper.embedding_times = times  # type: ignore[attr-defined]
    return wrapper


@timed_embedding_calls
def create_embedding(
    text: str,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
) -> dict[str, Any]:
    """Generate an embedding via Amazon Bedrock Titan Text Embeddings V2."""
    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")

    body = {
        "inputText": text,
        "dimensions": dimensions,
        "normalize": normalize,
    }

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
    except ClientError as e:
        raise RuntimeError(f"Bedrock invoke_model failed: {e}") from e

    vec = payload.get("embedding")
    if vec is None:
        raise RuntimeError(
            "Response missing top-level 'embedding'; "
            "if using binary-only embeddingTypes, read embeddingsByType instead."
        )

    return {
        "text": text,
        "model_id": model_id,
        "dimensions": dimensions,
        "normalize": normalize,
        "embedding": vec,
        "input_text_token_count": payload.get("inputTextTokenCount"),
    }


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity; if vectors are already L2-normalized, equals the dot product."""
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
