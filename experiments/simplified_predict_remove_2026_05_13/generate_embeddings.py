"""Generate Bedrock embeddings for simplified keep/remove rows, upload to S3 + DynamoDB, verify.

Run from repo root::

    PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/generate_embeddings.py --limit 2
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, NamedTuple

import pandas as pd
from rich.console import Console
from tqdm import tqdm

from experiments.simplified_predict_remove_2026_05_13.dataloader import Dataloader
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    create_embedding,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    AWS_REGION,
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
    S3_PREFIX,
)
from lib.aws.dynamodb import DynamoDBEmbeddingIndex
from lib.aws.embedding_identity import embedding_identity_sha256
from lib.aws.s3 import S3

TEXT_ROLE_ORIGINAL: Literal["original_text"] = "original_text"
TEXT_ROLE_MIRROR: Literal["mirror_text"] = "mirror_text"
TextRole = Literal["original_text", "mirror_text"]


class VerificationFailure(NamedTuple):
    post_id: str
    text_role: str
    embedding_id: str
    reason: str


@dataclass
class EmbeddingInstanceRow:
    """One generated embedding aligned with the plan's pointer contract."""

    post_id: str
    text_role: TextRole
    text: str
    embedding_id: str
    s3_bucket: str
    s3_key: str
    model_id: str
    dimensions: int
    normalize: bool
    embedding_vector: list[float] = field(repr=False)


@dataclass
class EmbeddingGenerationResult:
    s3_bucket: str
    dynamodb_table: str
    s3_prefix: str
    model_id: str
    dimensions: int
    normalize: bool
    text_instances: int
    embeddings_written: int
    embeddings_verified: int
    generated_rows: list[EmbeddingInstanceRow]
    failed_verifications: list[VerificationFailure]


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vectors_equivalent(a: list[float], b: list[float]) -> tuple[bool, str]:
    """Strict equality preferred; fallback to tolerance after JSON round-trip."""
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


def validate_post_ids_unique(df: pd.DataFrame, *, column: str = "post_id") -> None:
    if column not in df.columns:
        raise KeyError(f"Missing required column {column!r}")
    dup = df[df[column].duplicated(keep=False)]
    if len(dup):
        ids = dup[column].astype(str).unique().tolist()[:50]
        raise ValueError(f"Duplicate {column} values ({len(dup)} rows); sample ids: {ids}")


def build_text_instances(df: pd.DataFrame) -> list[tuple[str, TextRole, str]]:
    """Return two instances per dataframe row with validation."""
    required = ("post_id", "original_text", "mirror_text")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns for embedding: {missing}")
    validate_post_ids_unique(df)

    rows: list[tuple[str, TextRole, str]] = []
    for _, r in df.iterrows():
        pid = str(r["post_id"])
        ot = str(r["original_text"])
        mt = str(r["mirror_text"])
        if not ot.strip():
            raise ValueError(
                f"Blank original_text for post_id={pid}, text_role={TEXT_ROLE_ORIGINAL}"
            )
        if not mt.strip():
            raise ValueError(
                f"Blank mirror_text for post_id={pid}, text_role={TEXT_ROLE_MIRROR}"
            )
        rows.append((pid, TEXT_ROLE_ORIGINAL, ot))
        rows.append((pid, TEXT_ROLE_MIRROR, mt))
    return rows


