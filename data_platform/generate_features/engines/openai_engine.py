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
from openai import (
    APIConnectionError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)
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
BATCH_FAILED_STATUS = "failed"
BATCH_EXPIRED_STATUS = "expired"
BATCH_CANCELLED_STATUS = "cancelled"
BATCH_FAILED_STATUSES = frozenset(
    {
        BATCH_FAILED_STATUS,
        BATCH_EXPIRED_STATUS,
        BATCH_CANCELLED_STATUS,
    }
)
BATCH_TERMINAL_STATUSES = frozenset({BATCH_COMPLETED_STATUS, *BATCH_FAILED_STATUSES})
# An expired batch still carries output for the requests that did finish.
BATCH_STATUSES_WITH_OUTPUT = frozenset({BATCH_COMPLETED_STATUS, BATCH_EXPIRED_STATUS})
# Batch level error codes that clear on their own, so the same requests may be resubmitted.
TRANSIENT_BATCH_ERROR_CODES = frozenset({"token_limit_exceeded"})
TRANSIENT_POLL_ERRORS = (APIConnectionError, InternalServerError, RateLimitError)
HTTP_OK = 200
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR_MIN = 500
HTTP_SERVER_ERROR_MAX = 599
TRANSIENT_HTTP_STATUS_CODES = frozenset(
    {HTTP_TOO_MANY_REQUESTS, *range(HTTP_SERVER_ERROR_MIN, HTTP_SERVER_ERROR_MAX + 1)}
)
ACTIVE_STATE_POLLING = "polling"
ACTIVE_STATE_WRITING = "writing"
ACTIVE_STATE_TERMINAL = "terminal"
logger = logging.getLogger(__name__)


class OpenAIBatchClient(Protocol):
    """Subset of the OpenAI SDK client used by the Batch engine."""

    files: Any
    batches: Any


