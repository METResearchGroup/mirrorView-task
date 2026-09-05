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

import time
from dataclasses import dataclass

from openai.types import BatchUsage

from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchEngine,
    build_openai_engine,
)
from data_platform.generate_features.llm_toxicity_tiered.generate_feature import (
    SYSTEM_PROMPT,
    LlmToxicityTieredModel,
    LlmToxicityTieredOutputModel,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
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
    return FeatureSpec(
        name="llm_toxicity_tiered",
        model=LlmToxicityTieredModel,
        engine_type="openai",
        system_prompt=SYSTEM_PROMPT,
        llm_output_schema=LlmToxicityTieredOutputModel,
    )


def estimated_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Estimate Batch cost from the published GPT-5.4 nano token rates."""
    input_cost = input_tokens * INPUT_PRICE_PER_MILLION_TOKENS_USD
    output_cost = output_tokens * OUTPUT_PRICE_PER_MILLION_TOKENS_USD
    return (input_cost + output_cost) / TOKENS_PER_MILLION


def run_toxicity_smoke(posts: list[SyntheticPost]) -> SmokeRunResult:
    """Label synthetic posts in one OpenAI Batch and return cost metrics."""
    engine = build_openai_engine(openai_toxicity_spec(), FeatureRunConfig())
    started_at = time.perf_counter()
    raw_labels = engine.batch_label_records(_label_tasks(posts))
    elapsed_seconds = time.perf_counter() - started_at
    usage = _require_batch_usage(engine)
    labels = [LlmToxicityTieredModel.model_validate(row) for row in raw_labels]
    return _smoke_run_result(labels, elapsed_seconds, usage)


def _label_tasks(posts: list[SyntheticPost]) -> list[LabelTask]:
    return [LabelTask(uri=post.source_record_id, text=post.text) for post in posts]


def _require_batch_usage(engine: OpenAIBatchEngine) -> BatchUsage:
    batch = engine.last_batch
    if batch is None or batch.usage is None:
        raise RuntimeError("Completed OpenAI Batch did not report token usage")
    return batch.usage


def _label_counts(labels: list[LlmToxicityTieredModel]) -> ToxicityLabelCounts:
    return ToxicityLabelCounts(
        low=sum(1 for label in labels if label.toxicity_tier == "low"),
        medium=sum(1 for label in labels if label.toxicity_tier == "medium"),
        high=sum(1 for label in labels if label.toxicity_tier == "high"),
    )


def _smoke_run_result(
    labels: list[LlmToxicityTieredModel],
    elapsed_seconds: float,
    usage: BatchUsage,
) -> SmokeRunResult:
    return SmokeRunResult(
        labels=labels,
        elapsed_seconds=elapsed_seconds,
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost_usd=estimated_cost_usd(usage.input_tokens, usage.output_tokens),
        label_counts=_label_counts(labels),
        model=DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
    )


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