def generate_embeddings(
    df: pd.DataFrame | None = None,
    *,
    bucket: str | None = None,
    table: str | None = None,
    s3_prefix: str | None = None,
    model_id: str = BEDROCK_MODEL_ID,
    dimensions: int = EMBEDDING_DIMENSIONS,
    normalize: bool = True,
    limit: int | None = None,
    skip_table_create: bool = False,
) -> EmbeddingGenerationResult:
    """Compute embeddings via Bedrock, write S3 payloads and Dynamo pointers. No verification."""
    bucket_name = (bucket or S3_BUCKET).strip()
    tbl = (table or DYNAMODB_TABLE_NAME).strip()
    prefix_raw = (s3_prefix if s3_prefix is not None else S3_PREFIX)
    normalized_prefix = prefix_raw if prefix_raw.endswith("/") or not prefix_raw else prefix_raw + "/"

    if df is None:
        df = Dataloader().load_training_dataframe()
    instances = build_text_instances(df)
    if limit is not None:
        instances = instances[: max(0, int(limit))]
    if not instances:
        raise ValueError("No text instances after filtering.")

    s3 = S3(bucket_name, region_name=AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(tbl, region_name=AWS_REGION)
    if not skip_table_create:
        ddb.ensure_table_exists()

    generated: list[EmbeddingInstanceRow] = []
    for post_id, text_role, text in tqdm(instances, desc="generate embeddings", unit="emb"):
        emb_id = embedding_identity_sha256(
            text,
            model_id=model_id,
            dimensions=dimensions,
            normalize=normalize,
        )
        key = f"{normalized_prefix}{emb_id}.json"
        payload: dict[str, Any] = create_embedding(
            text,
            model_id=model_id,
            dimensions=dimensions,
            normalize=normalize,
        )
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        s3.upload_bytes(key, body, content_type="application/json")
        row_item = {
            "embedding_id": emb_id,
            "s3_bucket": bucket_name,
            "s3_key": key,
            "text_sha256": emb_id,
            "created_at": _utc_iso_z(),
            "model_id": model_id,
            "dimensions": dimensions,
            "normalize": normalize,
            "post_id": post_id,
            "text_role": text_role,
        }
        ddb.put_item(row_item)

        vec = payload["embedding"]
        if not isinstance(vec, list):
            raise TypeError(f"embedding must be a list[float], got {type(vec)!r}")

        generated.append(
            EmbeddingInstanceRow(
                post_id=post_id,
                text_role=text_role,
                text=text,
                embedding_id=emb_id,
                s3_bucket=bucket_name,
                s3_key=key,
                model_id=model_id,
                dimensions=dimensions,
                normalize=normalize,
                embedding_vector=[float(x) for x in vec],
            )
        )

    return EmbeddingGenerationResult(
        s3_bucket=bucket_name,
        dynamodb_table=tbl,
        s3_prefix=normalized_prefix,
        model_id=model_id,
        dimensions=dimensions,
        normalize=normalize,
        text_instances=len(instances),
        embeddings_written=len(generated),
        embeddings_verified=0,
        generated_rows=generated,
        failed_verifications=[],
    )


def verify_embeddings(
    result: EmbeddingGenerationResult,
) -> EmbeddingGenerationResult:
    """Reload every pointer from DynamoDB → S3 and compare vectors."""
    failures: list[VerificationFailure] = []
    verified = 0
    s3 = S3(result.s3_bucket, region_name=AWS_REGION)
    ddb = DynamoDBEmbeddingIndex(result.dynamodb_table, region_name=AWS_REGION)

    for row in tqdm(result.generated_rows, desc="verify embeddings", unit="chk"):
        d_row = ddb.get_item(row.embedding_id)
        if d_row is None:
            failures.append(
                VerificationFailure(
                    row.post_id,
                    row.text_role,
                    row.embedding_id,
                    "missing_dynamodb_pointer",
                )
            )
            continue
        b = d_row.get("s3_bucket")
        k = d_row.get("s3_key")
        if b != row.s3_bucket or k != row.s3_key:
            failures.append(
                VerificationFailure(
                    row.post_id,
                    row.text_role,
                    row.embedding_id,
                    "dynamodb_s3_pointer_mismatch",
                )
            )
            continue

        raw = s3.get_bytes(str(k))
        parsed = json.loads(raw.decode("utf-8"))
        loaded = parsed.get("embedding")
        if loaded is None:
            failures.append(
                VerificationFailure(
                    row.post_id,
                    row.text_role,
                    row.embedding_id,
                    "missing_embedding_in_json",
                )
            )
            continue
        if not isinstance(loaded, list):
            failures.append(
                VerificationFailure(
                    row.post_id,
                    row.text_role,
                    row.embedding_id,
                    f"s3_embedding_not_list:{type(loaded)!r}",
                )
            )
            continue

        lv = [float(x) for x in loaded]
        ok, detail = _vectors_equivalent(row.embedding_vector, lv)
        if not ok:
            failures.append(
                VerificationFailure(
                    row.post_id,
                    row.text_role,
                    row.embedding_id,
                    detail,
                )
            )
            continue
        verified += 1

    new_result = EmbeddingGenerationResult(
        s3_bucket=result.s3_bucket,
        dynamodb_table=result.dynamodb_table,
        s3_prefix=result.s3_prefix,
        model_id=result.model_id,
        dimensions=result.dimensions,
        normalize=result.normalize,
        text_instances=result.text_instances,
        embeddings_written=result.embeddings_written,
        embeddings_verified=verified,
        generated_rows=list(result.generated_rows),
        failed_verifications=failures,
    )
    return new_result


def _print_summary(r: EmbeddingGenerationResult) -> None:
    console = Console()
    console.print(
        f"Instances={r.text_instances} uploaded={r.embeddings_written} "
        f"verified={r.embeddings_verified} model={r.model_id} dims={r.dimensions} "
        f"normalize={r.normalize} s3_uri=s3://{r.s3_bucket}/{r.s3_prefix} "
        f"ddb={r.dynamodb_table}"
    )


def main_inner(args: argparse.Namespace) -> EmbeddingGenerationResult:
    console = Console()
    df = Dataloader().load_training_dataframe()

    gen = generate_embeddings(
        df,
        bucket=args.bucket,
        table=args.table,
        s3_prefix=args.s3_prefix,
        normalize=args.normalize,
        limit=args.limit,
        skip_table_create=args.skip_table_create,
    )
    out = verify_embeddings(gen)
    _print_summary(out)

    if out.failed_verifications:
        console.print("[bold red]✗ FAILED[/bold red]")
        for f in out.failed_verifications[:25]:
            console.print(
                f"  post_id={f.post_id} role={f.text_role} embedding_id={f.embedding_id} "
                f"reason={f.reason}",
                style="red",
            )
        if len(out.failed_verifications) > 25:
            console.print(f"  ... and {len(out.failed_verifications) - 25} more", style="red")
        raise SystemExit(1)

    console.print("[bold green]✓ SUCCESS[/bold green]")
    return out


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate and verify embeddings for simplified keep/remove.")
    p.add_argument("--bucket", default=None, help=f"S3 bucket (default from experiment script; {S3_BUCKET})")
    p.add_argument("--table", default=None, help=f"DynamoDB table (default {DYNAMODB_TABLE_NAME})")
    p.add_argument("--s3-prefix", default=None, help=f"S3 key prefix including trailing / (default {S3_PREFIX!r})")
    p.add_argument("--limit", type=int, default=None, help="Max text instances after expansion (pairs order)")
    p.add_argument(
        "--skip-table-create",
        action="store_true",
        help="Do not ensure DynamoDB table exists before writes.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--normalize", dest="normalize", action="store_true", default=True)
    g.add_argument("--no-normalize", dest="normalize", action="store_false")
    return p


def main() -> None:
    parser = _build_arg_parser()
    parsed = parser.parse_args()
    if not str(S3_BUCKET).strip():
        raise SystemExit("S3_BUCKET is unset in experiment_create_embedding_and_upload.py.")

    Console().print(
        f"Using AWS_REGION={AWS_REGION!r}; S3 bucket={parsed.bucket or S3_BUCKET!r}; "
        f"DynamoDB={parsed.table or DYNAMODB_TABLE_NAME!r}"
    )

    main_inner(parsed)


if __name__ == "__main__":
    main()
