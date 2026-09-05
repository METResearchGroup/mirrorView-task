"""Smoke-test the LLM toxicity classifier with one OpenAI Batch job.

given OPENAI_API_KEY is set
and faker can build 50 posts with 15 injected
when PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
then one OpenAI Batch job labels 50 posts
and RESULTS.md contains elapsed seconds, estimated USD, and low/medium/high counts that sum to 50

Run from the repo root:

    PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.generate_features.llm_toxicity_tiered.generate_feature import (
    LlmToxicityTieredModel,
)
from data_platform.generate_features.models import FeatureSpec
from experiments.llm_based_toxicity_classifier_2026_09_05.synthetic_posts import (
    SyntheticPost,
    build_synthetic_posts,
)

SMOKE_POST_COUNT = 50
INJECTED_TOXIC_COUNT = 15
RANDOM_SEED = 42
INPUT_PRICE_PER_MILLION_TOKENS_USD = 0.20
OUTPUT_PRICE_PER_MILLION_TOKENS_USD = 1.25
TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ToxicityLabelCounts:
    """Counts of low, medium, and high toxicity labels from one smoke run."""

    low: int
    medium: int
    high: int


@dataclass(frozen=True)
class SmokeRunResult:
    """Labels, token usage, and cost from one OpenAI Batch toxicity smoke run."""

    labels: list[LlmToxicityTieredModel]
    elapsed_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    label_counts: ToxicityLabelCounts
    model: str


def openai_toxicity_spec() -> FeatureSpec:
    """Return the LLM toxicity feature spec for the OpenAI Batch engine."""
    raise NotImplementedError


def run_toxicity_smoke(posts: list[SyntheticPost]) -> SmokeRunResult:
    """Label synthetic posts in one OpenAI Batch and return cost metrics."""
    raise NotImplementedError


def main() -> None:
    """Build 50 synthetic posts, label them in one batch, and write RESULTS.md."""
    posts = build_synthetic_posts(
        SMOKE_POST_COUNT,
        INJECTED_TOXIC_COUNT,
        RANDOM_SEED,
    )
    run_toxicity_smoke(posts)
    raise NotImplementedError


if __name__ == "__main__":
    main()
