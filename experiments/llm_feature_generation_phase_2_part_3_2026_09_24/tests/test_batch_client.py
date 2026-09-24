"""Tests for OpenAI Batch labeling helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batch_client, constants, llm_client
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import PostLabelResult


def _sample_codebook() -> list[dict]:
    return [
        {"feature_id": "cb_001", "name": "feat one", "definition": "The post uses slang."},
        {"feature_id": "cb_002", "name": "feat two", "definition": "The post asks a question."},
    ]


def _sample_posts() -> list[dict[str, str]]:
    return [
        {
            "post_id": "p1",
            "original_text": "hello",
            "mirror_text": "hi",
        },
        {
            "post_id": "p2",
            "original_text": "world",
            "mirror_text": "earth",
        },
    ]


def _make_output_line(custom_id: str, labels: dict[str, bool]) -> str:
    content = json.dumps({"labels": labels})
    return json.dumps(
        {
            "custom_id": custom_id,
            "response": {
                "status_code": 200,
                "body": {
                    "choices": [{"message": {"content": content}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                },
            },
        }
    )


class TestBuildBatchJsonl:
    """Tests for build_batch_jsonl."""

    def test_batch_jsonl_custom_id_format(self, tmp_path: Path) -> None:
        paths = batch_client.build_batch_jsonl(
            _sample_posts(),
            _sample_codebook(),
            ("original", "mirror"),
            tmp_path,
        )
        lines = paths[0].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 4
        custom_ids = {json.loads(line)["custom_id"] for line in lines}
        assert custom_ids == {"p1__original", "p1__mirror", "p2__original", "p2__mirror"}

    def test_batch_jsonl_body_has_model_and_schema(self, tmp_path: Path) -> None:
        paths = batch_client.build_batch_jsonl(
            [_sample_posts()[0]],
            _sample_codebook(),
            ("original",),
            tmp_path,
        )
        body = json.loads(paths[0].read_text(encoding="utf-8").splitlines()[0])["body"]
        assert body["model"] == constants.LLM_MODEL_ID
        assert body["reasoning_effort"] == constants.LLM_REASONING_EFFORT
        assert body["response_format"]["type"] == "json_schema"


class TestEstimateBatchCost:
    """Tests for estimate_batch_cost."""

    def test_projected_batch_cost_under_cap_before_submit(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "big.jsonl"
        jsonl_path.write_text("x" * 10_000_000 + "\n", encoding="utf-8")
        with patch.object(llm_client, "read_cumulative_cost_usd", return_value=24.99):
            estimate = batch_client.estimate_batch_cost([jsonl_path], feature_count=50)
        assert estimate.projected_total_usd >= constants.SPEND_CAP_USD


class TestParseBatchOutput:
    """Tests for parse_batch_output."""

    def test_batch_client_parses_output_to_labels(self, tmp_path: Path) -> None:
        line = _make_output_line("p1__original", {"cb_001": True, "cb_002": False})
        rows = batch_client.parse_batch_output([line])
        assert len(rows) == 1
        assert rows[0].post_id == "p1"
        assert rows[0].text_surface == "original"
        assert rows[0].labels["cb_001"] is True


class TestResubmitMissing:
    """Tests for resubmit_missing."""

    def test_batch_resubmit_only_failed_custom_ids(self, tmp_path: Path) -> None:
        present = {"p1__original", "p1__mirror", "p2__original"}
        paths = batch_client.resubmit_missing(
            _sample_posts(),
            _sample_codebook(),
            ("original", "mirror"),
            present,
            tmp_path,
        )
        lines = paths[0].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["custom_id"] == "p2__mirror"


class TestAppendBatchCostLog:
    """Tests for append_batch_cost_log."""

    def test_cost_log_uses_batch_prices_after_batch(self, tmp_path: Path) -> None:
        cost_log = tmp_path / "cost_log.jsonl"
        with patch.object(llm_client.paths, "cost_log_path", return_value=cost_log):
            batch_client.append_batch_cost_log(
                stage=batch_client.STAGE_LABEL_BATCH,
                input_tokens=1_000_000,
                output_tokens=0,
            )
        record = json.loads(cost_log.read_text(encoding="utf-8").strip())
        expected = llm_client.compute_cost_usd(1_000_000, 0) * batch_client.BATCH_PRICE_FRACTION
        assert record["cost_usd"] == expected


class TestSubmitBatch:
    """Tests for submit_batch."""

    def test_submit_batch_returns_batch_id(self, tmp_path: Path) -> None:
        jsonl = tmp_path / "in.jsonl"
        jsonl.write_text("{}\n", encoding="utf-8")
        client = MagicMock()
        client.files.create.return_value = MagicMock(id="file_1")
        client.batches.create.return_value = MagicMock(id="batch_abc")
        batch_id = batch_client.submit_batch(client, jsonl)
        assert batch_id == "batch_abc"