class OpenAIBatchJobError(RuntimeError):
    """The provider batch ended failed, expired, or cancelled.

    ``transient`` is True when resubmitting the same requests can succeed,
    which is the case for an expired batch and for a batch that failed only
    on the enqueued token limit.
    """

    def __init__(self, message: str, *, transient: bool) -> None:
        super().__init__(message)
        self.transient = transient


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
        ordered_ids = [task.uri for task in tasks]
        tasks_by_id = {task.uri: task for task in tasks}
        error_payloads = _download_payloads(
            self._client, completed_batch.error_file_id, self._sleep_fn
        )
        if error_payloads:
            parsed_errors = _parse_batch_payloads(
                error_payloads, ordered_ids, tasks_by_id, self.spec
            )
            _raise_for_failures(
                [failure for failure in parsed_errors.failures if not failure.missing_output]
            )
        output_payloads = _download_payloads(
            self._client, completed_batch.output_file_id, self._sleep_fn
        )
        parsed = _parse_batch_payloads(output_payloads, ordered_ids, tasks_by_id, self.spec)
        _raise_for_failures(parsed.failures)
        self.last_batch = completed_batch
        return parsed.rows

    def label_chunk(
        self,
        tasks: list[LabelTask],
        *,
        feature_name: str,
        run_dir: Path,
        batch_index: int,
        write_rows: Callable[[list[dict]], None],
    ) -> list[RecordLabelFailure]:
        """Label one chunk through provider jobs that survive a process crash.

        Reattaches to the job in the feature's state file when one is still
        ``polling`` or ``writing`` for this ``batch_index``. Writes every
        successful row as soon as its provider job completes, then submits one
        retry job at a time for ids that failed transiently and still have
        attempts left. Returns the records that ended without a valid row.
        """
        attempt_budget = self.run_config.max_label_retries + 1
        remaining = {task.uri: task for task in tasks}
        attempts = {task.uri: 0 for task in tasks}
        failures: list[RecordLabelFailure] = []
        job_count = 0
        while remaining:
            job_count += 1
            if job_count > 1:
                self._sleep_fn(_retry_job_delay_seconds(job_count))
            state, parsed = self._run_one_job(
                remaining,
                feature_name=feature_name,
                run_dir=run_dir,
                batch_index=batch_index,
                attempt_count=job_count,
            )
            write_rows(parsed.rows)
            for row in parsed.rows:
                remaining.pop(row["source_record_id"], None)
            for failure in parsed.failures:
                attempts[failure.source_record_id] += 1
                if failure.transient and attempts[failure.source_record_id] < attempt_budget:
                    continue
                failures.append(
                    RecordLabelFailure(
                        source_record_id=failure.source_record_id,
                        error=failure.error,
                        attempts=attempts[failure.source_record_id],
                    )
                )
                remaining.pop(failure.source_record_id)
            if state is not None:
                write_active_batch_state(
                    run_dir, feature_name, {**state, "state": ACTIVE_STATE_TERMINAL}
                )
        clear_active_batch_state(run_dir, feature_name)
        return failures

    def _run_one_job(
        self,
        remaining: dict[str, LabelTask],
        *,
        feature_name: str,
        run_dir: Path,
        batch_index: int,
        attempt_count: int,
    ) -> tuple[dict[str, Any] | None, ParsedBatchOutput]:
        """Reattach to or submit one provider job and parse its results.

        Any exception from submit or poll becomes one failure per task in the
        job, so the caller applies the same per record attempt accounting to
        whole job failures and to per request failures.
        """
        state = _matching_active_state(
            load_active_batch_state(run_dir, feature_name),
            feature_name,
            batch_index,
            remaining,
        )
        if state is None:
            job_tasks = list(remaining.values())
        else:
            logger.info(
                "Reattaching to in-flight OpenAI Batch",
                extra={"batch_id": state["batch_id"], "feature_name": feature_name},
            )
            job_tasks = [
                remaining[uri] for uri in state["pending_source_record_ids"] if uri in remaining
            ]
        tasks_by_id = {task.uri: task for task in job_tasks}
        try:
            if state is None:
                state = submit_active_batch(
                    self._client,
                    self.spec,
                    self._engine_config,
                    job_tasks,
                    run_dir=run_dir,
                    feature_name=feature_name,
                    batch_index=batch_index,
                    attempt_count=attempt_count,
                )
            terminal = wait_for_terminal_batch(
                self._client,
                state["batch_id"],
                self._engine_config.poll_interval_seconds,
                self._sleep_fn,
            )
            if terminal.status not in BATCH_STATUSES_WITH_OUTPUT:
                raise _batch_job_error(terminal)
        except Exception as error:
            logger.warning(
                "OpenAI Batch job failed for every request in the job",
                extra={"feature_name": feature_name, "batch_index": batch_index},
                exc_info=error,
            )
            return state, ParsedBatchOutput(
                rows=[],
                failures=[_job_failure(uri, error) for uri in tasks_by_id],
            )
        state = {**state, "state": ACTIVE_STATE_WRITING}
        write_active_batch_state(run_dir, feature_name, state)
        self.last_batch = terminal
        parsed = _parse_completed_batch(
            self._client,
            terminal,
            state["pending_source_record_ids"],
            tasks_by_id,
            self.spec,
            self._sleep_fn,
        )
        return state, parsed


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
    """Upload requests, create the provider batch, and save ``polling`` state.

    The returned dict is the saved state. It is on disk before this function
    returns, so a caller that polls afterwards can be resumed by a new process.
    """
    submitted = _submit_batch(client, spec, engine_config, tasks)
    state = {
        "input_file_id": submitted.input_file_id,
        "batch_id": submitted.batch_id,
        "logical_batch_index": batch_index,
        "pending_source_record_ids": [task.uri for task in tasks],
        "attempt_count": attempt_count,
        "state": ACTIVE_STATE_POLLING,
        "campaign_id": None,
        "feature_name": feature_name,
        "submitted_at": get_current_timestamp(),
    }
    write_active_batch_state(run_dir, feature_name, state)
    return state


