"""Bedrock embedding → S3 JSON + DynamoDB pointer → reload → vector equality check.

Invokes Titan once, stores the embedding JSON on S3,
records bucket/key/metadata in DynamoDB, then reloads strictly through the DynamoDB row.

Run from repository root:

    PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/experiment_create_embedding_and_upload.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    AWS_REGION as BEDROCK_AWS_REGION,
    BEDROCK_MODEL_ID,
    create_embedding,
    EMBEDDING_DIMENSIONS,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3

AWS_REGION = BEDROCK_AWS_REGION
S3_BUCKET = "jspsych-mirror-view-3"
DYNAMODB_TABLE_NAME = "jspsych-mirror-view-embedding-cache"
S3_PREFIX = "embeddings/"


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vectors_equivalent(a: list[float], b: list[float]) -> tuple[bool, str]:
    """Prefer strict equality; fall back to tiny float tolerance after JSON round-trip."""
    if a == b:
        return True, "strict_list_equality"
    if len(a) != len(b):
        return False, f"length_mismatch:{len(a)}_vs_{len(b)}"
    abs_tol = 1e-12
    rel_tol = 1e-15
    for i, (x, y) in enumerate(zip(a, b, strict=True)):
        if not math.isclose(x, y, rel_tol=rel_tol, abs_tol=abs_tol):
            return False, f"first_mismatch_index={i} {x!r} vs {y!r}"
    return True, f"math.isclose_all(abs_tol={abs_tol}, rel_tol={rel_tol})"


def main() -> None:
    if not S3_BUCKET.strip() or not DYNAMODB_TABLE_NAME.strip():
        raise SystemExit(
            "Set S3_BUCKET and DYNAMODB_TABLE_NAME at the top of this file."
        )

    bucket_name = S3_BUCKET.strip()
    table_name = DYNAMODB_TABLE_NAME.strip()

    sample_text = "MirrorView embedding cache round-trip smoke test string."
    normalize = True

    embedding_id = embedding_identity_sha256(
        sample_text,
        model_id=BEDROCK_MODEL_ID,
        dimensions=EMBEDDING_DIMENSIONS,
        normalize=normalize,
    )
    s3_key = f"{S3_PREFIX}{embedding_id}.json"

    s3 = S3(bucket_name, region_name=AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(table_name, region_name=AWS_REGION)
    ddb.ensure_table_exists()

    fresh: dict[str, Any] = create_embedding(
        sample_text,
        model_id=BEDROCK_MODEL_ID,
        dimensions=EMBEDDING_DIMENSIONS,
        normalize=normalize,
    )

    body = json.dumps(fresh, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    s3.upload_bytes(s3_key, body, content_type="application/json")

    item = {
        "embedding_id": embedding_id,
        "s3_bucket": bucket_name,
        "s3_key": s3_key,
        "text_sha256": embedding_id,
        "created_at": _utc_iso_z(),
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": normalize,
    }
    ddb.put_item(item)

    row = ddb.get_item(embedding_id)
    if row is None:
        raise RuntimeError("DynamoDB row missing immediately after put_item")
    loaded_bucket = row["s3_bucket"]
    loaded_key = row["s3_key"]
    if loaded_bucket != bucket_name:
        raise RuntimeError(
            f"DynamoDB s3_bucket mismatch: {loaded_bucket!r} != {bucket_name!r}"
        )

    raw_json = s3.get_bytes(loaded_key)
    parsed = json.loads(raw_json.decode("utf-8"))
    loaded_embedding = parsed["embedding"]
    fresh_embedding = fresh["embedding"]

    ok, how = _vectors_equivalent(fresh_embedding, loaded_embedding)
    if not ok:
        raise AssertionError(f"Embedding mismatch ({how})")

    print(
        f"ok embedding_id={embedding_id} s3_key={loaded_key} "
        f"dims={len(fresh_embedding)} compare={how}"
    )


if __name__ == "__main__":
    main()
