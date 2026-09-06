"""Pricing math, per-feature smoke cost reports, and the parent cost aggregate.

Run from the repo root once all seven per-feature reports exist:

    PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \\
        --aggregate \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --smoke-reports-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke \\
        --output docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/parent_cost_aggregate.json
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import typer
from openai.types import BatchUsage

from data_platform.generate_features.engines.openai_engine import (
    CUSTOM_ID_INDEX_WIDTH,
    CUSTOM_ID_PREFIX,
)
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.generate_features.s3_feature_campaign import run_id_for_feature
from lib.timestamp_utils import get_current_timestamp

PRICING_SOURCE_URL = "https://developers.openai.com/api/docs/pricing"
DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS = 0.10
DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS = 0.625
FULL_RUN_POST_COUNT = 200_000
CAMPAIGN_LLM_FEATURES = tuple(
    name for name, spec in FEATURE_REGISTRY.items() if spec.engine_type == "openai"
)
PARENT_AGGREGATE_FILENAME = "parent_cost_aggregate.json"
COST_REPORT_SUFFIX = "_cost_report.json"
TOKENS_PER_MILLION = 1_000_000
USD_DECIMALS = 6
TOKEN_AVERAGE_DECIMALS = 2
JSON_INDENT = 2


@dataclass(frozen=True)
class BatchPricing:
    """Batch API prices in USD per million tokens and the page they were read from."""

    source_url: str
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float

    def cost_usd(self, input_tokens: float, output_tokens: float) -> float:
        """Return the unrounded USD cost of the given token counts."""
        return (
            input_tokens * self.input_usd_per_million_tokens
            + output_tokens * self.output_usd_per_million_tokens
        ) / TOKENS_PER_MILLION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequestUsage:
    """Prompt and completion tokens of one request in a completed provider batch."""

    source_record_id: str
    request_id: str
    input_tokens: int
    output_tokens: int


def request_usages_from_output_text(text: str, ordered_ids: list[str]) -> list[RequestUsage]:
    """Read the ``usage`` block of each batch output line, in ``ordered_ids`` order.

    ``ordered_ids`` maps ``task-NNNNN`` custom ids back to ``source_record_id``
    values by position. Lines whose custom id is not in that range, or whose
    response carries no ``usage`` block, are skipped.
    """
    by_custom_id: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        if line.strip():
            payload = json.loads(line)
            by_custom_id[payload["custom_id"]] = payload
    usages: list[RequestUsage] = []
    for index, source_record_id in enumerate(ordered_ids):
        custom_id = f"{CUSTOM_ID_PREFIX}{index:0{CUSTOM_ID_INDEX_WIDTH}d}"
        response = (by_custom_id.get(custom_id) or {}).get("response") or {}
        usage = (response.get("body") or {}).get("usage")
        if not usage:
            continue
        usages.append(
            RequestUsage(
                source_record_id=source_record_id,
                request_id=custom_id,
                input_tokens=int(usage["prompt_tokens"]),
                output_tokens=int(usage["completion_tokens"]),
            )
        )
    return usages


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
    """Return the per-feature smoke cost report.

    Averages divide the per-request totals by the request count, maximums are
    the largest single request, and the two full-run estimates multiply
    ``full_run_post_count`` by the per-post cost under each assumption.

    Raises
    ------
    ValueError
        When ``request_usages`` is empty.
    """
    if not request_usages:
        raise ValueError("cannot build a cost report without per-request usage")
    request_count = len(request_usages)
    input_total = sum(usage.input_tokens for usage in request_usages)
    output_total = sum(usage.output_tokens for usage in request_usages)
    avg_input = input_total / request_count
    avg_output = output_total / request_count
    max_input = max(usage.input_tokens for usage in request_usages)
    max_output = max(usage.output_tokens for usage in request_usages)
    return {
        "campaign_id": campaign_id,
        "dataset_id": dataset_id,
        "preprocessed_run": preprocessed_run,
        "feature": feature,
        "run_id": run_id_for_feature(campaign_id, feature),
        "model": model,
        "smoke_uri": smoke_uri,
        "generated_at": get_current_timestamp(),
        "batch_id": batch_id,
        "request_count": request_count,
        "pricing": pricing.as_dict(),
        "batch_usage": None
        if batch_usage is None
        else {
            "input_tokens": batch_usage.input_tokens,
            "output_tokens": batch_usage.output_tokens,
            "total_tokens": batch_usage.total_tokens,
        },
        "per_request": [asdict(usage) for usage in request_usages],
        "avg_input_tokens_per_request": round(avg_input, TOKEN_AVERAGE_DECIMALS),
        "avg_output_tokens_per_request": round(avg_output, TOKEN_AVERAGE_DECIMALS),
        "max_input_tokens_per_request": max_input,
        "max_output_tokens_per_request": max_output,
        "smoke_cost_usd": round(pricing.cost_usd(input_total, output_total), USD_DECIMALS),
        "full_run_post_count": full_run_post_count,
        "estimated_full_run_usd_avg": round(
            full_run_post_count * pricing.cost_usd(avg_input, avg_output), USD_DECIMALS
        ),
        "estimated_full_run_usd_max": round(
            full_run_post_count * pricing.cost_usd(max_input, max_output), USD_DECIMALS
        ),
        "source_record_ids": [usage.source_record_id for usage in request_usages],
    }


def cost_report_path(smoke_reports_dir: Path, feature: str) -> Path:
    """Return ``{smoke_reports_dir}/{feature}/{feature}_cost_report.json``."""
    return smoke_reports_dir / feature / f"{feature}{COST_REPORT_SUFFIX}"


def aggregate_cost_reports(
    campaign_id: str,
    smoke_reports_dir: Path,
    features: tuple[str, ...] = CAMPAIGN_LLM_FEATURES,
) -> dict[str, Any]:
    """Sum the per-feature smoke cost reports of ``features`` into one parent estimate.

    Raises
    ------
    FileNotFoundError
        Naming every missing report, when any feature has no report file.
    ValueError
        When a report describes a different campaign or feature than its path.
    """
    paths = {feature: cost_report_path(smoke_reports_dir, feature) for feature in features}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing {len(missing)} cost reports: {missing}")
    entries: list[dict[str, Any]] = []
    for feature, path in paths.items():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("campaign_id") != campaign_id or report.get("feature") != feature:
            raise ValueError(
                f"{path} describes campaign {report.get('campaign_id')!r} feature "
                f"{report.get('feature')!r}, expected {campaign_id!r} {feature!r}"
            )
        entries.append(
            {
                "feature": feature,
                "report_path": str(path),
                "model": report["model"],
                "request_count": report["request_count"],
                "avg_input_tokens_per_request": report["avg_input_tokens_per_request"],
                "avg_output_tokens_per_request": report["avg_output_tokens_per_request"],
                "max_input_tokens_per_request": report["max_input_tokens_per_request"],
                "max_output_tokens_per_request": report["max_output_tokens_per_request"],
                "smoke_cost_usd": report["smoke_cost_usd"],
                "estimated_full_run_usd_avg": report["estimated_full_run_usd_avg"],
                "estimated_full_run_usd_max": report["estimated_full_run_usd_max"],
            }
        )
    return {
        "campaign_id": campaign_id,
        "generated_at": get_current_timestamp(),
        "features_included": len(entries),
        "features": entries,
        "total_smoke_cost_usd": round(
            sum(entry["smoke_cost_usd"] for entry in entries), USD_DECIMALS
        ),
        "total_estimated_full_run_usd_avg": round(
            sum(entry["estimated_full_run_usd_avg"] for entry in entries), USD_DECIMALS
        ),
        "total_estimated_full_run_usd_max": round(
            sum(entry["estimated_full_run_usd_max"] for entry in entries), USD_DECIMALS
        ),
    }


def main(
    aggregate: bool = typer.Option(False, "--aggregate"),
    campaign_id: str = typer.Option(..., "--campaign-id"),
    smoke_reports_dir: Path = typer.Option(..., "--smoke-reports-dir"),
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Sum the seven per-feature smoke cost reports into ``output`` and print the totals."""
    if not aggregate:
        raise typer.BadParameter("pass --aggregate; it is the only mode of this command")
    document = aggregate_cost_reports(campaign_id, smoke_reports_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(document, indent=JSON_INDENT)}\n", encoding="utf-8")
    print(f"features_included={document['features_included']}")
    print(f"total_estimated_full_run_usd_avg={document['total_estimated_full_run_usd_avg']}")
    print(f"total_estimated_full_run_usd_max={document['total_estimated_full_run_usd_max']}")
    print(f"{output.name} written")


if __name__ == "__main__":
    typer.run(main)
