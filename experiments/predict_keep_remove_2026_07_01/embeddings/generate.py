"""Generate Bedrock embeddings for keep/remove rows, upload to S3 + DynamoDB, verify.
Run from repo root::
    PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/embeddings/generate.py --limit 2
"""

from __future__ import annotations

import argparse

from rich.console import Console

from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader
from experiments.simplified_predict_remove_2026_05_13.generate_embeddings import (
    generate_embeddings as simplified_generate_embeddings,
    verify_embeddings as simplified_verify_embeddings,
)


def build_embedding_dataframe():
    """Return a dataframe compatible with simplified embedding generation."""
    df = Dataloader().load_training_dataframe().copy()
    df = df.rename(columns={"message_id": "post_id"})
    # simplified generator requires these columns
    return df[["post_id", "original_text", "mirror_text"]].copy()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate and verify embeddings for predict_keep_remove (2026-07-01)."
    )
    p.add_argument("--bucket", default=None, help="S3 bucket override (default from simplified script)")
    p.add_argument("--table", default=None, help="DynamoDB table override (default from simplified script)")
    p.add_argument(
        "--s3-prefix",
        default=None,
        help="S3 key prefix including trailing / (default from simplified script)",
    )
    p.add_argument("--limit", type=int, default=None, help="Max text instances after expansion")
    p.add_argument(
        "--skip-table-create",
        action="store_true",
        help="Do not ensure DynamoDB table exists before writes.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--normalize", dest="normalize", action="store_true", default=True)
    g.add_argument("--no-normalize", dest="normalize", action="store_false")
    return p


def main_inner(args: argparse.Namespace) -> int:
    console = Console()
    df = build_embedding_dataframe()

    gen = simplified_generate_embeddings(
        df,
        bucket=args.bucket,
        table=args.table,
        s3_prefix=args.s3_prefix,
        normalize=args.normalize,
        limit=args.limit,
        skip_table_create=args.skip_table_create,
    )
    out = simplified_verify_embeddings(gen)

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
        return 1

    console.print("[bold green]✓ SUCCESS[/bold green]")
    console.print(
        f"Instances={out.text_instances} uploaded={out.embeddings_written} verified={out.embeddings_verified} "
        f"model={out.model_id} dims={out.dimensions} normalize={out.normalize} "
        f"ddb={out.dynamodb_table} s3_prefix={out.s3_prefix}"
    )
    return 0


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    raise SystemExit(main_inner(args))


if __name__ == "__main__":
    main()
