"""Experiment: two similar texts → Bedrock embeddings → cosine similarity + latency.

Reusable helpers live in ``shared.embeddings.bedrock``. This module re-exports them
and keeps a small smoke-test ``main``.

Run from repository root with AWS credentials configured::

    PYTHONPATH=. uv run --group dev python experiments/simplified_predict_remove_2026_05_13/experiment_bedrock_embeddings.py

Sync dev deps first if needed (``boto3``): ``uv sync --group dev``.
"""

from __future__ import annotations

from shared.embeddings.bedrock import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    bedrock,
    cosine_similarity,
    create_embedding,
    timed_embedding_calls,
)

__all__ = [
    "AWS_REGION",
    "BEDROCK_MODEL_ID",
    "EMBEDDING_DIMENSIONS",
    "bedrock",
    "cosine_similarity",
    "create_embedding",
    "timed_embedding_calls",
]


def main() -> None:
    similar_a = (
        "Amazon Bedrock makes it easier to build generative AI applications on AWS."
    )
    similar_b = (
        "Bedrock on AWS simplifies building applications that use generative AI."
    )

    result_a = create_embedding(similar_a)
    result_b = create_embedding(similar_b)

    times: list[float] = create_embedding.embedding_times  # type: ignore[attr-defined]
    avg_s = sum(times) / len(times)

    sim = cosine_similarity(result_a["embedding"], result_b["embedding"])

    print(f"model_id={result_a['model_id']} dimensions={result_a['dimensions']} normalize={result_a['normalize']}")
    print(f"cosine_similarity(similar pair): {sim:.6f}")
    print(f"inputTextTokenCount: {result_a['input_text_token_count']}, {result_b['input_text_token_count']}")
    print("per-call latency (seconds):")
    for i, dt in enumerate(times):
        print(f"  embedding {i + 1}: {dt:.4f}s")
    print(f"average embedding latency: {avg_s:.4f}s ({avg_s * 1000:.2f} ms)")


if __name__ == "__main__":
    main()
