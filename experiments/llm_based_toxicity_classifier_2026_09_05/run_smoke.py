"""Run a small live test of the LLM toxicity classifier with one OpenAI Batch job.

given OPENAI_API_KEY is set
and Faker can build 50 posts, 15 of which have toxic language added
when PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
then one OpenAI Batch job returns labels for 50 posts
and RESULTS.md contains elapsed seconds, estimated USD, and low, medium, and high counts that sum to 50

Run from the repo root:

    PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
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
from lib.constants import REPO_ROOT

SMOKE_POST_COUNT = 50
INJECTED_TOXIC_COUNT = 15
RANDOM_SEED = 42
INPUT_PRICE_PER_MILLION_TOKENS_USD = 0.20
OUTPUT_PRICE_PER_MILLION_TOKENS_USD = 1.25
TOKENS_PER_MILLION = 1_000_000
PERCENT_SCALE = 100
PERCENT_DECIMALS = 1
USD_DECIMALS = 4
SECONDS_DECIMALS = 2
JSON_INDENT = 2
EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "llm_based_toxicity_classifier_2026_09_05"
)
OUTPUTS_DIR = EXPERIMENT_DIR / "outputs"
SYNTHETIC_POSTS_CSV = OUTPUTS_DIR / "synthetic_posts.csv"
LABELS_JSON = OUTPUTS_DIR / "labels.json"
METRICS_JSON = OUTPUTS_DIR / "metrics.json"
RESULTS_MD = EXPERIMENT_DIR / "RESULTS.md"
SMOKE_COMMAND = (
    "PYTHONPATH=. uv run python "
    "experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py"
)


@dataclass(frozen=True)
class ToxicityLabelCounts:
    """Counts of low, medium, and high toxicity labels from one live test run."""

    low: int
    medium: int
    high: int


@dataclass(frozen=True)
class SmokeRunResult:
    """Holds the labels, token counts, and estimated cost from one OpenAI Batch toxicity test run."""

    labels: list[LlmToxicityTieredModel]
    elapsed_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    label_counts: ToxicityLabelCounts
    model: str


def openai_toxicity_spec() -> FeatureSpec:
    """Return the FeatureSpec for the LLM toxicity classifier, configured for the OpenAI Batch engine."""
    return FeatureSpec(
        name="llm_toxicity_tiered",
        model=LlmToxicityTieredModel,
        engine_type="openai",
        system_prompt=SYSTEM_PROMPT,
        llm_output_schema=LlmToxicityTieredOutputModel,
    )


def estimated_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: float,
    output_price_per_million: float,
    tokens_per_million: int,
) -> float:
    """Estimate the OpenAI Batch API cost from published token rates."""
    input_cost = input_tokens * input_price_per_million
    output_cost = output_tokens * output_price_per_million
    return (input_cost + output_cost) / tokens_per_million


def run_toxicity_smoke(posts: list[SyntheticPost]) -> SmokeRunResult:
    """Label the made-up posts in one OpenAI Batch job, and return elapsed time, token counts, and estimated cost."""
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
        estimated_cost_usd=estimated_cost_usd(
            usage.input_tokens,
            usage.output_tokens,
            INPUT_PRICE_PER_MILLION_TOKENS_USD,
            OUTPUT_PRICE_PER_MILLION_TOKENS_USD,
            TOKENS_PER_MILLION,
        ),
        label_counts=_label_counts(labels),
        model=DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
    )


def main() -> None:
    """Build 50 made-up posts and label them in one OpenAI Batch job. Write RESULTS.md."""
    posts = build_synthetic_posts(
        SMOKE_POST_COUNT,
        INJECTED_TOXIC_COUNT,
        RANDOM_SEED,
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([post.model_dump() for post in posts]).to_csv(
        SYNTHETIC_POSTS_CSV,
        index=False,
    )
    print(f"Submitting {len(posts)} posts to the OpenAI Batch API...", flush=True)
    result = run_toxicity_smoke(posts)
    _write_label_artifacts(posts, result)
    print(f"Wrote {RESULTS_MD}", flush=True)


def _write_label_artifacts(posts: list[SyntheticPost], result: SmokeRunResult) -> None:
    _write_json(LABELS_JSON, [label.model_dump() for label in result.labels])
    _write_json(METRICS_JSON, _metrics_payload(result))
    RESULTS_MD.write_text(_results_markdown(posts, result), encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=JSON_INDENT) + "\n", encoding="utf-8")


def _metrics_payload(result: SmokeRunResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": result.model,
        "post_count": SMOKE_POST_COUNT,
        "injected_toxic_count": INJECTED_TOXIC_COUNT,
        "seed": RANDOM_SEED,
        "elapsed_seconds": result.elapsed_seconds,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "estimated_cost_usd": result.estimated_cost_usd,
        "label_counts": asdict(result.label_counts),
    }
    return payload


def _percent(count: int, total: int) -> str:
    return f"{(count / total) * PERCENT_SCALE:.{PERCENT_DECIMALS}f}"


def _injected_predicted_counts(
    posts: list[SyntheticPost],
    labels: list[LlmToxicityTieredModel],
) -> ToxicityLabelCounts:
    labels_by_id = {label.source_record_id: label for label in labels}
    injected_labels = [
        labels_by_id[post.source_record_id]
        for post in posts
        if post.toxicity_was_injected
    ]
    return _label_counts(injected_labels)


def _results_markdown(posts: list[SyntheticPost], result: SmokeRunResult) -> str:
    counts = result.label_counts
    total = len(result.labels)
    injected = _injected_predicted_counts(posts, result.labels)
    return _format_results_markdown(result, counts, total, injected)


def _format_results_markdown(
    result: SmokeRunResult,
    counts: ToxicityLabelCounts,
    total: int,
    injected: ToxicityLabelCounts,
) -> str:
    return f"""# LLM toxicity classifier live test results

