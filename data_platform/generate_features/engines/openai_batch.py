"""JSONL request and result helpers for the OpenAI Batch feature engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai.lib._parsing._completions import type_to_response_format_param
from pydantic import BaseModel

OPENAI_BATCH_HTTP_METHOD = "POST"
OPENAI_BATCH_ENDPOINT = "/v1/chat/completions"
CUSTOM_ID_PREFIX = "task-"
CUSTOM_ID_INDEX_WIDTH = 5
HTTP_OK_STATUS_CODE = 200
JSONL_LINE_SEPARATOR = "\n"
SYSTEM_MESSAGE_ROLE = "system"
USER_MESSAGE_ROLE = "user"
PROMPT_TOKENS_FIELD = "prompt_tokens"
COMPLETION_TOKENS_FIELD = "completion_tokens"
MISSING_TOKEN_COUNT = 0
FIRST_CHOICE_INDEX = 0


@dataclass(frozen=True)
class OpenAIBatchTokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_count: int


@dataclass(frozen=True)
class OpenAIBatchOutputRecord:
    custom_id: str
    status_code: int | None
    content: str | None
    prompt_tokens: int
    completion_tokens: int
    error: str | None


def custom_id_for_index(index: int) -> str:
    """Return a short unique custom_id for one row in a Batch JSONL file."""
    return f"{CUSTOM_ID_PREFIX}{index:0{CUSTOM_ID_INDEX_WIDTH}d}"


def structured_response_format(output_schema: type[BaseModel]) -> dict[str, Any]:
    """Return the OpenAI strict JSON schema wrapper for a Pydantic model."""
    return type_to_response_format_param(output_schema)


def build_batch_request_line(
    custom_id: str,
    text: str,
    system_prompt: str,
    model: str,
    response_format: dict[str, Any],
    temperature: float,
) -> dict[str, Any]:
    """Build one Chat Completions Batch JSONL request object."""
    return {
        "custom_id": custom_id,
        "method": OPENAI_BATCH_HTTP_METHOD,
        "url": OPENAI_BATCH_ENDPOINT,
        "body": {
            "model": model,
            "temperature": temperature,
            "response_format": response_format,
            "messages": [
                {"role": SYSTEM_MESSAGE_ROLE, "content": system_prompt},
                {"role": USER_MESSAGE_ROLE, "content": text},
            ],
        },
    }


def encode_batch_jsonl(request_lines: list[dict[str, Any]]) -> bytes:
    """Serialize Batch request objects as UTF-8 JSONL bytes."""
    payload = JSONL_LINE_SEPARATOR.join(json.dumps(line) for line in request_lines)
    return f"{payload}{JSONL_LINE_SEPARATOR}".encode("utf-8")


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _error_message(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if error is None:
        return None
    if isinstance(error, dict):
        return str(error.get("message", error))
    return str(error)


def _message_content(body: dict[str, Any]) -> str | None:
    choices = body.get("choices") or []
    if not choices:
        return None
    message = _mapping_or_empty(choices[FIRST_CHOICE_INDEX]).get("message")
    content = _mapping_or_empty(message).get("content")
    return content if isinstance(content, str) else None


def _token_count(usage: dict[str, Any], field_name: str) -> int:
    return int(usage.get(field_name, MISSING_TOKEN_COUNT) or MISSING_TOKEN_COUNT)


def parse_batch_output_line(raw_line: str) -> OpenAIBatchOutputRecord:
    """Parse one Batch output JSONL line into a typed result record."""
    payload = json.loads(raw_line)
    response = _mapping_or_empty(payload.get("response"))
    body = _mapping_or_empty(response.get("body"))
    usage = _mapping_or_empty(body.get("usage"))
    return OpenAIBatchOutputRecord(
        custom_id=str(payload["custom_id"]),
        status_code=response.get("status_code"),
        content=_message_content(body),
        prompt_tokens=_token_count(usage, PROMPT_TOKENS_FIELD),
        completion_tokens=_token_count(usage, COMPLETION_TOKENS_FIELD),
        error=_error_message(payload),
    )


def token_usage_from_output_records(
    records: list[OpenAIBatchOutputRecord],
) -> OpenAIBatchTokenUsage:
    """Sum prompt and completion tokens across Batch output records."""
    prompt_tokens = sum(record.prompt_tokens for record in records)
    completion_tokens = sum(record.completion_tokens for record in records)
    return OpenAIBatchTokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        request_count=len(records),
    )


def llm_fields_from_output_record(
    record: OpenAIBatchOutputRecord,
    output_schema: type[BaseModel],
) -> dict[str, Any]:
    """Validate structured JSON content against the feature output schema."""
    if record.content is None:
        raise ValueError(
            f"OpenAI Batch request {record.custom_id} has no structured content"
        )
    parsed = output_schema.model_validate_json(record.content)
    return parsed.model_dump()

