"""Tests for OpenAI Batch JSONL request and result helpers."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from data_platform.generate_features.engines.openai_batch import (
    CUSTOM_ID_PREFIX,
    HTTP_OK_STATUS_CODE,
    OPENAI_BATCH_ENDPOINT,
    OPENAI_BATCH_HTTP_METHOD,
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
from tests.data_platform.generate_features.conftest import (
    TinyLlmOut,
    make_openai_batch_output_line,
)


class TestCustomIdForIndex:
    """Tests for custom_id_for_index()."""

    def test_zero_pads_index(self) -> None:
        result = custom_id_for_index(0)
        expected = f"{CUSTOM_ID_PREFIX}00000"

        assert result == expected

    def test_keeps_ids_unique_for_later_indexes(self) -> None:
        result = custom_id_for_index(12)
        expected = f"{CUSTOM_ID_PREFIX}00012"

        assert result == expected


class TestStructuredResponseFormat:
    """Tests for structured_response_format()."""

    def test_wraps_pydantic_schema_as_strict_json_schema(self) -> None:
        result = structured_response_format(TinyLlmOut)

        assert result["type"] == "json_schema"
        assert result["json_schema"]["name"] == "TinyLlmOut"
        assert result["json_schema"]["strict"] is True
        assert result["json_schema"]["schema"]["additionalProperties"] is False
        assert "score" in result["json_schema"]["schema"]["properties"]


class TestBuildBatchRequestLine:
    """Tests for build_batch_request_line()."""

    def test_builds_chat_completion_batch_line(self) -> None:
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "TinyLlmOut", "strict": True, "schema": {}},
        }

        result = build_batch_request_line(
            "task-00000",
            "hello",
            "classify",
            "gpt-5.4-nano",
            response_format,
            0.0,
        )

        assert result["custom_id"] == "task-00000"
        assert result["method"] == OPENAI_BATCH_HTTP_METHOD
        assert result["url"] == OPENAI_BATCH_ENDPOINT
        assert result["body"]["model"] == "gpt-5.4-nano"
        assert result["body"]["temperature"] == 0.0
        assert result["body"]["response_format"] == response_format
        assert result["body"]["messages"] == [
            {"role": "system", "content": "classify"},
            {"role": "user", "content": "hello"},
        ]


class TestEncodeBatchJsonl:
    """Tests for encode_batch_jsonl()."""

    def test_encodes_one_object_per_line(self) -> None:
        request_lines = [
            {"custom_id": "task-00000", "method": "POST"},
            {"custom_id": "task-00001", "method": "POST"},
        ]

        result = encode_batch_jsonl(request_lines)
        decoded_lines = result.decode("utf-8").splitlines()

        assert [json.loads(line) for line in decoded_lines] == request_lines


class TestParseBatchOutputLine:
    """Tests for parse_batch_output_line()."""

    def test_reads_content_and_usage_from_success_line(self) -> None:
        raw_line = make_openai_batch_output_line("task-00000", "news", 11, 3)

        result = parse_batch_output_line(raw_line)
        expected = OpenAIBatchOutputRecord(
            custom_id="task-00000",
            status_code=HTTP_OK_STATUS_CODE,
            content=json.dumps({"category": "news"}),
            prompt_tokens=11,
            completion_tokens=3,
            error=None,
        )

        assert result == expected

    def test_captures_error_message_when_response_is_missing(self) -> None:
        raw_line = make_openai_batch_output_line(
            "task-00000",
            "news",
            error="rate limited",
        )

        result = parse_batch_output_line(raw_line)

        assert result.custom_id == "task-00000"
        assert result.content is None
        assert result.error == "rate limited"


class TestTokenUsageFromOutputRecords:
    """Tests for token_usage_from_output_records()."""

    def test_sums_tokens_across_records(self) -> None:
        records = [
            OpenAIBatchOutputRecord(
                custom_id="task-00000",
                status_code=HTTP_OK_STATUS_CODE,
                content="{}",
                prompt_tokens=10,
                completion_tokens=2,
                error=None,
            ),
            OpenAIBatchOutputRecord(
                custom_id="task-00001",
                status_code=HTTP_OK_STATUS_CODE,
                content="{}",
                prompt_tokens=4,
                completion_tokens=1,
                error=None,
            ),
        ]

        result = token_usage_from_output_records(records)
        expected = OpenAIBatchTokenUsage(
            prompt_tokens=14,
            completion_tokens=3,
            total_tokens=17,
            request_count=2,
        )

        assert result == expected


class TestLlmFieldsFromOutputRecord:
    """Tests for llm_fields_from_output_record()."""

    def test_validates_structured_content(self) -> None:
        record = OpenAIBatchOutputRecord(
            custom_id="task-00000",
            status_code=HTTP_OK_STATUS_CODE,
            content=json.dumps({"score": True}),
            prompt_tokens=10,
            completion_tokens=2,
            error=None,
        )

        result = llm_fields_from_output_record(record, TinyLlmOut)
        expected = {"score": True}

        assert result == expected

    def test_raises_when_content_is_missing(self) -> None:
        record = OpenAIBatchOutputRecord(
            custom_id="task-00000",
            status_code=None,
            content=None,
            prompt_tokens=0,
            completion_tokens=0,
            error="failed",
        )

        with pytest.raises(ValueError, match="task-00000"):
            llm_fields_from_output_record(record, TinyLlmOut)

    def test_raises_when_content_does_not_match_schema(self) -> None:
        record = OpenAIBatchOutputRecord(
            custom_id="task-00000",
            status_code=HTTP_OK_STATUS_CODE,
            content=json.dumps({"score": "not-a-bool"}),
            prompt_tokens=10,
            completion_tokens=2,
            error=None,
        )

        with pytest.raises(ValidationError):
            llm_fields_from_output_record(record, TinyLlmOut)
