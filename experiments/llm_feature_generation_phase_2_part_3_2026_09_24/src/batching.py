"""Discovery batch formation for mixed and single-class LLM runs.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batching
    print(batching.DEFAULT_KEEP_PER_BATCH)
    "
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths

DEFAULT_KEEP_PER_BATCH = 10
DEFAULT_REMOVE_PER_BATCH = 10
DEFAULT_KEEP_SAMPLE_SIZE = 500
DEFAULT_REMOVE_SAMPLE_SIZE = 500
DEFAULT_POSTS_PER_BATCH = 10


def load_discovery_cohort(arm: str) -> pd.DataFrame:
    """Load discovery-split rows from the latest cohort parquet for one arm."""
    raise NotImplementedError


def form_mixed_batches(
    cohort: pd.DataFrame,
    *,
    keep_per_batch: int = DEFAULT_KEEP_PER_BATCH,
    remove_per_batch: int = DEFAULT_REMOVE_PER_BATCH,
) -> list[dict[str, Any]]:
    """Form mixed keep/remove batches with unique message ids across batches."""
    raise NotImplementedError


def form_single_class_batches(
    cohort: pd.DataFrame,
    *,
    keep_sample_size: int = DEFAULT_KEEP_SAMPLE_SIZE,
    remove_sample_size: int = DEFAULT_REMOVE_SAMPLE_SIZE,
    posts_per_batch: int = DEFAULT_POSTS_PER_BATCH,
    seed: int,
) -> list[dict[str, Any]]:
    """Sample keep and remove posts and form single-class batches."""
    raise NotImplementedError
