"""OpenAI Batch API engine for LLM feature labeling.

Used by ``build_engine`` when a feature spec sets ``engine_type="openai"``.

Run the smoke test from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_openai_engine.py
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openai.lib._parsing._completions import (
    parse_chat_completion,
    type_to_response_format_param,
)
from openai import APIConnectionError, InternalServerError, RateLimitError
from openai.types import Batch
from openai.types.chat import ChatCompletion
from pydantic import BaseModel

from data_platform.generate_features.engines.base import (
    BaseBatchExecutionEngine,
    RecordLabelFailure,
    row_with_label_timestamp,
)
from data_platform.generate_features.models import (
    FeatureRunConfig,
    FeatureSpec,
    LabelTask,
)
from data_platform.generate_features.openai_batch_state import (
    clear_active_batch_state,
    load_active_batch_state,
    write_active_batch_state,
)
from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer
from lib.timestamp_utils import get_current_timestamp

OPENAI_BATCH_ENDPOINT = "/v1/chat/completions"
OPENAI_BATCH_COMPLETION_WINDOW = "24h"
OPENAI_BATCH_FILE_PURPOSE = "batch"
OPENAI_BATCH_TEMPERATURE = 0.0
POLL_INTERVAL_SECONDS = 5.0
SDK_READ_RETRY_INITIAL_SECONDS = 1.0
SDK_READ_RETRY_MAX_SECONDS = 60.0
CUSTOM_ID_PREFIX = "task-"
CUSTOM_ID_INDEX_WIDTH = 5
BATCH_COMPLETED_STATUS = "completed"
BATCH_FAILED_STATUSES = frozenset(
    {
        "failed",
        "expired",
        "cancelled",
    }
)
TRANSIENT_POLL_ERRORS = (APIConnectionError, InternalServerError, RateLimitError)
logger = logging.getLogger(__name__)


class OpenAIBatchClient(Protocol):
    """Subset of the OpenAI SDK client used by the Batch engine."""

    files: Any
    batches: Any


class OpenAIBatchJobError(RuntimeError):
    """The provider batch ended failed, expired, or cancelled."""


@dataclass(frozen=True)
class BatchRequestFailure:
    """One request in a provider batch that produced no valid label row."""

    source_record_id: str
    custom_id: str
    error: str
    transient: bool
    missing_output: bool


@dataclass(frozen=True)
class ParsedBatchOutput:
    """Rows and failures parsed from one completed provider batch."""

    rows: list[dict]
    failures: list[BatchRequestFailure]


@dataclass(frozen=True)
class OpenAIBatchEngineConfig:
    """Model, sampling, and poll settings for one OpenAI Batch labeling run."""

    model: str
    temperature: float
    poll_interval_seconds: float
    completion_window: str
    endpoint: str


DEFAULT_OPENAI_BATCH_ENGINE_CONFIG = OpenAIBatchEngineConfig(
    model=DEFAULT_LLM_MODEL,
    temperature=OPENAI_BATCH_TEMPERATURE,
    poll_interval_seconds=POLL_INTERVAL_SECONDS,
    completion_window=OPENAI_BATCH_COMPLETION_WINDOW,
    endpoint=OPENAI_BATCH_ENDPOINT,
)


class OpenAIBatchEngine(BaseBatchExecutionEngine):
    """Labels a batch of posts through OpenAI's Batch API with structured output.

    ``last_batch`` is set after a successful ``batch_label_records`` call.
    """

    def __init__(
        self,
        spec: FeatureSpec,
        run_config: FeatureRunConfig,
        client: OpenAIBatchClient,
        engine_config: OpenAIBatchEngineConfig,
        sleep_fn: Callable[[float], None],
    ) -> None:
        super().__init__(spec, run_config)
        _llm_prompt_and_schema(spec)
        self._client = client
        self._engine_config = engine_config
        self._sleep_fn = sleep_fn
        self.last_batch: Batch | None = None

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        """Submit tasks as one OpenAI Batch and return validated label rows."""
        if not tasks:
            return []
        completed_batch = _submit_and_wait_for_batch(
            self._client,
            self.spec,
            self._engine_config,
            tasks,
            self._sleep_fn,
        )
        _raise_for_request_errors(self._client, completed_batch, self._sleep_fn)
        output_lines = _download_output_lines(
            self._client,
            completed_batch,
            self._sleep_fn,
        )
        completions_by_id = _chat_completions_by_custom_id(output_lines)
        label_timestamp = get_current_timestamp()
        rows = [
            _label_row_for_task(
                task,
                _completion_for_index(completions_by_id, index),
                self.spec,
                label_timestamp,
            )
            for index, task in enumerate(tasks)
        ]
        self.last_batch = completed_batch
        return rows

    def label_chunk(
        self,
        tasks: list[LabelTask],
        *,
        feature_name: str,
        run_dir: Path,
        batch_index: int,
        write_rows: Callable[[list[dict]], None],
    ) -> list[RecordLabelFailure]:
        raise NotImplementedError


def submit_active_batch(
    client: OpenAIBatchClient,
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
    tasks: list[LabelTask],
    *,
    run_dir: Path,
    feature_name: str,
    batch_index: int,
    attempt_count: int,
) -> dict[str, Any]:
    raise NotImplementedError


def _parse_completed_batch(
    client: OpenAIBatchClient,
    batch: Batch,
    ordered_ids: list[str],
    tasks_by_id: dict[str, LabelTask],
    spec: FeatureSpec,
    sleep_fn: Callable[[float], None],
) -> ParsedBatchOutput:
    raise NotImplementedError


def _llm_prompt_and_schema(spec: FeatureSpec) -> tuple[str, type[BaseModel]]:
    system_prompt = spec.system_prompt
    output_schema = spec.llm_output_schema
    if system_prompt is None or output_schema is None:
        raise ValueError(
            f"Feature {spec.name} requires system_prompt and llm_output_schema"
        )
    return system_prompt, output_schema


def _custom_id_for_index(index: int) -> str:
    return f"{CUSTOM_ID_PREFIX}{index:0{CUSTOM_ID_INDEX_WIDTH}d}"


def _request_for_task(
    task: LabelTask,
    index: int,
    system_prompt: str,
    response_format: dict[str, Any],
    engine_config: OpenAIBatchEngineConfig,
) -> dict[str, Any]:
    return {
        "custom_id": _custom_id_for_index(index),
        "method": "POST",
        "url": engine_config.endpoint,
        "body": {
            "model": engine_config.model,
            "temperature": engine_config.temperature,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.text},
            ],
        },
    }


def _request_lines_for_tasks(
    tasks: list[LabelTask],
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
) -> list[dict[str, Any]]:
    system_prompt, output_schema = _llm_prompt_and_schema(spec)
    response_format = type_to_response_format_param(output_schema)
    return [
        _request_for_task(
            task,
            index,
            system_prompt,
            response_format,
            engine_config,
        )
        for index, task in enumerate(tasks)
    ]


def _submit_and_wait_for_batch(
    client: OpenAIBatchClient,
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
    tasks: list[LabelTask],
    sleep_fn: Callable[[float], None],
) -> Batch:
    requests = _request_lines_for_tasks(tasks, spec, engine_config)
    input_file_id = _upload_requests(client, requests)
    batch = client.batches.create(
        input_file_id=input_file_id,
        endpoint=engine_config.endpoint,
        completion_window=engine_config.completion_window,
    )
    return wait_for_completed_batch(
        client,
        batch.id,
        engine_config.poll_interval_seconds,
        sleep_fn,
    )


def _upload_requests(
    client: OpenAIBatchClient,
    requests: list[dict[str, Any]],
) -> str:
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".jsonl") as batch_file:
        for request in requests:
            batch_file.write(f"{json.dumps(request)}\n".encode())
        batch_file.flush()
        batch_file.seek(0)
        return client.files.create(
            file=batch_file.file,
            purpose=OPENAI_BATCH_FILE_PURPOSE,
        ).id


def _download_output_lines(
    client: OpenAIBatchClient,
    batch: Batch,
    sleep_fn: Callable[[float], None],
) -> list[str]:
    if batch.output_file_id is None:
        raise RuntimeError(f"OpenAI Batch {batch.id} completed without output_file_id")
    return _download_file_text(
        client,
        batch.output_file_id,
        sleep_fn,
    ).splitlines()


def _raise_for_request_errors(
    client: OpenAIBatchClient,
    batch: Batch,
    sleep_fn: Callable[[float], None],
) -> None:
    if batch.error_file_id is None:
        return
    error_text = _download_file_text(client, batch.error_file_id, sleep_fn)
    errors = [json.loads(line) for line in error_text.splitlines() if line.strip()]
    summaries = [
        f"{error.get('custom_id', 'unknown')}: {error.get('error', {})}"
        for error in errors
    ]
    raise RuntimeError(f"OpenAI Batch request failures: {'; '.join(summaries)}")


def _download_file_text(
    client: OpenAIBatchClient,
    file_id: str,
    sleep_fn: Callable[[float], None],
) -> str:
    retry_delay = SDK_READ_RETRY_INITIAL_SECONDS
    while True:
        try:
            return client.files.content(file_id).text
        except TRANSIENT_POLL_ERRORS as error:
            logger.warning(
                "OpenAI Batch file download failed; retrying existing file",
                extra={"file_id": file_id, "retry_delay_seconds": retry_delay},
                exc_info=error,
            )
            sleep_fn(retry_delay)
            retry_delay = min(retry_delay * 2, SDK_READ_RETRY_MAX_SECONDS)


def _chat_completions_by_custom_id(
    output_lines: list[str],
) -> dict[str, ChatCompletion]:
    completions: dict[str, ChatCompletion] = {}
    for line in output_lines:
        payload = json.loads(line)
        response = payload.get("response")
        if response is None:
            raise ValueError(f"OpenAI Batch request {payload['custom_id']} failed")
        completions[payload["custom_id"]] = ChatCompletion.model_validate(
            response["body"]
        )
    return completions


def _completion_for_index(
    completions_by_id: dict[str, ChatCompletion],
    index: int,
) -> ChatCompletion:
    custom_id = _custom_id_for_index(index)
    completion = completions_by_id.get(custom_id)
    if completion is None:
        raise ValueError(f"OpenAI Batch output is missing {custom_id}")
    return completion


def _label_row_for_task(
    task: LabelTask,
    completion: ChatCompletion,
    spec: FeatureSpec,
    label_timestamp: str,
) -> dict:
    _, output_schema = _llm_prompt_and_schema(spec)
    parsed_completion = parse_chat_completion(
        response_format=output_schema,
        input_tools=[],
        chat_completion=completion,
    )
    parsed = parsed_completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError(f"OpenAI did not return structured output for {task.uri}")
    row = row_with_label_timestamp(
        {"source_record_id": task.uri, **parsed.model_dump()},
        label_timestamp=label_timestamp,
    )
    return spec.model.model_validate(row).model_dump()


def create_openai_client() -> OpenAIBatchClient:
    """Build an OpenAI SDK client using OPENAI_API_KEY."""
    from openai import OpenAI

    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return OpenAI(api_key=api_key)


def build_openai_engine(
    spec: FeatureSpec,
    run_config: FeatureRunConfig,
) -> OpenAIBatchEngine:
    """Construct the OpenAI Batch engine with the default SDK client and clock."""
    return OpenAIBatchEngine(
        spec,
        run_config,
        create_openai_client(),
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        time.sleep,
    )


def _require_batch_not_failed(batch_id: str, status: str) -> None:
    if status in BATCH_FAILED_STATUSES:
        raise RuntimeError(f"OpenAI Batch {batch_id} ended with status {status}")


def _retrieve_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    sleep_fn: Callable[[float], None],
) -> Batch:
    retry_delay = SDK_READ_RETRY_INITIAL_SECONDS
    while True:
        try:
            return client.batches.retrieve(batch_id)
        except TRANSIENT_POLL_ERRORS as error:
            logger.warning(
                "OpenAI Batch status check failed; retrying existing batch",
                extra={"batch_id": batch_id, "retry_delay_seconds": retry_delay},
                exc_info=error,
            )
            sleep_fn(retry_delay)
            retry_delay = min(retry_delay * 2, SDK_READ_RETRY_MAX_SECONDS)


def wait_for_completed_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    poll_interval_seconds: float,
    sleep_fn: Callable[[float], None],
) -> Batch:
    """Poll an OpenAI Batch until OpenAI reports a terminal status.

    Raises
    ------
    RuntimeError
        When the batch ends in a failed, expired, or cancelled status.
    """
    while True:
        batch = _retrieve_batch(client, batch_id, sleep_fn)
        status = batch.status
        if status == BATCH_COMPLETED_STATUS:
            return batch
        _require_batch_not_failed(batch_id, status)
        sleep_fn(poll_interval_seconds)

