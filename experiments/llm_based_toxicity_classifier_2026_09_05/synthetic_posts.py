"""Build synthetic social media posts for the LLM toxicity smoke test.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SyntheticPost(BaseModel):
    """One synthetic smoke-test post, including whether toxic language was injected."""

    source_record_id: str
    text: str
    toxicity_was_injected: bool
    injected_tier: Literal["medium", "high"] | None


def build_synthetic_posts(
    post_count: int,
    injected_toxic_count: int,
    seed: int,
) -> list[SyntheticPost]:
    """Build Faker posts and inject toxic language into a random subset.

    Parameters
    ----------
    post_count
        Number of posts to build.
    injected_toxic_count
        How many of those posts receive injected toxic language.
    seed
        Seed for Faker and for choosing which posts are injected.

    Returns
    -------
    list[SyntheticPost]
        Posts with ids, text, and injection flags.

    Raises
    ------
    ValueError
        When ``injected_toxic_count`` is outside ``[0, post_count]``.
    """
    raise NotImplementedError
