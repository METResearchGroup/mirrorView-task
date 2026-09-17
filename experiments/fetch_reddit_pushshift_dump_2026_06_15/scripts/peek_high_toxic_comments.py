"""Inspect a retained high-toxicity parquet output from the command line."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

app = typer.Typer(add_completion=False)


@app.command()
def main(
    parquet_path: Path = typer.Argument(
        ...,
        help="Path to outputs/{stem}/high_toxic_comments.parquet",
        exists=True,
        readable=True,
    ),
) -> None:
    """Print basic shape, schema, and sample rows for one parquet output."""

    df = pd.read_parquet(parquet_path)

    print(f"file: {parquet_path.resolve()}")
    print(f"shape: {df.shape}")
    print("\ncolumns and dtypes:")
    print(df.dtypes.to_string())
    print("\nhead(5):")
    print(df.head(5).to_string())


if __name__ == "__main__":
    app()