## Command

```bash
{SMOKE_COMMAND}
```

## Setup

- Model: `{result.model}`
- Posts: {SMOKE_POST_COUNT}
- Posts with added toxic language: {INJECTED_TOXIC_COUNT}
- Seed: {RANDOM_SEED}

## Runtime cost

| Metric | Value |
| ------ | ----- |
| Elapsed seconds | {result.elapsed_seconds:.{SECONDS_DECIMALS}f} |
| Input tokens | {result.prompt_tokens} |
| Output tokens | {result.completion_tokens} |
| Total tokens | {result.total_tokens} |
| Estimated cost (USD) | {result.estimated_cost_usd:.{USD_DECIMALS}f} |

The estimated cost is computed from the published GPT-5.4 nano Batch API rates. \
The rates are ${INPUT_PRICE_PER_MILLION_TOKENS_USD:.2f} per million input tokens and \
${OUTPUT_PRICE_PER_MILLION_TOKENS_USD:.2f} per million output tokens.

```text
(input tokens × ${INPUT_PRICE_PER_MILLION_TOKENS_USD:.2f} / {TOKENS_PER_MILLION})
  + (output tokens × ${OUTPUT_PRICE_PER_MILLION_TOKENS_USD:.2f} / {TOKENS_PER_MILLION})
```

## Counts of low, medium, and high labels

| Tier | Count | Percent |
| ---- | ----- | ------- |
| low | {counts.low} | {_percent(counts.low, total)} |
| medium | {counts.medium} | {_percent(counts.medium, total)} |
| high | {counts.high} | {_percent(counts.high, total)} |
| total | {total} | {_percent(total, total)} |

## Posts with added toxic language

The {INJECTED_TOXIC_COUNT} posts that had toxic language added were labeled \
{injected.low} low, {injected.medium} medium, and {injected.high} high. \
The live test only checks that the classifier returned labels for those posts, \
and it is not a measure of accuracy against human labels.

## Outputs

- `outputs/synthetic_posts.csv`
- `outputs/labels.json`
- `outputs/metrics.json`
"""


if __name__ == "__main__":
    main()
