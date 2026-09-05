"""Smoke test for the OpenAI Batch feature engine.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_openai_engine.py
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import typer
from openai.types import BatchUsage

from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    build_openai_engine,
)
from data_platform.generate_features.is_news_or_opinion.generate_feature import (
    SYSTEM_PROMPT as IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
)
from data_platform.generate_features.is_news_or_opinion.generate_feature import (
    IsNewsOrOpinionModel,
    LlmIsNewsOrOpinionModel,
)
from data_platform.generate_features.models import (
    FeatureRunConfig,
    FeatureSpec,
    LabelTask,
)
from lib.constants import REPO_ROOT

SMOKE_POST_COUNT = 100
SMOKE_ID_COLUMN = "post_primary_key"
SMOKE_TEXT_COLUMN = "original_text"
SMOKE_METRICS_JSON_INDENT = 2
DEFAULT_SMOKE_POSTS_CSV = (
    REPO_ROOT
    / "shared"
    / "data"
    / "raw"
    / "study_phase_2_part_1"
    / "stimuli"
    / "claude_generated_mirrors.csv"
)


@dataclass(frozen=True)
class OpenAIEngineSmokeMetrics:
    """Throughput and token estimates from one OpenAI engine smoke run."""
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


def _cell_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_smoke_label_tasks(
    posts_csv: Path,
    post_count: int,
    id_column: str,
    text_column: str,
) -> list[LabelTask]:
    """Load the first post_count posts that have non-empty text."""
    records = pd.read_csv(posts_csv)
    tasks: list[LabelTask] = []
    for _, row in records.iterrows():
        text = _cell_text(row[text_column])
        if not text:
            continue
        tasks.append(LabelTask(uri=str(row[id_column]), text=text))
        if len(tasks) == post_count:
            return tasks
    raise ValueError(
        f"Need {post_count} posts with text in {posts_csv}, found {len(tasks)}"
    )


def compute_openai_engine_smoke_metrics(
    usage: BatchUsage,
    request_count: int,
    elapsed_seconds: float,
    labeled_count: int,
    model: str,
) -> OpenAIEngineSmokeMetrics:
    """Compute throughput and per-request token estimates for a smoke run."""
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")
    if request_count <= 0:
        raise ValueError("request_count must be greater than 0")
    return OpenAIEngineSmokeMetrics(
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
    )


def news_or_opinion_openai_spec() -> FeatureSpec:
    """Return the news-or-opinion feature spec for the OpenAI Batch engine."""
    return FeatureSpec(
        name="is_news_or_opinion",
        model=IsNewsOrOpinionModel,
        engine_type="openai",
        system_prompt=IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
        llm_output_schema=LlmIsNewsOrOpinionModel,
    )


def run_openai_engine_smoke(
    posts_csv: Path,
    post_count: int,
    id_column: str,
    text_column: str,
) -> OpenAIEngineSmokeMetrics:
    """Label posts with the OpenAI engine and return smoke-test metrics."""
    tasks = load_smoke_label_tasks(posts_csv, post_count, id_column, text_column)
    print(f"Submitting {len(tasks)} posts to the OpenAI Batch API...", flush=True)
    engine = build_openai_engine(
        news_or_opinion_openai_spec(),
        FeatureRunConfig(),
    )
    started_at = time.perf_counter()
    labels = engine.batch_label_records(tasks)
    elapsed_seconds = time.perf_counter() - started_at
    batch = engine.last_batch
    if batch is None or batch.usage is None:
        raise RuntimeError("Completed OpenAI Batch did not report token usage")
    return compute_openai_engine_smoke_metrics(
        batch.usage,
        batch.request_counts.completed,
        elapsed_seconds,
        len(labels),
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
    )


def main(
    posts_csv: Path = typer.Option(DEFAULT_SMOKE_POSTS_CSV, "--posts-csv"),
    post_count: int = typer.Option(SMOKE_POST_COUNT, "--post-count"),
    id_column: str = typer.Option(SMOKE_ID_COLUMN, "--id-column"),
    text_column: str = typer.Option(SMOKE_TEXT_COLUMN, "--text-column"),
) -> None:
    """Run the OpenAI Batch news-or-opinion smoke test and print metrics JSON."""
    metrics = run_openai_engine_smoke(posts_csv, post_count, id_column, text_column)
    print(json.dumps(asdict(metrics), indent=SMOKE_METRICS_JSON_INDENT))


if __name__ == "__main__":
    typer.run(main)
