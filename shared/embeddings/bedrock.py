"""Amazon Bedrock Titan Text Embeddings helpers.

Provides ``create_embedding`` for live Bedrock calls and ``cosine_similarity``
for comparing vectors. Default model, region, and dimensions are module
constants. Requires AWS credentials with Bedrock invoke access.
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
    """Append each call's wall-clock seconds to ``fn.embedding_times``.

    Latencies are recorded even when the wrapped function raises.
    """

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
    """Invoke Titan Text Embeddings and return the vector plus request metadata.

    Defaults match the shared embedding-cache identity (256-d, L2-normalized).
    Decorated by :func:`timed_embedding_calls`, so latencies accumulate on
    ``create_embedding.embedding_times``.

    Parameters
    ----------
    text : str
        Non-empty input; whitespace-only strings are rejected.
    normalize : bool
        When True, Bedrock returns an L2-normalized vector.

    Returns
    -------
    dict
        Keys include ``text``, ``model_id``, ``dimensions``, ``normalize``,
        ``embedding``, and ``input_text_token_count`` (may be ``None``).

    Raises
    ------
    ValueError
        If ``text`` is empty or whitespace-only.
    RuntimeError
        If the Bedrock call fails or the response has no ``embedding`` field.
    """
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
    """Return the cosine similarity of two equal-length vectors.

    Zero-norm vectors yield ``0.0``. For already L2-normalized inputs this
    equals the dot product.

    Raises
    ------
    ValueError
        If ``a`` and ``b`` have different lengths.
    """
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
