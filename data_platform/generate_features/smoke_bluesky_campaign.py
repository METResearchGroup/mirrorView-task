"""Ten-post smoke for one feature of a Bluesky LLM campaign, with an interrupt-and-resume proof.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --feature is_news_or_opinion

Pass ``--smoke-prefix s3://bucket/root/`` to write under ``root/{feature}/smoke/``
instead of the canonical campaign feature prefix.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

from data_platform.generate_features.campaign_cost_report import (
    DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS,
    DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_SOURCE_URL,
    BatchPricing,
)
from data_platform.generate_features.deterministic_smoke_sample import (
    load_deterministic_ten_posts,
)
from data_platform.generate_features.engines.openai_engine import (
    OpenAIBatchClient,
)
from data_platform.generate_features.s3_feature_campaign import FeaturePaths
from lib.constants import REPO_ROOT

DEFAULT_SMOKE_REPORTS_DIR = (
    REPO_ROOT / "docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke"
)


class CountingOpenAIClient:
    def __init__(self, client: OpenAIBatchClient) -> None:
        self.calls: Counter[str] = Counter()
        self.files: Any = client.files
        self.batches: Any = client.batches


@dataclass(frozen=True)
class SmokeResult:
    cost_report: dict[str, Any]
    resume_evidence: dict[str, Any]
    checks: dict[str, bool]
    cost_report_path: Path


def run_campaign_smoke(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    smoke_prefix: str | None,
    output_dir: Path,
    pricing: BatchPricing,
) -> SmokeResult:
    paths = FeaturePaths.canonical(campaign_id, feature, dataset_id=dataset_id)
    posts = load_deterministic_ten_posts(dataset_id, preprocessed_run)
    raise NotImplementedError(f"{paths.prefix} {len(posts)}")


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str | None = typer.Option(None, "--smoke-prefix"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
    input_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS, "--input-usd-per-million-tokens"
    ),
    output_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS, "--output-usd-per-million-tokens"
    ),
) -> None:
    result = run_campaign_smoke(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        smoke_prefix=smoke_prefix,
        output_dir=output_dir or DEFAULT_SMOKE_REPORTS_DIR / feature,
        pricing=BatchPricing(
            source_url=PRICING_SOURCE_URL,
            input_usd_per_million_tokens=input_usd_per_million_tokens,
            output_usd_per_million_tokens=output_usd_per_million_tokens,
        ),
    )
    print(f"cost_report={result.cost_report_path}")


if __name__ == "__main__":
    typer.run(main)
