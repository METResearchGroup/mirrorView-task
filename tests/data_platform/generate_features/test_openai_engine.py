"""Tests for the OpenAI Batch feature engine and factory wiring."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import httpx
import pytest
from openai import APIConnectionError

from data_platform.generate_features.engines import ENGINE_BUILDERS, build_engine
from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchEngine,
    build_openai_engine,
    wait_for_completed_batch,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from tests.data_platform.constants import LABEL_TIMESTAMP, URI_POST_A, URI_POST_B
from tests.data_platform.generate_features.conftest import (
    TinyLlmOut,
    TinyRowModel,
    make_completed_openai_client,
    make_openai_batch_output_line,
    make_openai_news_spec,
)


def _make_engine(
    spec: FeatureSpec,
    client: MagicMock,
    sleep_fn=lambda _seconds: None,
) -> OpenAIBatchEngine:
    return OpenAIBatchEngine(
        spec,
        FeatureRunConfig(),
        client,
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        sleep_fn,
    )


class TestOpenAIBatchEngineInit:
    """Tests for OpenAIBatchEngine.__init__()."""

    def test_requires_system_prompt(self) -> None:
        spec = FeatureSpec(
            name="test_feature",
            model=TinyRowModel,
            engine_type="openai",
            llm_output_schema=TinyLlmOut,
        )

        with pytest.raises(ValueError, match="system_prompt"):
            _make_engine(spec, MagicMock())

    def test_requires_llm_output_schema(self) -> None:
        spec = FeatureSpec(
            name="test_feature",
            model=TinyRowModel,
            engine_type="openai",
            system_prompt="classify",
        )

        with pytest.raises(ValueError, match="llm_output_schema"):
            _make_engine(spec, MagicMock())


class TestOpenAIBatchEngineBatchLabelRecords:
    """Tests for OpenAIBatchEngine.batch_label_records()."""

    def test_returns_validated_label_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "data_platform.generate_features.engines.openai_engine.get_current_timestamp",
            lambda: LABEL_TIMESTAMP,
        )
        output_text = "\n".join(
            [
                make_openai_batch_output_line("task-00000", "news", 10, 2),
                make_openai_batch_output_line("task-00001", "opinion", 12, 3),
            ]
        )
        client = make_completed_openai_client(output_text)
        engine = _make_engine(make_openai_news_spec(), client)
        tasks = [
            LabelTask(uri=URI_POST_A, text="Fed raised rates."),
            LabelTask(uri=URI_POST_B, text="This policy is a disaster."),
        ]

        result = engine.batch_label_records(tasks)

        assert [row["source_record_id"] for row in result] == [URI_POST_A, URI_POST_B]
        assert [row["category"] for row in result] == ["news", "opinion"]
        assert result[0]["label_timestamp"] == LABEL_TIMESTAMP
        assert engine.last_batch is not None
        assert engine.last_batch.id == "batch_1"
        client.files.create.assert_called_once()
        uploaded_file = client.files.create.call_args.kwargs["file"]
        assert isinstance(uploaded_file, io.IOBase)
        client.batches.create.assert_called_once()
        client.files.content.assert_called_once_with("file_output")

    def test_returns_empty_list_for_no_tasks(self) -> None:
        engine = _make_engine(make_openai_news_spec(), MagicMock())

        result = engine.batch_label_records([])

        assert result == []

    def test_raises_when_an_output_request_fails(self) -> None:
        error_text = make_openai_batch_output_line(
            "task-00000",
            "news",
            error="invalid prompt",
        )
        client = make_completed_openai_client("", error_text)
        engine = _make_engine(make_openai_news_spec(), client)
        tasks = [LabelTask(uri=URI_POST_A, text="hello")]

        with pytest.raises(RuntimeError, match="task-00000"):
            engine.batch_label_records(tasks)

        client.files.content.assert_called_once_with("file_error")

    def test_raises_when_an_output_custom_id_is_missing(self) -> None:
        output_text = make_openai_batch_output_line("task-00001", "news")
        client = make_completed_openai_client(output_text)
        engine = _make_engine(make_openai_news_spec(), client)
        tasks = [LabelTask(uri=URI_POST_A, text="hello")]

        with pytest.raises(ValueError, match="task-00000"):
            engine.batch_label_records(tasks)

    def test_retries_output_download_without_creating_new_batch(self) -> None:
        output_text = make_openai_batch_output_line("task-00000", "news")
        client = make_completed_openai_client(output_text)
        connection_error = APIConnectionError(
            request=httpx.Request("GET", "https://api.openai.com/v1/files/file_output")
        )
        output_file = MagicMock(text=output_text)
        client.files.content.side_effect = [connection_error, output_file]
        sleeps: list[float] = []
        engine = _make_engine(make_openai_news_spec(), client, sleeps.append)
        tasks = [LabelTask(uri=URI_POST_A, text="Fed raised rates.")]

        result = engine.batch_label_records(tasks)

        assert result[0]["category"] == "news"
        assert sleeps == [1.0]
        client.batches.create.assert_called_once()
        assert client.files.content.call_count == 2


class TestWaitForCompletedBatch:
    """Tests for wait_for_completed_batch()."""

    def test_returns_when_batch_is_already_completed(self) -> None:
        client = MagicMock()
        completed = MagicMock()
        completed.status = "completed"
        client.batches.retrieve.return_value = completed
        sleeps: list[float] = []

        result = wait_for_completed_batch(
            client,
            "batch_1",
            5.0,
            sleeps.append,
        )

        assert result is completed
        assert sleeps == []

    def test_keeps_polling_until_openai_reports_completion(self) -> None:
        client = MagicMock()
        pending = MagicMock(status="in_progress")
        completed = MagicMock(status="completed")
        client.batches.retrieve.side_effect = [pending, completed]
        sleeps: list[float] = []

        result = wait_for_completed_batch(
            client,
            "batch_1",
            5.0,
            sleeps.append,
        )

        assert result is completed
        assert sleeps == [5.0]

    def test_retries_transient_retrieve_error_without_creating_new_batch(self) -> None:
        client = MagicMock()
        completed = MagicMock(status="completed")
        connection_error = APIConnectionError(
            request=httpx.Request("GET", "https://api.openai.com/v1/batches/batch_1")
        )
        client.batches.retrieve.side_effect = [connection_error, completed]
        sleeps: list[float] = []

        result = wait_for_completed_batch(
            client,
            "batch_1",
            5.0,
            sleeps.append,
        )

        assert result is completed
        assert sleeps == [1.0]
        client.batches.create.assert_not_called()

    def test_waits_while_batch_is_cancelling(self) -> None:
        client = MagicMock()
        cancelling = MagicMock(status="cancelling")
        cancelled = MagicMock(status="cancelled")
        client.batches.retrieve.side_effect = [cancelling, cancelled]
        sleeps: list[float] = []

        with pytest.raises(RuntimeError, match="cancelled"):
            wait_for_completed_batch(
                client,
                "batch_1",
                5.0,
                sleeps.append,
            )

        assert sleeps == [5.0]

    def test_raises_when_batch_fails(self) -> None:
        client = MagicMock()
        failed = MagicMock()
        failed.status = "failed"
        failed.errors = "bad file"
        client.batches.retrieve.return_value = failed

        with pytest.raises(RuntimeError, match="failed"):
            wait_for_completed_batch(
                client,
                "batch_1",
                5.0,
                lambda _seconds: None,
            )


class TestBuildEngine:
    """Tests for build_engine()."""

    def test_dispatches_openai_builder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sentinel = MagicMock()
        monkeypatch.setitem(ENGINE_BUILDERS, "openai", lambda spec, run_config: sentinel)
        spec = make_openai_news_spec()

        result = build_engine(spec, FeatureRunConfig())

        assert result is sentinel

    def test_unknown_engine_type_raises(self) -> None:
        spec = FeatureSpec(
            name="test_feature",
            model=TinyRowModel,
            engine_type="langchain",
            system_prompt="x",
            llm_output_schema=TinyLlmOut,
        )
        object.__setattr__(spec, "engine_type", "unknown")

        with pytest.raises(ValueError, match="Unknown engine_type"):
            build_engine(spec, FeatureRunConfig())


class TestBuildOpenAIEngine:
    """Tests for build_openai_engine()."""

    def test_constructs_engine_with_sdk_client(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_client = MagicMock()
        monkeypatch.setattr(
            "data_platform.generate_features.engines.openai_engine.create_openai_client",
            lambda: fake_client,
        )
        spec = make_openai_news_spec()

        result = build_openai_engine(spec, FeatureRunConfig())

        assert isinstance(result, OpenAIBatchEngine)
        assert result.last_batch is None
