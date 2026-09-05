"""JSONL request and result helpers for the OpenAI Batch feature engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def custom_id_for_index(index: int) -> str:
    raise NotImplementedError


def structured_response_format(output_schema: type[BaseModel]) -> dict[str, Any]:
    raise NotImplementedError


def build_batch_request_line(
    custom_id: str,
    text: str,
    system_prompt: str,
    model: str,
    response_format: dict[str, Any],
    temperature: float,
) -> dict[str, Any]:
    raise NotImplementedError


def encode_batch_jsonl(request_lines: list[dict[str, Any]]) -> bytes:
    raise NotImplementedError


def parse_batch_output_line(raw_line: str) -> Any:
    raise NotImplementedError


def token_usage_from_output_records(records: list[Any]) -> Any:
    raise NotImplementedError


def llm_fields_from_output_record(
    record: Any,
    output_schema: type[BaseModel],
) -> dict[str, Any]:
    raise NotImplementedError
