"""Build synthetic social media posts for the LLM toxicity smoke test.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SyntheticPost(BaseModel):
    pass


def build_synthetic_posts(
    post_count: int,
    injected_toxic_count: int,
    seed: int,
) -> list[SyntheticPost]:
    """Build Faker posts and inject toxic language into a random subset."""
    raise NotImplementedError
