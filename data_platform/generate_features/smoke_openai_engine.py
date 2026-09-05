"""Smoke test for the OpenAI Batch feature engine.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_openai_engine.py
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.models import LabelTask


def load_smoke_label_tasks(
    posts_csv: Path,
    post_count: int,
    id_column: str,
    text_column: str,
) -> list[LabelTask]:
    raise NotImplementedError


def compute_openai_engine_smoke_metrics(
    usage: object,
    elapsed_seconds: float,
    labeled_count: int,
    model: str,
) -> object:
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
