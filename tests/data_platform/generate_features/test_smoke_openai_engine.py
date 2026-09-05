"""Tests for OpenAI Batch engine smoke-test helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from openai.types import BatchUsage

from data_platform.generate_features.models import LabelTask
from data_platform.generate_features.smoke_openai_engine import (
    OpenAIEngineSmokeMetrics,
    compute_openai_engine_smoke_metrics,
    load_smoke_label_tasks,
)
from tests.data_platform.constants import URI_POST_A, URI_POST_B


def _batch_usage(input_tokens: int, output_tokens: int) -> BatchUsage:
    return BatchUsage.model_validate(
        {
            "input_tokens": input_tokens,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": output_tokens,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": input_tokens + output_tokens,
        }
    )


class TestLoadSmokeLabelTasks:
    """Tests for load_smoke_label_tasks()."""

    def test_loads_requested_post_count(self, tmp_path: Path) -> None:
        posts_csv = tmp_path / "posts.csv"
        posts_csv.write_text(
            "uri,text\n"
            f"{URI_POST_A},Fed raised rates today.\n"
            f"{URI_POST_B},This policy is a disaster.\n"
            "at://c/post/3,Just got coffee.\n",
            encoding="utf-8",
        )

        result = load_smoke_label_tasks(posts_csv, 2, "uri", "text")
        expected = [
            LabelTask(uri=URI_POST_A, text="Fed raised rates today."),
            LabelTask(uri=URI_POST_B, text="This policy is a disaster."),
        ]

        assert result == expected

    def test_skips_empty_text_before_counting(self, tmp_path: Path) -> None:
        posts_csv = tmp_path / "posts.csv"
        posts_csv.write_text(
            "uri,text\n"
            f"{URI_POST_A},\n"
            f"{URI_POST_B},Just got coffee.\n"
            "at://c/post/3,City council approved the budget.\n",
            encoding="utf-8",
        )

        result = load_smoke_label_tasks(posts_csv, 2, "uri", "text")

        assert [task.uri for task in result] == [URI_POST_B, "at://c/post/3"]

    def test_raises_when_csv_has_too_few_posts(self, tmp_path: Path) -> None:
        posts_csv = tmp_path / "posts.csv"
        posts_csv.write_text(
            f"uri,text\n{URI_POST_A},hello\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="2"):
            load_smoke_label_tasks(posts_csv, 2, "uri", "text")


class TestComputeOpenAIEngineSmokeMetrics:
    """Tests for compute_openai_engine_smoke_metrics()."""

    def test_reports_throughput_and_per_request_token_estimates(self) -> None:
        usage = _batch_usage(1000, 50)

        result = compute_openai_engine_smoke_metrics(
            usage,
            10,
            2.0,
            10,
            "gpt-5.4-nano",
        )
        expected = OpenAIEngineSmokeMetrics(
            post_count=10,
            labeled_count=10,
            elapsed_seconds=2.0,
            posts_per_second=5.0,
            tokens_per_second=525.0,
            estimated_input_tokens_per_request=100.0,
            estimated_output_tokens_per_request=5.0,
            prompt_tokens=1000,
            completion_tokens=50,
            total_tokens=1050,
            model="gpt-5.4-nano",
        )

        assert result == expected

    def test_raises_when_elapsed_time_is_not_positive(self) -> None:
        usage = _batch_usage(10, 2)

        with pytest.raises(ValueError, match="elapsed"):
            compute_openai_engine_smoke_metrics(usage, 1, 0.0, 1, "gpt-5.4-nano")

    def test_raises_when_request_count_is_zero(self) -> None:
        usage = _batch_usage(0, 0)

        with pytest.raises(ValueError, match="request_count"):
            compute_openai_engine_smoke_metrics(usage, 0, 1.0, 0, "gpt-5.4-nano")
