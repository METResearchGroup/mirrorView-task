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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.generate_features.campaign_cost_report import (
    DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS,
    DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_SOURCE_URL,
    BatchPricing,
    RequestUsage,
)
from data_platform.generate_features.deterministic_smoke_sample import (
    load_deterministic_ten_posts,
)
from data_platform.generate_features.engines.openai_engine import (
    OpenAIBatchClient,
    OpenAIBatchEngine,
)
from data_platform.generate_features.models import FeatureSpec
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
)
from lib.constants import REPO_ROOT

DEFAULT_SMOKE_REPORTS_DIR = (
    REPO_ROOT / "docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke"
)
FILES_CREATE_CALL = "files.create"
BATCHES_CREATE_CALL = "batches.create"
SMOKE_BATCH_INDEX = 0
SMOKE_ATTEMPT_COUNT = 1
COST_REPORT_SUFFIX = "_cost_report.json"
RESUME_EVIDENCE_SUFFIX = "_resume_evidence.json"
S3_CHECKS_SUFFIX = "_s3_checks.txt"
CHECK_SMOKE_OUTPUT_OK = "s3_smoke_output_ok"
CHECK_RESUME_EVIDENCE_OK = "s3_smoke_resume_evidence_ok"
CHECK_NO_BATCHES = "no_batches_prefix_objects"
CHECK_CANONICAL_TOUCHED = "canonical_smoke_prefix_touched"


class _CountingNamespace:
    """Delegates to ``client.files`` or ``client.batches`` and counts ``create`` calls."""

    def __init__(self, target: Any, calls: Counter[str], call_name: str) -> None:
        self._target = target
        self._calls = calls
        self._call_name = call_name

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError


class CountingOpenAIClient:
    """OpenAI client wrapper whose ``calls`` counter records every upload and batch creation."""

    def __init__(self, client: OpenAIBatchClient) -> None:
        self.calls: Counter[str] = Counter()
        self.files: Any = _CountingNamespace(client.files, self.calls, FILES_CREATE_CALL)
        self.batches: Any = _CountingNamespace(client.batches, self.calls, BATCHES_CREATE_CALL)


@dataclass(frozen=True)
class SmokePaths:
    """Smoke paths in use plus the canonical paths they must not overlap."""

    paths: FeaturePaths
    canonical: FeaturePaths
    smoke_prefix_uri: str


@dataclass(frozen=True)
class InterruptedJob:
    """The provider job state saved before the deliberate interruption, and the calls it took."""

    state: dict[str, Any]
    submit_calls: dict[str, int]
    interrupted_at: str


@dataclass(frozen=True)
class ResumedJob:
    """Rows and usage collected by the engine that reattached to the interrupted job."""

    rows: list[dict[str, Any]]
    request_usages: list[RequestUsage]
    engine: OpenAIBatchEngine
    resume_calls: dict[str, int]
    resumed_at: str


@dataclass(frozen=True)
class SmokeResult:
    """Everything one smoke run produced, for printing and for the Git copies."""

    smoke_prefix_uri: str
    cost_report: dict[str, Any]
    resume_evidence: dict[str, Any]
    checks: dict[str, bool]
    cost_report_path: Path


def build_smoke_paths(
    campaign_id: str, dataset_id: str, feature: str, smoke_prefix: str | None
) -> SmokePaths:
    raise NotImplementedError


def submit_and_interrupt(
    client: CountingOpenAIClient,
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_dir: Path,
) -> InterruptedJob:
    raise NotImplementedError


def resume_and_collect_rows(
    client: CountingOpenAIClient,
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_dir: Path,
    run_id: str,
) -> ResumedJob:
    raise NotImplementedError


def build_resume_evidence(
    *,
    feature: str,
    run_id: str,
    interrupted: InterruptedJob,
    resumed: ResumedJob,
) -> dict[str, Any]:
    raise NotImplementedError


def write_smoke_objects(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    posts: pd.DataFrame,
    rows: list[dict[str, Any]],
    spec: FeatureSpec,
    cost_report: dict[str, Any],
    resume_evidence: dict[str, Any],
) -> None:
    raise NotImplementedError


def run_s3_checks(
    store: CampaignObjectStore,
    smoke_paths: SmokePaths,
    *,
    spec: FeatureSpec,
    canonical_smoke_keys_before: list[str],
) -> tuple[dict[str, bool], list[str]]:
    raise NotImplementedError


def write_git_copies(
    output_dir: Path,
    feature: str,
    *,
    cost_report: dict[str, Any],
    resume_evidence: dict[str, Any],
    check_lines: list[str],
) -> Path:
    raise NotImplementedError


def run_campaign_smoke(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    smoke_prefix: str | None,
    output_dir: Path,
    pricing: BatchPricing,
    client_factory: Callable[[], OpenAIBatchClient] | None = None,
) -> SmokeResult:
    raise NotImplementedError


def summary_lines(result: SmokeResult) -> list[str]:
    raise NotImplementedError


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
    for line in summary_lines(result):
        print(line)
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