def _matching_active_state(
    state: dict[str, Any] | None,
    feature_name: str,
    batch_index: int,
    remaining: dict[str, LabelTask],
) -> dict[str, Any] | None:
    """Return the saved state when it describes an unfinished job for this chunk."""
    if state is None:
        return None
    if state["feature_name"] != feature_name or state["logical_batch_index"] != batch_index:
        return None
    if state["state"] not in (ACTIVE_STATE_POLLING, ACTIVE_STATE_WRITING):
        return None
    if not any(uri in remaining for uri in state["pending_source_record_ids"]):
        return None
    return state


def _job_failure(source_record_id: str, error: Exception) -> BatchRequestFailure:
    """Describe a whole job failure for one record.

    Transport errors, provider 5xx and 429 errors, and batch level errors
    that clear on their own are transient. Everything else fails fast.
    """
    if isinstance(error, OpenAIBatchJobError):
        transient = error.transient
    else:
        transient = isinstance(error, TRANSIENT_POLL_ERRORS)
    return BatchRequestFailure(
        source_record_id=source_record_id,
        custom_id="",
        error=f"{type(error).__name__}: {error}",
        transient=transient,
        missing_output=False,
    )


def _retry_job_delay_seconds(job_count: int) -> float:
    return min(
        SDK_READ_RETRY_INITIAL_SECONDS * 2 ** (job_count - 2),
        SDK_READ_RETRY_MAX_SECONDS,
    )


def _parse_completed_batch(
    client: OpenAIBatchClient,
    batch: Batch,
    ordered_ids: list[str],
    tasks_by_id: dict[str, LabelTask],
    spec: FeatureSpec,
    sleep_fn: Callable[[float], None],
) -> ParsedBatchOutput:
    """Split a completed batch into validated rows and per request failures.

    ``ordered_ids`` gives the id for each ``task-NNNNN`` custom id. Only ids
    that are keys of ``tasks_by_id`` are classified; the rest are ignored.
    """
    payloads = _download_payloads(client, batch.error_file_id, sleep_fn)
    payloads.update(_download_payloads(client, batch.output_file_id, sleep_fn))
    return _parse_batch_payloads(payloads, ordered_ids, tasks_by_id, spec)


def _parse_batch_payloads(
    payloads: dict[str, dict[str, Any]],
    ordered_ids: list[str],
    tasks_by_id: dict[str, LabelTask],
    spec: FeatureSpec,
) -> ParsedBatchOutput:
    """Classify each wanted id as a validated row or a request failure.

    An id with no payload is a transient ``missing_output`` failure. A payload
    without an HTTP 200 body is a failure that is transient only for HTTP 429
    and 5xx. A payload whose body does not parse into a valid row is a
    non transient failure.
    """
    label_timestamp = get_current_timestamp()
    rows: list[dict] = []
    failures: list[BatchRequestFailure] = []
    for index, source_record_id in enumerate(ordered_ids):
        task = tasks_by_id.get(source_record_id)
        if task is None:
            continue
        custom_id = _custom_id_for_index(index)
        payload = payloads.get(custom_id)
        if payload is None:
            failures.append(
                BatchRequestFailure(
                    source_record_id=source_record_id,
                    custom_id=custom_id,
                    error="missing from the batch output and error files",
                    transient=True,
                    missing_output=True,
                )
            )
            continue
        failure = _failure_for_payload(payload, source_record_id, custom_id)
        if failure is not None:
            failures.append(failure)
            continue
        try:
            completion = ChatCompletion.model_validate(payload["response"]["body"])
            rows.append(_label_row_for_task(task, completion, spec, label_timestamp))
        except (ValueError, OpenAIError) as error:
            failures.append(
                BatchRequestFailure(
                    source_record_id=source_record_id,
                    custom_id=custom_id,
                    error=f"{type(error).__name__}: {error}",
                    transient=False,
                    missing_output=False,
                )
            )
    return ParsedBatchOutput(rows=rows, failures=failures)


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


@dataclass(frozen=True)
class SubmittedBatch:
    """Provider ids returned by one upload and ``batches.create`` pair."""

    input_file_id: str
    batch_id: str


