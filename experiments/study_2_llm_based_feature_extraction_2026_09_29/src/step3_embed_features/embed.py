"""Bedrock Titan embedding with throttling retries and concurrent workers."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from botocore.exceptions import ClientError

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    EMBED_THROTTLE_BACKOFF_SECONDS,
)
from shared.embeddings.bedrock import EMBEDDING_DIMENSIONS


def _is_throttling_error(exc: BaseException) -> bool:
    """Return True when ``exc`` or its cause is a Bedrock throttling ClientError."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code")
        return code == "ThrottlingException"
    cause = exc.__cause__
    if isinstance(cause, ClientError):
        code = cause.response.get("Error", {}).get("Code")
        return code == "ThrottlingException"
    return False


def embed_one_with_retry(
    text: str,
    embed_fn: Callable[[str], dict],
    sleep_fn: Callable[[float], None],
) -> dict:
    """Call ``embed_fn`` and retry throttling failures with fixed backoff.

    Parameters
    ----------
    text
        Input string for the embedding model.
    embed_fn
        Callable that returns a Bedrock-style embedding dict.
    sleep_fn
        Sleep callable used between retries.

    Returns
    -------
    dict
        Embedding response from ``embed_fn``.

    Raises
    ------
    RuntimeError
        When a non-throttling error occurs or retries are exhausted.
    """
    max_attempts = len(EMBED_THROTTLE_BACKOFF_SECONDS) + 1
    for attempt in range(max_attempts):
        try:
            return embed_fn(text)
        except RuntimeError as exc:
            if _is_throttling_error(exc) and attempt < len(EMBED_THROTTLE_BACKOFF_SECONDS):
                sleep_fn(EMBED_THROTTLE_BACKOFF_SECONDS[attempt])
                continue
            raise
    raise RuntimeError("embedding retries exhausted")


def embed_texts(
    texts: list[str],
    embed_fn: Callable[[str], dict],
    sleep_fn: Callable[[float], None],
    max_workers: int,
) -> tuple[np.ndarray, int]:
    """Embed texts concurrently and return a matrix plus total token count.

    Parameters
    ----------
    texts
        Strings to embed, in the desired output row order.
    embed_fn
        Callable passed to :func:`embed_one_with_retry`.
    sleep_fn
        Sleep callable passed to :func:`embed_one_with_retry`.
    max_workers
        Thread pool size.

    Returns
    -------
    tuple[numpy.ndarray, int]
        ``(n, EMBEDDING_DIMENSIONS)`` float64 matrix in input order and the sum
        of ``input_text_token_count`` values.

    Raises
    ------
    ValueError
        When a vector length differs from ``EMBEDDING_DIMENSIONS`` or a token
        count is missing.
    """
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSIONS), dtype=np.float64), 0

    vectors: list[np.ndarray | None] = [None] * len(texts)
    total_tokens = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(embed_one_with_retry, text, embed_fn, sleep_fn): index
            for index, text in enumerate(texts)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            payload = future.result()
            embedding = payload.get("embedding")
            if embedding is None or len(embedding) != EMBEDDING_DIMENSIONS:
                length = len(embedding) if embedding is not None else 0
                raise ValueError(
                    f"embedding at index {index} has length {length}, "
                    f"expected {EMBEDDING_DIMENSIONS}"
                )
            token_count = payload.get("input_text_token_count")
            if token_count is None:
                raise ValueError(f"missing input_text_token_count at index {index}")
            vectors[index] = np.asarray(embedding, dtype=np.float64)
            total_tokens += int(token_count)

    matrix = np.vstack(vectors)
    return matrix, total_tokens
