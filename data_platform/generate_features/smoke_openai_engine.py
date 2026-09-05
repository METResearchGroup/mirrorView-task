"""Smoke test for the OpenAI Batch feature engine.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_openai_engine.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_platform.generate_features.engines.openai_batch import OpenAIBatchTokenUsage
from data_platform.generate_features.models import LabelTask
from lib.constants import REPO_ROOT

SMOKE_POST_COUNT = 100
SMOKE_ID_COLUMN = "uri"
SMOKE_TEXT_COLUMN = "text"
DEFAULT_SMOKE_POSTS_CSV = (
    REPO_ROOT
    / "experiments"
    / "data_ingestion_smoke_2026_08_28"
    / "data"
    / "bluesky"
    / "bluesky_c0ffee00-0000-4000-8000-000000000100"
    / "preprocessed"
    / "2026_08_28-16:45:56"
    / "posts.csv"
)


@dataclass(frozen=True)
class OpenAIEngineSmokeMetrics:
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
    usage: OpenAIBatchTokenUsage,
    elapsed_seconds: float,
    labeled_count: int,
    model: str,
) -> OpenAIEngineSmokeMetrics:
    """Compute throughput and per-request token estimates for a smoke run."""
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")
    if usage.request_count <= 0:
        raise ValueError("request_count must be greater than 0")
    return OpenAIEngineSmokeMetrics(
        post_count=labeled_count,
        labeled_count=labeled_count,
        elapsed_seconds=elapsed_seconds,
        posts_per_second=labeled_count / elapsed_seconds,
        tokens_per_second=usage.total_tokens / elapsed_seconds,
        estimated_input_tokens_per_request=usage.prompt_tokens / usage.request_count,
        estimated_output_tokens_per_request=usage.completion_tokens / usage.request_count,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        model=model,
    )


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
