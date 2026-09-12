"""OpenAI Batch runner for remove-index labeling."""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.generate_features.campaign_cost_report import (
    RequestUsage,
    request_usages_from_output_text,
)
from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.engines.openai_engine import (
    build_openai_engine,
    create_openai_client,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask

ATTEMPT_COUNT = 1


@dataclass(frozen=True)
class OpenAILabelResult:
    """Rows, failures, and per-request token usage from one OpenAI batch."""

    rows: list[dict]
    failures: list[RecordLabelFailure]
    request_usages: list[RequestUsage]


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through the OpenAI Batch API."""
    result = label_tasks_with_usage(spec, tasks)
    return result.rows, result.failures


def label_tasks_with_usage(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> OpenAILabelResult:
    """Label tasks and return per-request token usage from the batch output."""
    if not tasks:
        return OpenAILabelResult([], [], [])
    engine = build_openai_engine(spec, FeatureRunConfig())
    try:
        rows = engine.batch_label_records(tasks)
    except Exception as error:
        failures = _failures_for_tasks(tasks, str(error))
        return OpenAILabelResult([], failures, [])
    usages = _request_usages_from_engine(engine, tasks)
    return OpenAILabelResult(rows, [], usages)


def _request_usages_from_engine(
    engine: object,
    tasks: list[LabelTask],
) -> list[RequestUsage]:
    batch = getattr(engine, "last_batch", None)
    if batch is None or batch.output_file_id is None:
        return []
    client = create_openai_client()
    text = client.files.content(batch.output_file_id).text
    return request_usages_from_output_text(text, [task.uri for task in tasks])


def _failures_for_tasks(
    tasks: list[LabelTask],
    error: str,
) -> list[RecordLabelFailure]:
    return [
        RecordLabelFailure(
            source_record_id=task.uri,
            error=error,
            attempts=ATTEMPT_COUNT,
        )
        for task in tasks
    ]
