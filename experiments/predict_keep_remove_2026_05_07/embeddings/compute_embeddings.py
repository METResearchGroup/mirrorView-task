"""Precompute OpenAI embeddings for keep/remove training texts (CLI).

Run (after ``uv sync --group dev`` and analysis label CSVs exist):

PYTHONPATH=. uv run python \\
  experiments/predict_keep_remove_2026_05_07/embeddings/compute_embeddings.py run \\
  --dry-run

See ``metadata.json`` and Parquet outputs under ``--output-dir``.
"""

from __future__ import annotations

from pathlib import Path

import typer

from experiments.predict_keep_remove_2026_05_07.embeddings.compute import (
    run_embedding_pipeline,
)
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)

_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_OUTPUT_ROOT = _EXPERIMENT_DIR / "embeddings" / "outputs"


@app.command("run")
def run_command(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for Parquet + metadata (default: embeddings/outputs/<timestamp>).",
    ),
    model: str = typer.Option(
        "text-embedding-3-small",
        "--model",
        help="OpenAI embedding model id.",
    ),
    batch_size: int = typer.Option(
        128,
        "--batch-size",
        min=1,
        max=2048,
        help="Number of texts per embeddings.create call.",
    ),
    input_cache: Path | None = typer.Option(
        None,
        "--input-cache",
        help="Optional Parquet of prior hash-level embeddings (text_hash, embedding_model, ...).",
    ),
    write_cache: Path | None = typer.Option(
        None,
        "--write-cache",
        help="Optional path to write merged hash-level cache after this run.",
    ),
    l2_normalize: bool = typer.Option(
        True,
        "--l2-normalize/--no-l2-normalize",
        help="L2-normalize each embedding vector before saving.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only write text_instances.parquet + metadata (no API calls).",
    ),
    omit_text: bool = typer.Option(
        False,
        "--omit-text",
        help="Drop raw ``text`` from embedding rows in the main Parquet (smaller files).",
    ),
) -> None:
    """Build text-instance table and optionally call OpenAI embeddings."""
    out = output_dir
    if out is None:
        out = _DEFAULT_OUTPUT_ROOT / get_current_timestamp()

    result = run_embedding_pipeline(
        output_dir=out,
        embedding_model=model,
        batch_size=batch_size,
        input_cache_path=input_cache,
        write_cache_path=write_cache,
        l2_normalize=l2_normalize,
        dry_run=dry_run,
        omit_text_column=omit_text,
    )

    typer.echo(f"Output directory: {result.output_dir}")
    typer.echo(f"Metadata: {result.metadata_path}")
    if result.text_instances_path is not None:
        typer.echo(f"Text instances: {result.text_instances_path}")
    if result.embeddings_text_instances_path is not None:
        typer.echo(f"Embeddings (long): {result.embeddings_text_instances_path}")
        typer.echo(f"Sidecar original: {result.original_sidecar_path}")
        typer.echo(f"Sidecar mirrors: {result.mirrors_sidecar_path}")
    typer.echo(
        f"Instances={result.n_text_instances}, unique_hashes={result.n_unique_text_hashes}, "
        f"new_api_hashes={result.n_embedded_new}, reused={result.n_reused_from_cache}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
