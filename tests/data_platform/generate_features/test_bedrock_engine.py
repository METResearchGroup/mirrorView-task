"""Tests for the Bedrock Converse feature engine and factory wiring."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from data_platform.generate_features.engines import ENGINE_BUILDERS, build_engine
from data_platform.generate_features.engines.bedrock_engine import (
    CONVERSE_RETRY_ATTEMPTS,
    BedrockConverseEngine,
    BedrockUsage,
    build_bedrock_engine,
    parse_json_object,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO
from tests.data_platform.constants import LABEL_TIMESTAMP, URI_POST_A, URI_POST_B
from tests.data_platform.generate_features.conftest import (
    TinyLlmOut,
    TinyRowModel,
    make_openai_news_spec,
)


def _converse_response(
    category: str,
    input_tokens: int = 10,
    output_tokens: int = 2,
    text: str | None = None,
) -> dict:
    content = text if text is not None else json.dumps({"category": category})
    return {
        "output": {"message": {"content": [{"text": content}]}},
        "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens},
        "stopReason": "end_turn",
    }


def _make_engine(spec: FeatureSpec, client: MagicMock) -> BedrockConverseEngine:
    return BedrockConverseEngine(
        spec,
        FeatureRunConfig(max_concurrency=2),
        client,
        DEFAULT_BEDROCK_NOVA_MICRO,
    )


def _news_spec() -> FeatureSpec:
    spec = make_openai_news_spec()
    return FeatureSpec(
        name=spec.name,
        model=spec.model,
        engine_type="bedrock",
        system_prompt=spec.system_prompt,
        llm_output_schema=spec.llm_output_schema,
    )


class TestParseJsonObject:
    """Tests for parse_json_object()."""

    def test_parses_a_plain_object(self) -> None:
        expected = {"category": "news"}
        result = parse_json_object('{"category": "news"}')
        assert result == expected

    def test_strips_markdown_fences(self) -> None:
        expected = {"category": "opinion"}
        result = parse_json_object('```json\n{"category": "opinion"}\n```')
        assert result == expected

    def test_accepts_a_bare_category_word(self) -> None:
        expected = {"category": "neither"}
        result = parse_json_object("neither")
        assert result == expected

    def test_maps_content_filter_text_to_neither(self) -> None:
        expected = {"category": "neither"}
        result = parse_json_object(
            "- The generated text has been blocked by our content filters."
        )
        assert result == expected

    def test_raises_when_json_is_not_an_object(self) -> None:
        with pytest.raises(ValueError, match="object"):
            parse_json_object("[1]")


class TestBedrockConverseEngineInit:
    """Tests for BedrockConverseEngine.__init__()."""

    def test_requires_system_prompt(self) -> None:
        spec = FeatureSpec(
            name="test_feature",
            model=TinyRowModel,
            engine_type="bedrock",
            llm_output_schema=TinyLlmOut,
        )
        with pytest.raises(ValueError, match="system_prompt"):
            _make_engine(spec, MagicMock())

    def test_requires_llm_output_schema(self) -> None:
        spec = FeatureSpec(
            name="test_feature",
            model=TinyRowModel,
            engine_type="bedrock",
            system_prompt="classify",
        )
        with pytest.raises(ValueError, match="llm_output_schema"):
            _make_engine(spec, MagicMock())


class TestBedrockConverseEngineBatchLabelRecords:
    """Tests for BedrockConverseEngine.batch_label_records()."""

    def test_returns_validated_label_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.get_current_timestamp",
            lambda: LABEL_TIMESTAMP,
        )
        client = MagicMock()
        client.converse.return_value = _converse_response("news")
        engine = _make_engine(_news_spec(), client)
        tasks = [LabelTask(uri=URI_POST_A, text="Fed raised rates.")]

        result = engine.batch_label_records(tasks)
        expected = [
            {
                "source_record_id": URI_POST_A,
                "label_timestamp": LABEL_TIMESTAMP,
                "category": "news",
            }
        ]
        assert result == expected
        assert engine.last_usage == BedrockUsage(10, 2, 12)
        client.converse.assert_called_once()

    def test_preserves_input_order_for_two_tasks(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.get_current_timestamp",
            lambda: LABEL_TIMESTAMP,
        )
        client = MagicMock()

        def _converse(**kwargs: object) -> dict:
            messages = kwargs["messages"]  # type: ignore[index]
            text = messages[0]["content"][0]["text"]
            if "Fed" in text:
                return _converse_response("news", 10, 2)
            return _converse_response("opinion", 12, 3)

        client.converse.side_effect = _converse
        engine = _make_engine(_news_spec(), client)
        tasks = [
            LabelTask(uri=URI_POST_A, text="Fed raised rates."),
            LabelTask(uri=URI_POST_B, text="This policy is a disaster."),
        ]

        result = engine.batch_label_records(tasks)
        expected_categories = ["news", "opinion"]
        assert [row["category"] for row in result] == expected_categories
        assert [row["source_record_id"] for row in result] == [URI_POST_A, URI_POST_B]
        assert engine.last_usage == BedrockUsage(22, 5, 27)

    def test_returns_empty_list_for_no_tasks(self) -> None:
        client = MagicMock()
        engine = _make_engine(_news_spec(), client)

        result = engine.batch_label_records([])

        assert result == []
        assert engine.last_usage == BedrockUsage(0, 0, 0)
        client.converse.assert_not_called()

    def test_raises_when_response_is_not_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.time.sleep",
            lambda seconds: None,
        )
        client = MagicMock()
        client.converse.return_value = _converse_response(
            "news",
            text="not json",
        )
        engine = _make_engine(_news_spec(), client)
        tasks = [LabelTask(uri=URI_POST_A, text="hello")]

        with pytest.raises(ValueError):
            engine.batch_label_records(tasks)
        assert client.converse.call_count == CONVERSE_RETRY_ATTEMPTS

    def test_retries_empty_json_then_succeeds(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.get_current_timestamp",
            lambda: LABEL_TIMESTAMP,
        )
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.time.sleep",
            lambda seconds: None,
        )
        client = MagicMock()
        client.converse.side_effect = [
            _converse_response("news", text=""),
            _converse_response("news"),
        ]
        engine = _make_engine(_news_spec(), client)
        tasks = [LabelTask(uri=URI_POST_A, text="Fed raised rates.")]

        result = engine.batch_label_records(tasks)

        assert result[0]["category"] == "news"
        assert client.converse.call_count == 2


class TestBuildEngine:
    """Tests for build_engine() bedrock dispatch."""

    def test_dispatches_bedrock_builder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sentinel = MagicMock()
        monkeypatch.setitem(ENGINE_BUILDERS, "bedrock", lambda spec, run_config: sentinel)
        spec = _news_spec()

        result = build_engine(spec, FeatureRunConfig())

        assert result is sentinel


class TestBuildBedrockEngine:
    """Tests for build_bedrock_engine()."""

    def test_constructs_engine_with_runtime_client(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_client = MagicMock()
        monkeypatch.setattr(
            "data_platform.generate_features.engines.bedrock_engine.create_bedrock_runtime_client",
            lambda: fake_client,
        )
        spec = _news_spec()

        result = build_bedrock_engine(spec, FeatureRunConfig())

        assert isinstance(result, BedrockConverseEngine)
        assert result.last_usage is None
