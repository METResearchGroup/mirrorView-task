"""Orchestrate Pushshift .zst files until stop threshold or file cap."""

from __future__ import annotations

from pathlib import Path

import typer

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    EXPERIMENT_ROOT,
    GLOBAL_STOP_COUNT,
    INPUT_GLOB,
    MAX_FILES_TO_PROCESS,
    RAW_DATA_DIR,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.runner import process_input_file
from experiments.fetch_reddit_pushshift_dump_2026_06_15.writer import load_total_metadata

app = typer.Typer(add_completion=False)


def discover_input_files() -> list[Path]:
    return sorted(RAW_DATA_DIR.glob("**/RC_*.zst"), reverse=True)


def resolve_max_files(max_files: int | None) -> int | None:
    if max_files == 0:
        return None
    if max_files is not None:
        return max_files
    return MAX_FILES_TO_PROCESS


@app.command()
def main(
    max_files: int | None = typer.Option(
        None,
        "--max-files",
        help="Cap files attempted in loop order; 0 means unlimited.",
    ),
) -> None:
    cap = resolve_max_files(max_files)
    input_files = discover_input_files()
    if not input_files:
        print(f"No input files found under {RAW_DATA_DIR}")
        raise typer.Exit(code=1)

    attempted = 0
    for input_file in input_files:
        total = load_total_metadata()
        if total.total_high_toxic >= GLOBAL_STOP_COUNT:
            print(
                f"Global stop threshold reached: total_high_toxic={total.total_high_toxic}"
            )
            break

        if cap is not None and attempted >= cap:
            print(f"Reached max_files_to_process={cap}, stopping orchestration")
            break

        attempted += 1
        process_input_file(input_file)

        total = load_total_metadata()
        if total.total_high_toxic >= GLOBAL_STOP_COUNT:
            print(
                f"Global stop threshold reached: total_high_toxic={total.total_high_toxic}"
            )
            break


if __name__ == "__main__":
    app()
