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


def parse_batch_output_line(raw_line: str) -> OpenAIBatchOutputRecord:
    raise NotImplementedError


def token_usage_from_output_records(
    records: list[OpenAIBatchOutputRecord],
) -> OpenAIBatchTokenUsage:
    raise NotImplementedError


def llm_fields_from_output_record(
    record: OpenAIBatchOutputRecord,
    output_schema: type[BaseModel],
) -> dict[str, Any]:
    raise NotImplementedError
