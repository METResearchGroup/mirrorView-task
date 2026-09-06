"""Pricing math, per-feature smoke cost reports, and the parent cost aggregate.

Run from the repo root once all seven per-feature reports exist:

    PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \\
        --aggregate \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --smoke-reports-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke \\
        --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/parent_cost_aggregate.json
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from openai.types import BatchUsage

from data_platform.generate_features.registry import FEATURE_REGISTRY

PRICING_SOURCE_URL = "https://developers.openai.com/api/docs/pricing"
DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS = 0.10
DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS = 0.625
FULL_RUN_POST_COUNT = 200_000
CAMPAIGN_LLM_FEATURES = tuple(
    name for name, spec in FEATURE_REGISTRY.items() if spec.engine_type == "openai"
)
PARENT_AGGREGATE_FILENAME = "parent_cost_aggregate.json"


@dataclass(frozen=True)
class BatchPricing:
    source_url: str
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class RequestUsage:
    source_record_id: str
    request_id: str
    input_tokens: int
    output_tokens: int


def request_usages_from_output_text(text: str, ordered_ids: list[str]) -> list[RequestUsage]:
    raise NotImplementedError


def build_feature_cost_report(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    model: str,
    smoke_uri: str,
    batch_id: str,
    batch_usage: BatchUsage | None,
    request_usages: list[RequestUsage],
    pricing: BatchPricing,
    full_run_post_count: int = FULL_RUN_POST_COUNT,
) -> dict[str, Any]:
    raise NotImplementedError


def cost_report_path(smoke_reports_dir: Path, feature: str) -> Path:
    raise NotImplementedError


def aggregate_cost_reports(
    campaign_id: str,
    smoke_reports_dir: Path,
    features: tuple[str, ...] = CAMPAIGN_LLM_FEATURES,
) -> dict[str, Any]:
    raise NotImplementedError


def main(
    aggregate: bool = typer.Option(False, "--aggregate"),
    campaign_id: str = typer.Option(..., "--campaign-id"),
    smoke_reports_dir: Path = typer.Option(..., "--smoke-reports-dir"),
    output: Path = typer.Option(..., "--output"),
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
