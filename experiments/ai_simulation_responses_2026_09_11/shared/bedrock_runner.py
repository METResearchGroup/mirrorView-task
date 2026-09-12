"""Bedrock Converse runner for remove-index labeling."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from data_platform.generate_features.engines.base import (
    RecordLabelFailure,
    row_with_label_timestamp,
)
from data_platform.generate_features.engines.bedrock_campaign import (
    BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
)
from data_platform.generate_features.engines.bedrock_engine import (
    BedrockContentFilterError,
    BedrockTaskOutcome,
    BedrockUsage,
    converse_label,
    create_bedrock_runtime_client,
    label_tasks_collecting_failures,
)
from data_platform.generate_features.models import FeatureSpec, LabelTask
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    BEDROCK_MAX_TOKENS,
)
from lib.timestamp_utils import get_current_timestamp

ATTEMPT_COUNT = 1
MIN_THREAD_WORKERS = 1


@dataclass(frozen=True)
class BedrockTokenUsage:
    """Token counts for one successful Bedrock request."""

    source_record_id: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class BedrockLabelResult:
    """Rows, failures, and per-request token usage from one Bedrock part."""

    rows: list[dict]
    failures: list[RecordLabelFailure]
    request_usages: list[BedrockTokenUsage]


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
    model_id: str,
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through Bedrock Converse without OpenAI fallback."""
    if not tasks:
        return [], []
    outcome = label_tasks_collecting_failures(
        create_bedrock_runtime_client(),
        model_id,
        spec,
        tasks,
        BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
        get_current_timestamp(),
        max_tokens=BEDROCK_MAX_TOKENS,
    )
    failures = [*outcome.content_filter_failures, *outcome.other_failures]
    return outcome.rows, failures


def label_tasks_with_usage(
    spec: FeatureSpec,
    tasks: list[LabelTask],
    model_id: str,
) -> BedrockLabelResult:
    """Label tasks and capture per-request token usage for smoke runs only.

    ``label_tasks_collecting_failures`` discards token usage, so smoke labeling
    uses this path to record usage via ``converse_label`` (the same primitive
    the helper uses). Full labeling should call ``label_tasks`` instead.
    """
    if not tasks:
        return BedrockLabelResult([], [], [])
    client = create_bedrock_runtime_client()
    label_timestamp = get_current_timestamp()
    outcome, usages = _label_collecting_failures_with_usage(
        client,
        model_id,
        spec,
        tasks,
        BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
        label_timestamp,
        BEDROCK_MAX_TOKENS,
    )
    failures = [*outcome.content_filter_failures, *outcome.other_failures]
    return BedrockLabelResult(outcome.rows, failures, usages)


def _label_collecting_failures_with_usage(
    client: object,
    model_id: str,
    spec: FeatureSpec,
    tasks: list[LabelTask],
    max_concurrency: int,
    label_timestamp: str,
    max_tokens: int,
) -> tuple[BedrockTaskOutcome, list[BedrockTokenUsage]]:
    """Mirror ``label_tasks_collecting_failures`` while recording token usage."""
    system_prompt, output_schema = _prompt_and_schema(spec)
    worker_count = max(MIN_THREAD_WORKERS, min(max_concurrency, len(tasks)))
    outcomes = _run_label_pool(
        client,
        model_id,
        spec,
        system_prompt,
        output_schema,
        tasks,
        worker_count,
        label_timestamp,
        max_tokens,
    )
    return _split_outcomes(outcomes)


def _prompt_and_schema(spec: FeatureSpec) -> tuple[str, type[BaseModel]]:
    if spec.system_prompt is None or spec.llm_output_schema is None:
        raise ValueError(
            f"Feature {spec.name} requires system_prompt and llm_output_schema"
        )
    return spec.system_prompt, spec.llm_output_schema


def _run_label_pool(
    client: object,
    model_id: str,
    spec: FeatureSpec,
    system_prompt: str,
    output_schema: type[BaseModel],
    tasks: list[LabelTask],
    worker_count: int,
    label_timestamp: str,
    max_tokens: int,
) -> list[tuple[str, dict | RecordLabelFailure, BedrockUsage | None] | None]:
    outcomes: list[
        tuple[str, dict | RecordLabelFailure, BedrockUsage | None] | None
    ] = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(
                _label_task_or_failure,
                client,
                model_id,
                spec,
                system_prompt,
                output_schema,
                task,
                label_timestamp,
                max_tokens,
            ): index
            for index, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            outcomes[futures[future]] = future.result()
    return outcomes


def _label_task_or_failure(
    client: object,
    model_id: str,
    spec: FeatureSpec,
    system_prompt: str,
    output_schema: type[BaseModel],
    task: LabelTask,
    label_timestamp: str,
    max_tokens: int,
) -> tuple[str, dict | RecordLabelFailure, BedrockUsage | None]:
    try:
        parsed, usage = converse_label(
            client,
            model_id,
            system_prompt,
            output_schema,
            task.text,
            max_tokens,
        )
        row = row_with_label_timestamp(
            {"source_record_id": task.uri, **parsed.model_dump()},
            label_timestamp=label_timestamp,
        )
        return ("row", spec.model.model_validate(row).model_dump(), usage)
    except BedrockContentFilterError as error:
        return ("content_filter", _failure_for_task(task, str(error)), None)
    except Exception as error:
        return ("other", _failure_for_task(task, str(error)), None)


def _split_outcomes(
    outcomes: list[tuple[str, dict | RecordLabelFailure, BedrockUsage | None] | None],
) -> tuple[BedrockTaskOutcome, list[BedrockTokenUsage]]:
    rows: list[dict] = []
    content_filter_failures: list[RecordLabelFailure] = []
    other_failures: list[RecordLabelFailure] = []
    usages: list[BedrockTokenUsage] = []
    for outcome in outcomes:
        if outcome is None:
            raise RuntimeError("Bedrock Converse did not return a result for every task")
        kind, payload, usage = outcome
        if kind == "row":
            rows.append(payload)  # type: ignore[arg-type]
            if usage is not None:
                usages.append(
                    BedrockTokenUsage(
                        source_record_id=str(payload["source_record_id"]),
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                    )
                )
        elif kind == "content_filter":
            content_filter_failures.append(payload)  # type: ignore[arg-type]
        else:
            other_failures.append(payload)  # type: ignore[arg-type]
    return BedrockTaskOutcome(rows, content_filter_failures, other_failures), usages


def _failure_for_task(task: LabelTask, error: str) -> RecordLabelFailure:
    return RecordLabelFailure(
        source_record_id=task.uri,
        error=error,
        attempts=ATTEMPT_COUNT,
    )
