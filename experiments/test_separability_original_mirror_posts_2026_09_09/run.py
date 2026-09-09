"""Run the separability original vs mirror experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import sys

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    write_presentation: bool = typer.Option(
        False, "--write-presentation", help="Write the shared presentation parquet."
    ),
    engine: str | None = typer.Option(
        None, "--engine", help="Labeling engine: openai or bedrock."
    ),
    smoke: bool = typer.Option(False, "--smoke", help="Label only the smoke subset."),
    score: bool = typer.Option(False, "--score", help="Score labels and write RESULTS.md."),
) -> None:
    """Write presentations, label pairs, or score results."""
    raise NotImplementedError


if __name__ == "__main__":
    try:
        app()
    except (FileExistsError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
