"""Bedrock Converse engine for LLM feature labeling.

Used by ``build_engine`` when a feature spec sets ``engine_type="bedrock"``.

Run the smoke test from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_bedrock_engine.py
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Protocol

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, ValidationError

from data_platform.generate_features.engines.base import (
    BaseBatchExecutionEngine,
    row_with_label_timestamp,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from lib.constants import BEDROCK_REGION, DEFAULT_BEDROCK_NOVA_MICRO
from lib.timestamp_utils import get_current_timestamp

BEDROCK_MAX_TOKENS = 32
BEDROCK_TEMPERATURE = 0.0
BEDROCK_JSON_INSTRUCTION = (
    "Reply with a single JSON object only. "
    "The object must have one string field named category "
    "whose value is news, opinion, or neither."
)
JSON_FENCE = "```"
JSON_FENCE_LANGUAGE = "json"
MIN_THREAD_WORKERS = 1
CONVERSE_RETRY_ATTEMPTS = 8
CONVERSE_RETRY_SLEEP_SECONDS = 1.0
NEWS_OPINION_CATEGORIES = frozenset({"news", "opinion", "neither"})
RETRYABLE_CONVERSE_ERRORS = (
    json.JSONDecodeError,
    ValueError,
    ValidationError,
    ClientError,
)


class BedrockRuntimeClient(Protocol):
    """Subset of the Bedrock Runtime client used by the Converse engine."""

    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class BedrockUsage:
    """Token counts from one or more Converse calls."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class BedrockConverseEngine(BaseBatchExecutionEngine):
    """Labels a batch of posts through Amazon Nova Micro Converse.

    ``last_usage`` is set after a successful ``batch_label_records`` call.
    """

    def __init__(
        self,
        spec: FeatureSpec,
        run_config: FeatureRunConfig,
        client: BedrockRuntimeClient,
        model_id: str,
    ) -> None:
        super().__init__(spec, run_config)
        _llm_prompt_and_schema(spec)
        self._client = client
        self._model_id = model_id
        self.last_usage: BedrockUsage | None = None

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        """Label tasks through Converse and return validated label rows."""
        if not tasks:
            self.last_usage = BedrockUsage(0, 0, 0)
            return []
        label_timestamp = get_current_timestamp()
        parsed_rows, usages = _label_tasks_in_order(
            self._client,
            self._model_id,
            self.spec,
            tasks,
            self.run_config.max_concurrency,
        )
        self.last_usage = _sum_usages(usages)
        return [
            _label_row_for_task(task, parsed, self.spec, label_timestamp)
            for task, parsed in zip(tasks, parsed_rows, strict=True)
        ]


