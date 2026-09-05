"""Measure OpenAI Batch throughput across multiple Python processes.

Run from the repository root:

    PYTHONPATH=. uv run --no-dev python \
        experiments/openai_batch_parallelization_2026_09_05/run_experiment.py
"""

from __future__ import annotations

import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Any

import typer

from data_platform.generate_features.smoke_openai_engine import (
    OpenAIEngineSmokeMetrics,
    run_openai_engine_smoke,
)
from lib.constants import DEFAULT_LLM_MODEL, REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

BATCH_SIZE_PER_PROCESS = 2_000
DEFAULT_PROCESS_COUNTS = "2,4,6,8"
INPUT_PRICE_PER_MILLION_TOKENS_USD = 0.20
OUTPUT_PRICE_PER_MILLION_TOKENS_USD = 1.25
TOKENS_PER_MILLION = 1_000_000
ID_COLUMN = "post_primary_key"
TEXT_COLUMN = "original_text"
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
    / "openai_batch_parallelization_2026_09_05"
    / "results.json"
)


def estimated_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate Batch cost from the published GPT-5.4 nano token rates."""
    input_cost = input_tokens * INPUT_PRICE_PER_MILLION_TOKENS_USD
    output_cost = output_tokens * OUTPUT_PRICE_PER_MILLION_TOKENS_USD
    return (input_cost + output_cost) / TOKENS_PER_MILLION


def run_worker(
    process_index: int,
    posts_csv: Path,
    batch_size: int,
) -> dict[str, Any]:
    """Run one 2,000-post Batch job in a spawned Python process."""
    metrics = run_openai_engine_smoke(
        posts_csv,
        batch_size,
        ID_COLUMN,
        TEXT_COLUMN,
    )
    return _worker_result(process_index, metrics)


def _worker_result(
    process_index: int,
    metrics: OpenAIEngineSmokeMetrics,
) -> dict[str, Any]:
    result = {"process_index": process_index, **asdict(metrics)}
    result["estimated_cost_usd"] = estimated_cost_usd(
        metrics.prompt_tokens,
        metrics.completion_tokens,
    )
    return result


def _aggregate_result(
    process_count: int,
    batch_size: int,
    wall_seconds: float,
    workers: list[dict[str, Any]],
) -> dict[str, Any]:
    input_tokens = sum(worker["prompt_tokens"] for worker in workers)
    output_tokens = sum(worker["completion_tokens"] for worker in workers)
    total_tokens = input_tokens + output_tokens
    total_posts = sum(worker["post_count"] for worker in workers)
    return {
        "process_count": process_count,
        "batch_size_per_process": batch_size,
        "total_posts": total_posts,
        "wall_seconds": wall_seconds,
        "posts_per_second": total_posts / wall_seconds,
        "tokens_per_second": total_tokens / wall_seconds,
        "estimated_input_tokens_per_request": input_tokens / total_posts,
        "estimated_output_tokens_per_request": output_tokens / total_posts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd(input_tokens, output_tokens),
        "workers": sorted(workers, key=lambda worker: worker["process_index"]),
    }


def run_ablation(
    process_count: int,
    posts_csv: Path,
    batch_size: int,
) -> dict[str, Any]:
    """Run one process-count ablation and return worker plus aggregate metrics."""
    worker = partial(run_worker, posts_csv=posts_csv, batch_size=batch_size)
    started_at = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=process_count,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        workers = list(executor.map(worker, range(1, process_count + 1)))
    wall_seconds = time.perf_counter() - started_at
    return _aggregate_result(process_count, batch_size, wall_seconds, workers)


def parse_process_counts(raw_process_counts: str) -> tuple[int, ...]:
    """Parse a comma-separated list of positive process counts."""
    process_counts = tuple(
        int(value.strip())
        for value in raw_process_counts.split(",")
        if value.strip()
    )
    if not process_counts or any(count <= 0 for count in process_counts):
        raise ValueError("process counts must be positive integers")
    return process_counts


def write_results(
    output_json: Path,
    posts_csv: Path,
    started_at: str,
    ablations: list[dict[str, Any]],
) -> None:
    """Write completed ablations so long experiments retain partial results."""
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_at": started_at,
        "updated_at": get_current_timestamp(),
        "model": DEFAULT_LLM_MODEL,
        "source_posts_csv": str(posts_csv.relative_to(REPO_ROOT)),
        "pricing_usd_per_million_tokens": {
            "input": INPUT_PRICE_PER_MILLION_TOKENS_USD,
            "output": OUTPUT_PRICE_PER_MILLION_TOKENS_USD,
        },
        "ablations": ablations,
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(
    process_counts: str = typer.Option(
        DEFAULT_PROCESS_COUNTS,
        "--process-counts",
    ),
    posts_csv: Path = typer.Option(SOURCE_POSTS_CSV, "--posts-csv"),
    batch_size: int = typer.Option(BATCH_SIZE_PER_PROCESS, "--batch-size"),
    output_json: Path = typer.Option(DEFAULT_OUTPUT_JSON, "--output-json"),
) -> None:
    """Run each process-count ablation and checkpoint results as JSON."""
    started_at = get_current_timestamp()
    ablations: list[dict[str, Any]] = []
    for process_count in parse_process_counts(process_counts):
        print(f"Starting {process_count}-process ablation", flush=True)
        result = run_ablation(process_count, posts_csv, batch_size)
        ablations.append(result)
        write_results(output_json, posts_csv, started_at, ablations)
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    typer.run(main)
