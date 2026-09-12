"""Smoke token loading and cost estimate tables for the experiment."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from typing import Any

from data_platform.generate_features.campaign_cost_report import (
    BatchPricing,
    PRICING_SOURCE_URL,
    BEDROCK_PRICING_SOURCE_URL,
)
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    s3_uri,
)
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CostRow,
    CohortTrial,
    CohortUser,
    EXPERIMENT_S3_PREFIX,
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA,
    MODEL_FOLDER_BEDROCK_QWEN,
    MODEL_FOLDER_OPENAI,
    OUTPUT_S3_BUCKET,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import render_user_prompt
from experiments.ai_simulation_responses_2026_09_11.shared.write import put_new_mirrored

TOKEN_USAGE_FILENAME = "token_usage.json"
COST_ESTIMATE_RELATIVE_PATH = f"{EXPERIMENT_S3_PREFIX}COST_ESTIMATE.md"
LOW_COST_MULTIPLIER = 0.5
HIGH_COST_MULTIPLIER = 2.0
USD_DECIMALS = 2

OPENAI_PRICING = BatchPricing(
    source_url=PRICING_SOURCE_URL,
    input_usd_per_million_tokens=0.10,
    output_usd_per_million_tokens=0.625,
)
NOVA_PRICING = BatchPricing(
    source_url=BEDROCK_PRICING_SOURCE_URL,
    input_usd_per_million_tokens=0.035,
    output_usd_per_million_tokens=0.14,
)
QWEN_PRICING = BatchPricing(
    source_url=BEDROCK_PRICING_SOURCE_URL,
    input_usd_per_million_tokens=0.15,
    output_usd_per_million_tokens=0.60,
)
CLAUDE_PRICING = BatchPricing(
    source_url=BEDROCK_PRICING_SOURCE_URL,
    input_usd_per_million_tokens=3.00,
    output_usd_per_million_tokens=15.00,
)

MODEL_PRICING = {
    MODEL_FOLDER_OPENAI: OPENAI_PRICING,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA: NOVA_PRICING,
    MODEL_FOLDER_BEDROCK_QWEN: QWEN_PRICING,
    MODEL_FOLDER_BEDROCK_CLAUDE: CLAUDE_PRICING,
}

MODEL_ORDER = (
    MODEL_FOLDER_OPENAI,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA,
    MODEL_FOLDER_BEDROCK_QWEN,
    MODEL_FOLDER_BEDROCK_CLAUDE,
)


@dataclass(frozen=True)
class TokenUsageRecord:
    """Per-request token counts from one smoke label."""

    source_record_id: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class MedianTokens:
    """Median input and output tokens across successful smoke requests."""

    input_tokens: float
    output_tokens: float


@dataclass(frozen=True)
class ExperimentCostSection:
    """Cost table rows for one experiment."""

    experiment_number: int
    rows: tuple[CostRow, ...]


def token_usage_key(paths: FeaturePaths) -> str:
    """Return the smoke token usage object key."""
    return f"{paths.prefix}{TOKEN_USAGE_FILENAME}"


def save_token_usage(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    usages: list[TokenUsageRecord],
) -> None:
    """Persist per-request smoke token counts under the smoke prefix."""
    if store.get(token_usage_key(paths)) is not None:
        return
    body = json.dumps([asdict(usage) for usage in usages], indent=2).encode("utf-8")
    store.put_new(token_usage_key(paths), body)


def load_token_usage(store: CampaignObjectStore, paths: FeaturePaths) -> list[TokenUsageRecord]:
    """Load per-request smoke token counts."""
    stored = store.get(token_usage_key(paths))
    if stored is None:
        raise FileNotFoundError(
            f"Missing smoke token usage: {paths.uri(token_usage_key(paths))}"
        )
    records = json.loads(stored.body.decode("utf-8"))
    return [TokenUsageRecord(**record) for record in records]


def median_tokens(usages: list[TokenUsageRecord]) -> MedianTokens:
    """Return median input and output tokens across successful smoke requests."""
    if not usages:
        return MedianTokens(0.0, 0.0)
    input_values = [usage.input_tokens for usage in usages]
    output_values = [usage.output_tokens for usage in usages]
    return MedianTokens(
        input_tokens=statistics.median(input_values),
        output_tokens=statistics.median(output_values),
    )


def mean_prompt_chars(
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    experiment_number: int,
) -> float:
    """Return mean rendered prompt length for one experiment."""
    lengths = [
        len(render_user_prompt(experiment_number, user, trials_by_user[user.prolific_id]))
        for user in users
    ]
    return sum(lengths) / len(lengths)


def scale_input_tokens(
    median_input: float,
    user_count: int,
    length_ratio: float,
) -> int:
    """Scale experiment 1 median input tokens to another experiment."""
    return int(round(median_input * user_count * length_ratio))


def scale_output_tokens(median_output: float, user_count: int) -> int:
    """Scale experiment 1 median output tokens to the full cohort."""
    return int(round(median_output * user_count))


def cost_row_for_model(
    model_folder: str,
    tokens_in: int,
    tokens_out: int,
) -> CostRow:
    """Build one cost table row for a model."""
    pricing = MODEL_PRICING[model_folder]
    median = pricing.cost_usd(tokens_in, tokens_out)
    return CostRow(
        model=model_folder,
        estimated_tokens_in=tokens_in,
        estimated_tokens_out=tokens_out,
        median_cost_usd=round(median, USD_DECIMALS),
        low_cost_usd=round(median * LOW_COST_MULTIPLIER, USD_DECIMALS),
        high_cost_usd=round(median * HIGH_COST_MULTIPLIER, USD_DECIMALS),
    )


def build_experiment_sections(
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    medians_by_model: dict[str, MedianTokens],
) -> tuple[ExperimentCostSection, ...]:
    """Build cost sections for experiments 1 through 4."""
    user_count = len(users)
    exp1_chars = mean_prompt_chars(users, trials_by_user, 1)
    sections: list[ExperimentCostSection] = []
    for experiment_number in range(1, 5):
        ratio = 1.0
        if experiment_number != 1:
            exp_chars = mean_prompt_chars(users, trials_by_user, experiment_number)
            ratio = exp_chars / exp1_chars if exp1_chars else 1.0
        rows = tuple(
            cost_row_for_model(
                model_folder,
                scale_input_tokens(
                    medians_by_model[model_folder].input_tokens,
                    user_count,
                    ratio,
                ),
                scale_output_tokens(
                    medians_by_model[model_folder].output_tokens,
                    user_count,
                ),
            )
            for model_folder in MODEL_ORDER
        )
        sections.append(ExperimentCostSection(experiment_number, rows))
    return tuple(sections)


def format_cost_table(rows: tuple[CostRow, ...]) -> str:
    """Render one experiment cost table."""
    header = (
        "| model | estimated tokens in | estimated tokens out | "
        "median estimated cost | low/high estimated cost |"
    )
    divider = "| --- | --- | --- | --- | --- |"
    body = [
        (
            f"| {row.model} | {row.estimated_tokens_in} | {row.estimated_tokens_out} | "
            f"${row.median_cost_usd:.2f} | ${row.low_cost_usd:.2f} / ${row.high_cost_usd:.2f} |"
        )
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def total_rows(sections: tuple[ExperimentCostSection, ...]) -> tuple[CostRow, ...]:
    """Sum token and cost estimates across experiments 1 through 4."""
    totals: dict[str, dict[str, float]] = {
        model: {"in": 0.0, "out": 0.0, "median": 0.0, "low": 0.0, "high": 0.0}
        for model in MODEL_ORDER
    }
    for section in sections:
        for row in section.rows:
            bucket = totals[row.model]
            bucket["in"] += row.estimated_tokens_in
            bucket["out"] += row.estimated_tokens_out
            bucket["median"] += row.median_cost_usd
            bucket["low"] += row.low_cost_usd
            bucket["high"] += row.high_cost_usd
    return tuple(
        CostRow(
            model=model,
            estimated_tokens_in=int(totals[model]["in"]),
            estimated_tokens_out=int(totals[model]["out"]),
            median_cost_usd=round(totals[model]["median"], USD_DECIMALS),
            low_cost_usd=round(totals[model]["low"], USD_DECIMALS),
            high_cost_usd=round(totals[model]["high"], USD_DECIMALS),
        )
        for model in MODEL_ORDER
    )


def build_cost_estimate_markdown(
    sections: tuple[ExperimentCostSection, ...],
) -> str:
    """Render the full COST_ESTIMATE.md body."""
    lines = [
        "# AI simulation responses cost estimate",
        "",
        "## Pricing sources",
        "",
        f"- OpenAI Batch: {PRICING_SOURCE_URL} (input $0.10/M, output $0.625/M)",
        f"- Bedrock on-demand: {BEDROCK_PRICING_SOURCE_URL}",
        "  - Nova Micro: input $0.035/M, output $0.14/M",
        "  - Qwen3 32B: input $0.15/M, output $0.60/M",
        "  - Claude Sonnet 4.6: input $3.00/M, output $15.00/M",
        "",
        "Low/high bounds are 0.5× and 2× the median estimate.",
        "",
    ]
    for section in sections:
        lines.append(f"## Experiment {section.experiment_number}")
        lines.append("")
        lines.append("Estimated cost:")
        lines.append("")
        lines.append(format_cost_table(section.rows))
        lines.append("")
    lines.extend(
        [
            "## Experiment 5",
            "",
            "Estimated cost: 0 (analysis only)",
            "",
            "## Total across experiments",
            "",
            "Estimated cost:",
            "",
            format_cost_table(total_rows(sections)),
            "",
        ]
    )
    return "\n".join(lines)


def load_medians_by_model(
    store: CampaignObjectStore,
    smoke_paths_by_model: dict[str, FeaturePaths],
) -> dict[str, MedianTokens]:
    """Load median smoke tokens for every model or raise when smoke is missing."""
    medians: dict[str, MedianTokens] = {}
    for model_folder in MODEL_ORDER:
        paths = smoke_paths_by_model[model_folder]
        usages = load_token_usage(store, paths)
        medians[model_folder] = median_tokens(usages)
    return medians


def upload_cost_estimate(store: CampaignObjectStore, markdown: str) -> str:
    """Write COST_ESTIMATE.md locally and upload with put_new."""
    body = markdown.encode("utf-8")
    put_new_mirrored(store, COST_ESTIMATE_RELATIVE_PATH, body)
    return s3_uri(OUTPUT_S3_BUCKET, COST_ESTIMATE_RELATIVE_PATH)


def token_usage_records_from_openai(
    usages: list[Any],
) -> list[TokenUsageRecord]:
    """Convert OpenAI RequestUsage rows into TokenUsageRecord."""
    return [
        TokenUsageRecord(
            source_record_id=usage.source_record_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        for usage in usages
    ]


def token_usage_records_from_bedrock(
    usages: list[Any],
) -> list[TokenUsageRecord]:
    """Convert BedrockTokenUsage rows into TokenUsageRecord."""
    return [
        TokenUsageRecord(
            source_record_id=usage.source_record_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        for usage in usages
    ]