def _llm_prompt_and_schema(spec: FeatureSpec) -> tuple[str, type[BaseModel]]:
    system_prompt = spec.system_prompt
    output_schema = spec.llm_output_schema
    if system_prompt is None or output_schema is None:
        raise ValueError(
            f"Feature {spec.name} requires system_prompt and llm_output_schema"
        )
    return system_prompt, output_schema


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text, ignoring optional markdown fences.

    A bare news, opinion, or neither word is accepted when JSON is missing.
    """
    stripped = text.strip()
    if stripped.startswith(JSON_FENCE):
        stripped = _strip_markdown_fence(stripped)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as error:
        payload = _payload_from_loose_text(stripped)
        if payload is None:
            raise ValueError(f"Bedrock response was not JSON: {stripped!r}") from error
    if not isinstance(payload, dict):
        raise ValueError("Bedrock response JSON must be an object")
    return payload


def _payload_from_loose_text(text: str) -> dict[str, Any] | None:
    lowered = text.strip().strip('"').lower()
    if lowered in NEWS_OPINION_CATEGORIES:
        return {"category": lowered}
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload
    return None


def _strip_markdown_fence(text: str) -> str:
    body = text.strip().removeprefix(JSON_FENCE).strip()
    if body.lower().startswith(JSON_FENCE_LANGUAGE):
        body = body[len(JSON_FENCE_LANGUAGE) :].strip()
    if body.endswith(JSON_FENCE):
        body = body[: -len(JSON_FENCE)].strip()
    return body


def converse_label(
    client: BedrockRuntimeClient,
    model_id: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    user_text: str,
) -> tuple[BaseModel, BedrockUsage]:
    """Return structured output and token usage from one Converse call.

    Empty or invalid JSON is retried a small number of times.
    """
    last_error: Exception | None = None
    for attempt in range(CONVERSE_RETRY_ATTEMPTS):
        try:
            return _converse_once(
                client, model_id, system_prompt, output_schema, user_text
            )
        except RETRYABLE_CONVERSE_ERRORS as error:
            last_error = error
            print(
                f"Bedrock Converse retry {attempt + 1}/{CONVERSE_RETRY_ATTEMPTS}: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            if attempt + 1 >= CONVERSE_RETRY_ATTEMPTS:
                break
            time.sleep(CONVERSE_RETRY_SLEEP_SECONDS)
    if last_error is None:
        raise RuntimeError("Converse retry loop exited without a result")
    raise last_error


def _converse_once(
    client: BedrockRuntimeClient,
    model_id: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    user_text: str,
) -> tuple[BaseModel, BedrockUsage]:
    response = client.converse(
        modelId=model_id,
        system=[{"text": f"{system_prompt}\n{BEDROCK_JSON_INSTRUCTION}"}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig={
            "maxTokens": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
        },
    )
    text = _first_text_block(response)
    parsed = output_schema.model_validate(parse_json_object(text))
    return parsed, _usage_from_response(response)


def _first_text_block(response: dict[str, Any]) -> str:
    content = response["output"]["message"]["content"]
    for block in content:
        text = block.get("text")
        if text:
            return str(text)
    stop_reason = response.get("stopReason", "")
    raise ValueError(
        "Bedrock Converse response had no text "
        f"(stopReason={stop_reason!r}, content={content!r})"
    )


def _usage_from_response(response: dict[str, Any]) -> BedrockUsage:
    usage = response.get("usage", {})
    input_tokens = int(usage.get("inputTokens", 0))
    output_tokens = int(usage.get("outputTokens", 0))
    return BedrockUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def _sum_usages(usages: list[BedrockUsage]) -> BedrockUsage:
    input_tokens = sum(usage.input_tokens for usage in usages)
    output_tokens = sum(usage.output_tokens for usage in usages)
    return BedrockUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def _label_tasks_in_order(
    client: BedrockRuntimeClient,
    model_id: str,
    spec: FeatureSpec,
    tasks: list[LabelTask],
    max_concurrency: int,
) -> tuple[list[BaseModel], list[BedrockUsage]]:
    system_prompt, output_schema = _llm_prompt_and_schema(spec)
    worker_count = max(MIN_THREAD_WORKERS, min(max_concurrency, len(tasks)))
    parsed_rows: list[BaseModel | None] = [None] * len(tasks)
    usages: list[BedrockUsage | None] = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(
                converse_label,
                client,
                model_id,
                system_prompt,
                output_schema,
                task.text,
            ): index
            for index, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            index = futures[future]
            parsed, usage = future.result()
            parsed_rows[index] = parsed
            usages[index] = usage
    if any(row is None or usage is None for row, usage in zip(parsed_rows, usages, strict=True)):
        raise RuntimeError("Bedrock Converse did not return a result for every task")
    return (
        [row for row in parsed_rows if row is not None],
        [usage for usage in usages if usage is not None],
    )


def _label_row_for_task(
    task: LabelTask,
    parsed: BaseModel,
    spec: FeatureSpec,
    label_timestamp: str,
) -> dict:
    row = row_with_label_timestamp(
        {"source_record_id": task.uri, **parsed.model_dump()},
        label_timestamp=label_timestamp,
    )
    return spec.model.model_validate(row).model_dump()


def create_bedrock_runtime_client() -> BedrockRuntimeClient:
    """Build a Bedrock Runtime client in BEDROCK_REGION."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        lab_access = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if lab_access:
            os.environ["AWS_ACCESS_KEY_ID"] = lab_access
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        lab_secret = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if lab_secret:
            os.environ["AWS_SECRET_ACCESS_KEY"] = lab_secret
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def build_bedrock_engine(
    spec: FeatureSpec,
    run_config: FeatureRunConfig,
) -> BedrockConverseEngine:
    """Construct the Bedrock Converse engine with the default client and model."""
    return BedrockConverseEngine(
        spec,
        run_config,
        create_bedrock_runtime_client(),
        DEFAULT_BEDROCK_NOVA_MICRO,
    )
