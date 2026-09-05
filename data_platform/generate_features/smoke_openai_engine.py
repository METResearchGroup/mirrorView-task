"""Smoke test for the OpenAI Batch feature engine.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_openai_engine.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def load_smoke_label_tasks(
    posts_csv: Path,
    post_count: int,
    id_column: str,
    text_column: str,
) -> list[LabelTask]:
    raise NotImplementedError


def compute_openai_engine_smoke_metrics(
    usage: OpenAIBatchTokenUsage,
    elapsed_seconds: float,
    labeled_count: int,
    model: str,
) -> OpenAIEngineSmokeMetrics:
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