def _submit_batch(
    client: OpenAIBatchClient,
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
    tasks: list[LabelTask],
) -> SubmittedBatch:
    requests = _request_lines_for_tasks(tasks, spec, engine_config)
    input_file_id = _upload_requests(client, requests)
    batch = client.batches.create(
        input_file_id=input_file_id,
        endpoint=engine_config.endpoint,
        completion_window=engine_config.completion_window,
    )
    return SubmittedBatch(input_file_id=input_file_id, batch_id=batch.id)


def _submit_and_wait_for_batch(
    client: OpenAIBatchClient,
    spec: FeatureSpec,
    engine_config: OpenAIBatchEngineConfig,
    tasks: list[LabelTask],
    sleep_fn: Callable[[float], None],
) -> Batch:
    submitted = _submit_batch(client, spec, engine_config, tasks)
    return wait_for_completed_batch(
        client,
        submitted.batch_id,
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


def _download_payloads(
    client: OpenAIBatchClient,
    file_id: str | None,
    sleep_fn: Callable[[float], None],
) -> dict[str, dict[str, Any]]:
    """Return the JSON lines of a batch output or error file keyed by custom id."""
    if file_id is None:
        return {}
    text = _download_file_text(client, file_id, sleep_fn)
    payloads: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        if line.strip():
            payload = json.loads(line)
            payloads[payload["custom_id"]] = payload
    return payloads


def _failure_for_payload(
    payload: dict[str, Any],
    source_record_id: str,
    custom_id: str,
) -> BatchRequestFailure | None:
    """Return the request failure described by a batch line, or None for a success."""
    response = payload.get("response") or {}
    status_code = response.get("status_code")
    if status_code == HTTP_OK and response.get("body"):
        return None
    error = payload.get("error") or (response.get("body") or {}).get("error") or {}
    message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
    prefix = "" if status_code is None else f"HTTP {status_code}: "
    return BatchRequestFailure(
        source_record_id=source_record_id,
        custom_id=custom_id,
        error=f"{prefix}{message}",
        transient=status_code in TRANSIENT_HTTP_STATUS_CODES,
        missing_output=False,
    )


def _raise_for_failures(failures: list[BatchRequestFailure]) -> None:
    """Keep the strict all-or-nothing contract of ``batch_label_records``.

    Raises
    ------
    ValueError
        When a request is missing from both the output and the error file.
    RuntimeError
        When a request failed or its output could not become a valid row.
    """
    if not failures:
        return
    summary = "; ".join(f"{failure.custom_id}: {failure.error}" for failure in failures)
    if any(failure.missing_output for failure in failures):
        raise ValueError(f"OpenAI Batch output is missing requests: {summary}")
    raise RuntimeError(f"OpenAI Batch request failures: {summary}")


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


def _batch_job_error(batch: Batch) -> OpenAIBatchJobError:
    """Describe a batch that ended failed, expired, or cancelled."""
    errors = list(getattr(batch.errors, "data", None) or [])
    codes = [error.code for error in errors]
    if batch.status == BATCH_FAILED_STATUS:
        transient = all(code in TRANSIENT_BATCH_ERROR_CODES for code in codes)
    else:
        transient = batch.status == BATCH_EXPIRED_STATUS
    detail = "; ".join(f"{error.code}: {error.message}" for error in errors)
    suffix = f" ({detail})" if detail else ""
    return OpenAIBatchJobError(
        f"OpenAI Batch {batch.id} ended with status {batch.status}{suffix}",
        transient=transient,
    )


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
    """Poll an OpenAI Batch until it completes.

    Raises
    ------
    OpenAIBatchJobError
        When the batch ends in a failed, expired, or cancelled status.
    """
    batch = wait_for_terminal_batch(client, batch_id, poll_interval_seconds, sleep_fn)
    if batch.status != BATCH_COMPLETED_STATUS:
        raise _batch_job_error(batch)
    return batch


def wait_for_terminal_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    poll_interval_seconds: float,
    sleep_fn: Callable[[float], None],
) -> Batch:
    """Poll an OpenAI Batch until OpenAI reports any terminal status."""
    while True:
        batch = _retrieve_batch(client, batch_id, sleep_fn)
        if batch.status in BATCH_TERMINAL_STATUSES:
            return batch
        sleep_fn(poll_interval_seconds)

