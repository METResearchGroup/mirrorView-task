"""Tests for Part 3 chat dataset creation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.finetune_lora_phase2_part3_2026_09_24.shared.create_chat_dataset import (
    row_to_chat_record,
    write_chat_jsonl,
)


class TestRowToChatRecord:
    """Tests for row_to_chat_record."""

    def test_user_content_has_post1_original_and_post2_mirror(self):
        """User prompt places original text in Post 1 and mirror in Post 2."""
        row = pd.Series(
            {
                "message_id": "post-1",
                "original_text": "alpha original",
                "mirror_text": "beta mirror",
                "decision": "keep",
            }
        )

        result = row_to_chat_record(row)
        user_content = result["messages"][1]["content"]

        assert "Post 1: alpha original" in user_content
        assert "Post 2: beta mirror" in user_content
        assert "Allow Or Remove?" not in user_content

    def test_assistant_content_is_keep_or_remove(self):
        """Assistant message matches the gold decision."""
        row = pd.Series(
            {
                "message_id": "post-2",
                "original_text": "alpha",
                "mirror_text": "beta",
                "decision": "remove",
            }
        )

        result = row_to_chat_record(row)

        assert result["messages"][2]["content"] == "remove"


class TestWriteChatJsonl:
    """Tests for write_chat_jsonl."""

    def test_jsonl_line_count_matches_csv_rows(self, tmp_path: Path):
        """JSONL row count equals the source CSV row count."""
        csv_path = tmp_path / "train.csv"
        jsonl_path = tmp_path / "chat_train.jsonl"
        frame = pd.DataFrame(
            [
                {
                    "message_id": "a",
                    "original_text": "orig-a",
                    "mirror_text": "mir-a",
                    "decision": "keep",
                },
                {
                    "message_id": "b",
                    "original_text": "orig-b",
                    "mirror_text": "mir-b",
                    "decision": "remove",
                },
            ]
        )
        frame.to_csv(csv_path, index=False)

        row_count = write_chat_jsonl(csv_path, jsonl_path, force=True)

        assert row_count == len(frame)

    def test_each_jsonl_line_has_message_id_and_messages(self, tmp_path: Path):
        """Each JSONL record includes message_id and messages keys."""
        csv_path = tmp_path / "train.csv"
        jsonl_path = tmp_path / "chat_train.jsonl"
        frame = pd.DataFrame(
            [
                {
                    "message_id": "a",
                    "original_text": "orig-a",
                    "mirror_text": "mir-a",
                    "decision": "keep",
                }
            ]
        )
        frame.to_csv(csv_path, index=False)
        write_chat_jsonl(csv_path, jsonl_path, force=True)

        with jsonl_path.open(encoding="utf-8") as handle:
            record = json.loads(handle.readline())

        assert "message_id" in record
        assert "messages" in record
