"""Orchestrate Pushshift .zst files until stop threshold or file cap."""

from __future__ import annotations

from pathlib import Path

import typer

from experiments.fetch_reddit_pushshift_dump_2026_06_15.api_budget import (
    api_calls_used,
    budget_exhausted,
    reset_session_budget,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    GLOBAL_STOP_COUNT,
    MAX_FILES_TO_PROCESS,
    MAX_SESSION_API_CALLS,
    RAW_DATA_DIR,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.runner import process_input_file
from experiments.fetch_reddit_pushshift_dump_2026_06_15.writer import load_total_metadata

app = typer.Typer(add_completion=False)

IGNORED_INPUT_STEMS = frozenset({"RC_smoke_fixture"})


def discover_input_files(prefixes: tuple[str, ...] | None = None) -> list[Path]:
    files = [
        path
        for path in RAW_DATA_DIR.glob("**/RC_*.zst")
        if path.stem not in IGNORED_INPUT_STEMS
    ]
    if prefixes:
        files = [path for path in files if path.stem.startswith(prefixes)]
    return sorted(files)


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
    stem_prefix: str | None = typer.Option(
        None,
        "--stem-prefix",
        help="Comma-separated filename stem prefixes to include (e.g. RC_2005,RC_2006).",
    ),
) -> None:
    reset_session_budget()
    cap = resolve_max_files(max_files)
    prefixes = tuple(p.strip() for p in stem_prefix.split(",") if p.strip()) if stem_prefix else None
    input_files = discover_input_files(prefixes=prefixes)
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

        if budget_exhausted():
            print(
                f"Session API budget exhausted ({api_calls_used()} / "
                f"{MAX_SESSION_API_CALLS} calls)"
            )
            break

        attempted += 1
        process_input_file(input_file)

        if budget_exhausted():
            print(
                f"Session API budget exhausted ({api_calls_used()} / "
                f"{MAX_SESSION_API_CALLS} calls)"
            )
            break

        total = load_total_metadata()
        if total.total_high_toxic >= GLOBAL_STOP_COUNT:
            print(
                f"Global stop threshold reached: total_high_toxic={total.total_high_toxic}"
            )
            break


if __name__ == "__main__":
    app()
