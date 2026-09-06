"""Run OpenAI-matching Bedrock size jobs after cost approval.

Without --i-approve-the-cost-estimate the command exits 2 and does not call Bedrock.

    PYTHONPATH=. uv run python \\
        experiments/bedrock_batch_parallelization_2026_09_06/run_size_experiment.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import typer

from data_platform.generate_features.smoke_bedrock_engine import (
    run_bedrock_engine_smoke,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

DEFAULT_SIZES = "100,200,300,400,500,1000,2000,5000"
ID_COLUMN = "post_primary_key"
TEXT_COLUMN = "original_text"
BLOCKED_MESSAGE = (
    "blocked: size jobs wait for COST_ESTIMATE.md approval "
    "(pass --i-approve-the-cost-estimate)"
)
SOURCE_POSTS_CSV = (
    REPO_ROOT
    / "shared"
    / "data"
    / "raw"
    / "study_phase_2_part_2"
    / "stimuli"
    / "flips.csv"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "experiments"
    / "bedrock_batch_parallelization_2026_09_06"
    / "size_results.json"
)
BLOCKED_EXIT_CODE = 2


def parse_sizes(raw_sizes: str) -> tuple[int, ...]:
    """Parse a comma-separated list of positive post counts."""
    sizes = tuple(
        int(value.strip()) for value in raw_sizes.split(",") if value.strip()
    )
    if not sizes or any(count <= 0 for count in sizes):
        raise ValueError("sizes must be positive integers")
    return sizes


def main(
    sizes: str = typer.Option(DEFAULT_SIZES, "--sizes"),
    posts_csv: Path = typer.Option(SOURCE_POSTS_CSV, "--posts-csv"),
    output_json: Path = typer.Option(DEFAULT_OUTPUT_JSON, "--output-json"),
    i_approve_the_cost_estimate: bool = typer.Option(
        False,
        "--i-approve-the-cost-estimate",
    ),
) -> None:
    """Run each size through the Bedrock smoke helper after approval."""
    if not i_approve_the_cost_estimate:
        print(BLOCKED_MESSAGE, file=sys.stderr)
        raise typer.Exit(BLOCKED_EXIT_CODE)
    started_at = get_current_timestamp()
    runs: list[dict] = []
    for post_count in parse_sizes(sizes):
        print(f"Starting {post_count}-post size run", flush=True)
        metrics = run_bedrock_engine_smoke(
            posts_csv,
            post_count,
            ID_COLUMN,
            TEXT_COLUMN,
        )
        runs.append(asdict(metrics))
        payload = {
            "started_at": started_at,
            "updated_at": get_current_timestamp(),
            "model": DEFAULT_BEDROCK_NOVA_MICRO,
            "sizes": runs,
        }
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(asdict(metrics), indent=2), flush=True)


if __name__ == "__main__":
    typer.run(main)
