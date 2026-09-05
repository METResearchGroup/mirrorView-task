"""Tests for OpenAI Batch JSONL request and result helpers."""

from __future__ import annotations

from data_platform.generate_features.engines.openai_batch import (
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
