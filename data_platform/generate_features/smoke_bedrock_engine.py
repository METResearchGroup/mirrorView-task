"""Smoke test for the Bedrock Converse feature engine.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_bedrock_engine.py
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import typer

from data_platform.generate_features.engines.bedrock_engine import (
    BedrockUsage,
    build_bedrock_engine,
)
from data_platform.generate_features.is_news_or_opinion.generate_feature import (
    SYSTEM_PROMPT as IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
)
from data_platform.generate_features.is_news_or_opinion.generate_feature import (
    IsNewsOrOpinionModel,
    LlmIsNewsOrOpinionModel,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec
from data_platform.generate_features.smoke_openai_engine import load_smoke_label_tasks
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, REPO_ROOT

SMOKE_POST_COUNT = 100
SMOKE_MAX_CONCURRENCY = 8
SMOKE_ID_COLUMN = "post_primary_key"
SMOKE_TEXT_COLUMN = "original_text"
SMOKE_METRICS_JSON_INDENT = 2
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
TOKENS_PER_MILLION = 1_000_000
DEFAULT_SMOKE_POSTS_CSV = (
    REPO_ROOT
    / "shared"
    / "data"
    / "raw"
    / "study_phase_2_part_2"
    / "stimuli"
    / "flips.csv"
)
DEFAULT_METRICS_JSON = (
    REPO_ROOT
    / "experiments"
    / "bedrock_batch_parallelization_2026_09_06"
    / "smoke_metrics.json"
)
DEFAULT_SMOKE_RESULTS = (
    REPO_ROOT
    / "experiments"
    / "bedrock_batch_parallelization_2026_09_06"
    / "SMOKE_RESULTS.md"
)


@dataclass(frozen=True)
class BedrockEngineSmokeMetrics:
    """Throughput, token, and dollar estimates from one Bedrock engine smoke run."""

    post_count: int
    labeled_count: int
    elapsed_seconds: float
    posts_per_second: float
    tokens_per_second: float
    estimated_input_tokens_per_request: float
    estimated_output_tokens_per_request: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    estimated_cost_usd: float


def estimated_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate on-demand Nova Micro cost from Ohio token rates."""
    input_cost = input_tokens * ON_DEMAND_INPUT_USD_PER_MILLION
    output_cost = output_tokens * ON_DEMAND_OUTPUT_USD_PER_MILLION
    return (input_cost + output_cost) / TOKENS_PER_MILLION


def compute_bedrock_engine_smoke_metrics(
    usage: BedrockUsage,
    request_count: int,
    elapsed_seconds: float,
    labeled_count: int,
    model: str,
) -> BedrockEngineSmokeMetrics:
    """Compute throughput, token, and dollar estimates for a smoke run."""
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")
    if request_count <= 0:
        raise ValueError("request_count must be greater than 0")
    return BedrockEngineSmokeMetrics(
        post_count=labeled_count,
        labeled_count=labeled_count,
        elapsed_seconds=elapsed_seconds,
        posts_per_second=labeled_count / elapsed_seconds,
        tokens_per_second=usage.total_tokens / elapsed_seconds,
        estimated_input_tokens_per_request=usage.input_tokens / request_count,
        estimated_output_tokens_per_request=usage.output_tokens / request_count,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        model=model,
        estimated_cost_usd=estimated_cost_usd(
            usage.input_tokens,
            usage.output_tokens,
        ),
    )


def news_or_opinion_bedrock_spec() -> FeatureSpec:
    """Return the news-or-opinion feature spec for the Bedrock Converse engine."""
    return FeatureSpec(
        name="is_news_or_opinion",
        model=IsNewsOrOpinionModel,
        engine_type="bedrock",
        system_prompt=IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
        llm_output_schema=LlmIsNewsOrOpinionModel,
    )


def run_bedrock_engine_smoke(
    posts_csv: Path,
    post_count: int,
    id_column: str,
    text_column: str,
) -> BedrockEngineSmokeMetrics:
    """Label posts with the Bedrock engine and return smoke-test metrics."""
    tasks = load_smoke_label_tasks(posts_csv, post_count, id_column, text_column)
    print(f"Submitting {len(tasks)} posts to Bedrock Converse...", flush=True)
    engine = build_bedrock_engine(
        news_or_opinion_bedrock_spec(),
        FeatureRunConfig(max_concurrency=SMOKE_MAX_CONCURRENCY),
    )
    started_at = time.perf_counter()
    labels = engine.batch_label_records(tasks)
    elapsed_seconds = time.perf_counter() - started_at
    usage = engine.last_usage
    if usage is None:
        raise RuntimeError("Completed Bedrock run did not report token usage")
    return compute_bedrock_engine_smoke_metrics(
        usage,
        len(tasks),
        elapsed_seconds,
        len(labels),
        DEFAULT_BEDROCK_NOVA_MICRO,
    )


def _write_smoke_results(
    metrics: BedrockEngineSmokeMetrics,
    metrics_json: Path,
    results_md: Path,
) -> None:
    metrics_json.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(metrics)
    metrics_json.write_text(
        json.dumps(payload, indent=SMOKE_METRICS_JSON_INDENT) + "\n",
        encoding="utf-8",
    )
    results_md.write_text(
        "# Bedrock Nova Micro smoke results\n\n"
        f"Model: `{metrics.model}`\n\n"
        "| Posts | Elapsed seconds | Posts per second | Tokens per second "
        "| Mean input tokens | Mean output tokens | Input tokens "
        "| Output tokens | Total tokens | Estimated cost (USD) |\n"
        "| ----- | --------------- | ---------------- | ----------------- "
        "| ----------------- | ------------------ | ------------ "
        "| ------------- | ------------ | -------------------- |\n"
        f"| {metrics.labeled_count} "
        f"| {metrics.elapsed_seconds:.2f} "
        f"| {metrics.posts_per_second:.2f} "
        f"| {metrics.tokens_per_second:.2f} "
        f"| {metrics.estimated_input_tokens_per_request:.2f} "
        f"| {metrics.estimated_output_tokens_per_request:.2f} "
        f"| {metrics.prompt_tokens:,} "
        f"| {metrics.completion_tokens:,} "
        f"| {metrics.total_tokens:,} "
        f"| ${metrics.estimated_cost_usd:.4f} |\n",
        encoding="utf-8",
    )


def main(
    posts_csv: Path = typer.Option(DEFAULT_SMOKE_POSTS_CSV, "--posts-csv"),
    post_count: int = typer.Option(SMOKE_POST_COUNT, "--post-count"),
    id_column: str = typer.Option(SMOKE_ID_COLUMN, "--id-column"),
    text_column: str = typer.Option(SMOKE_TEXT_COLUMN, "--text-column"),
) -> None:
    """Run the Bedrock Converse news-or-opinion smoke test and print metrics JSON."""
    metrics = run_bedrock_engine_smoke(posts_csv, post_count, id_column, text_column)
    _write_smoke_results(metrics, DEFAULT_METRICS_JSON, DEFAULT_SMOKE_RESULTS)
    print(json.dumps(asdict(metrics), indent=SMOKE_METRICS_JSON_INDENT))


if __name__ == "__main__":
    typer.run(main)
