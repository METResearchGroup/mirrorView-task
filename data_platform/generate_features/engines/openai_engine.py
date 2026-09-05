"""OpenAI Batch API engine for LLM feature labeling."""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from data_platform.generate_features.engines.base import (
    BaseBatchExecutionEngine,
    row_with_label_timestamp,
)
from data_platform.generate_features.engines.openai_batch import (
    OPENAI_BATCH_ENDPOINT,
    OpenAIBatchOutputRecord,
    OpenAIBatchTokenUsage,
    build_batch_request_line,
    custom_id_for_index,
    encode_batch_jsonl,
    llm_fields_from_output_record,
    parse_batch_output_line,
    structured_response_format,
    token_usage_from_output_records,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from lib.constants import DEFAULT_LLM_MODEL
from lib.timestamp_utils import get_current_timestamp

OPENAI_BATCH_COMPLETION_WINDOW = "24h"
OPENAI_BATCH_FILE_PURPOSE = "batch"
OPENAI_BATCH_JSONL_FILENAME = "openai_feature_batch.jsonl"
OPENAI_BATCH_TEMPERATURE = 0.0
POLL_INTERVAL_SECONDS = 5.0
POLL_TIMEOUT_SECONDS = 3600.0
BATCH_COMPLETED_STATUS = "completed"
BATCH_FAILED_STATUSES = frozenset(
    {
        "failed",
        "expired",
        "cancelled",
        "cancelling",
    }
)


class OpenAIBatchClient(Protocol):
    """Subset of the OpenAI SDK client used by the Batch engine."""

    files: Any
    batches: Any


@dataclass(frozen=True)
class OpenAIBatchEngineConfig:
    model: str
    temperature: float
    poll_interval_seconds: float
    poll_timeout_seconds: float
    completion_window: str
    endpoint: str


DEFAULT_OPENAI_BATCH_ENGINE_CONFIG = OpenAIBatchEngineConfig(
    model=DEFAULT_LLM_MODEL,
    temperature=OPENAI_BATCH_TEMPERATURE,
    poll_interval_seconds=POLL_INTERVAL_SECONDS,
    poll_timeout_seconds=POLL_TIMEOUT_SECONDS,
    completion_window=OPENAI_BATCH_COMPLETION_WINDOW,
    endpoint=OPENAI_BATCH_ENDPOINT,
)


class OpenAIBatchEngine(BaseBatchExecutionEngine):
    """Label tasks through the OpenAI Batch API with structured outputs."""

    def __init__(
        self,
        spec: FeatureSpec,
        run_config: FeatureRunConfig,
        client: OpenAIBatchClient,
        engine_config: OpenAIBatchEngineConfig,
        sleep_fn: Callable[[float], None],
        monotonic_fn: Callable[[], float],
    ) -> None:
        super().__init__(spec, run_config)
        _require_llm_feature_spec(spec)
        self._client = client
        self._engine_config = engine_config
        self._sleep_fn = sleep_fn
        self._monotonic_fn = monotonic_fn
        self.last_batch_usage: OpenAIBatchTokenUsage | None = None

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        """Submit tasks as one OpenAI Batch and return validated label rows."""
        if not tasks:
            return []
        output_text = _run_openai_batch(
            self._client,
            self.spec,
            self._engine_config,
            tasks,
            self._sleep_fn,
            self._monotonic_fn,
        )
        records_by_id = _output_records_by_custom_id(output_text)
        ordered_records = [
            _record_for_custom_id(records_by_id, custom_id_for_index(index))
            for index in range(len(tasks))
        ]
        label_timestamp = get_current_timestamp()
        rows = [
            _label_row_for_task(task, record, self.spec, label_timestamp)
            for task, record in zip(tasks, ordered_records, strict=True)
        ]
        self.last_batch_usage = token_usage_from_output_records(ordered_records)
        return rows


def _require_llm_feature_spec(spec: FeatureSpec) -> None:
    if spec.system_prompt is None or spec.llm_output_schema is None:
        raise ValueError(
            f"Feature {spec.name} requires system_prompt and llm_output_schema"
        )


def _request_lines_for_tasks(
    tasks: list[LabelTask],
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
) -> list[dict[str, Any]]:
    _require_llm_feature_spec(spec)
    system_prompt = spec.system_prompt
    output_schema = spec.llm_output_schema
    response_format = structured_response_format(output_schema)
    return [
        build_batch_request_line(
            custom_id_for_index(index),
            task.text,
            system_prompt,
            engine_config.model,
            response_format,
            engine_config.temperature,
        )
        for index, task in enumerate(tasks)
    ]


def _upload_batch_file(client: OpenAIBatchClient, jsonl_bytes: bytes) -> str:
    uploaded = client.files.create(
        file=(OPENAI_BATCH_JSONL_FILENAME, io.BytesIO(jsonl_bytes)),
        purpose=OPENAI_BATCH_FILE_PURPOSE,
    )
    return uploaded.id


def _create_batch(
    client: OpenAIBatchClient,
    input_file_id: str,
    engine_config: OpenAIBatchEngineConfig,
) -> Any:
    return client.batches.create(
        input_file_id=input_file_id,
        endpoint=engine_config.endpoint,
        completion_window=engine_config.completion_window,
    )


def _download_batch_output_text(client: OpenAIBatchClient, batch: Any) -> str:
    output_file_id = batch.output_file_id
    if not output_file_id:
        raise RuntimeError(f"OpenAI Batch {batch.id} completed without output_file_id")
    return client.files.content(output_file_id).text


def _run_openai_batch(
    client: OpenAIBatchClient,
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
    tasks: list[LabelTask],
    sleep_fn: Callable[[float], None],
    monotonic_fn: Callable[[], float],
) -> str:
    jsonl_bytes = encode_batch_jsonl(
        _request_lines_for_tasks(tasks, spec, engine_config)
    )
    created = _create_batch(
        client,
        _upload_batch_file(client, jsonl_bytes),
        engine_config,
    )
    completed = wait_for_completed_batch(
        client,
        created.id,
        engine_config.poll_interval_seconds,
        engine_config.poll_timeout_seconds,
        sleep_fn,
        monotonic_fn,
    )
    return _download_batch_output_text(client, completed)


def _output_records_by_custom_id(
    output_text: str,
) -> dict[str, OpenAIBatchOutputRecord]:
    records = [
        parse_batch_output_line(line)
        for line in output_text.splitlines()
        if line.strip()
    ]
    return {record.custom_id: record for record in records}


def _record_for_custom_id(
    records_by_id: dict[str, OpenAIBatchOutputRecord],
    custom_id: str,
) -> OpenAIBatchOutputRecord:
    record = records_by_id.get(custom_id)
    if record is None:
        raise ValueError(f"OpenAI Batch output is missing {custom_id}")
    return record


def _label_row_for_task(
    task: LabelTask,
    record: OpenAIBatchOutputRecord,
    spec: FeatureSpec,
    label_timestamp: str,
) -> dict:
    _require_llm_feature_spec(spec)
    fields = llm_fields_from_output_record(record, spec.llm_output_schema)
    row = row_with_label_timestamp(
        {"source_record_id": task.uri, **fields},
        label_timestamp=label_timestamp,
    )
    return spec.model.model_validate(row).model_dump()


def create_openai_client() -> OpenAIBatchClient:
    raise NotImplementedError


def build_openai_engine(
    spec: FeatureSpec,
    run_config: FeatureRunConfig,
) -> OpenAIBatchEngine:
    raise NotImplementedError


def _require_batch_not_failed(batch_id: str, status: str) -> None:
    if status in BATCH_FAILED_STATUSES:
        raise RuntimeError(f"OpenAI Batch {batch_id} ended with status {status}")


def wait_for_completed_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    poll_interval_seconds: float,
    poll_timeout_seconds: float,
    sleep_fn: Callable[[float], None],
    monotonic_fn: Callable[[], float],
) -> Any:
    """Poll an OpenAI Batch until it completes, fails, or the timeout expires."""
    deadline = monotonic_fn() + poll_timeout_seconds
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        if status == BATCH_COMPLETED_STATUS:
            return batch
        _require_batch_not_failed(batch_id, status)
        if monotonic_fn() >= deadline:
            raise TimeoutError(
                f"OpenAI Batch {batch_id} did not complete before the poll timeout"
            )
        sleep_fn(poll_interval_seconds)

