"""Tests for build_all_posts_frame and writers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.build_all_posts import (
    build_all_posts_frame,
    write_all_posts,
    write_chat_jsonl,
)


def _trial_row(
    *,
    post_id: str,
    prolific_id: str,
    decision: str,
    original_text: str = "orig",
    mirror_text: str = "mir",
) -> dict[str, str]:
    return {
        "post_id": post_id,
        "prolific_id": prolific_id,
        "decision": decision,
        "evaluation_mode": "linked_fate",
        "original_text": original_text,
        "mirror_text": mirror_text,
    }


def _manifest_row(
    *,
    post_id: str,
    split: str,
    modal_label: str,
    in_unanimous: bool,
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "split": split,
        "modal_label": modal_label,
        "in_unanimous": in_unanimous,
    }


class TestBuildAllPostsFrame:
    """Tests for build_all_posts_frame."""

    def test_tie_becomes_remove(self) -> None:
        """Tied keep and remove counts become remove."""
        raw = pd.DataFrame(
            [
                _trial_row(post_id="C", prolific_id="W1", decision="keep"),
                _trial_row(post_id="C", prolific_id="W2", decision="remove"),
            ]
        )
        manifest = pd.DataFrame(
            [_manifest_row(post_id="C", split="test", modal_label="remove", in_unanimous=False)]
        )

        result = build_all_posts_frame(raw, manifest)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["message_id"] == "C"
        assert row["decision"] == "remove"
        assert row["keep_remove_label"] == 1

    def test_n_remove_and_n_raters(self) -> None:
        """n_remove counts remove trials; n_raters matches modal aggregation."""
        raw = pd.DataFrame(
            [
                _trial_row(post_id="H", prolific_id="W1", decision="keep"),
                _trial_row(post_id="H", prolific_id="W2", decision="keep"),
                _trial_row(post_id="H", prolific_id="W3", decision="remove"),
            ]
        )
        manifest = pd.DataFrame(
            [_manifest_row(post_id="H", split="train", modal_label="keep", in_unanimous=True)]
        )

        result = build_all_posts_frame(raw, manifest)

        row = result.iloc[0]
        assert row["n_raters"] == 3
        assert row["n_remove"] == 1
        assert row["decision"] == "keep"

    def test_manifest_join_adds_split_and_in_unanimous(self) -> None:
        """Split manifest columns appear on the output frame."""
        raw = pd.DataFrame(
            [
                _trial_row(post_id="P1", prolific_id="W1", decision="remove"),
                _trial_row(post_id="P1", prolific_id="W2", decision="remove"),
            ]
        )
        manifest = pd.DataFrame(
            [
                _manifest_row(
                    post_id="P1",
                    split="test",
                    modal_label="remove",
                    in_unanimous=True,
                )
            ]
        )

        result = build_all_posts_frame(raw, manifest)

        row = result.iloc[0]
        assert row["split"] == "test"
        assert bool(row["in_unanimous"]) is True

    def test_missing_manifest_post_raises(self) -> None:
        """Modal post absent from manifest raises ValueError."""
        raw = pd.DataFrame(
            [_trial_row(post_id="MISSING", prolific_id="W1", decision="keep")]
        )
        manifest = pd.DataFrame(
            [_manifest_row(post_id="OTHER", split="train", modal_label="keep", in_unanimous=False)]
        )

        with pytest.raises(ValueError, match="missing from split manifest"):
            build_all_posts_frame(raw, manifest)

    def test_dedupe_drops_conflicting_worker(self) -> None:
        """Conflicting worker-post pair is dropped before aggregation."""
        raw = pd.DataFrame(
            [
                _trial_row(post_id="X1", prolific_id="W1", decision="keep"),
                _trial_row(post_id="X1", prolific_id="W1", decision="remove"),
                _trial_row(post_id="X1", prolific_id="W2", decision="remove"),
            ]
        )
        manifest = pd.DataFrame(
            [
                _manifest_row(
                    post_id="X1",
                    split="train",
                    modal_label="remove",
                    in_unanimous=False,
                )
            ]
        )

        result = build_all_posts_frame(raw, manifest)

        row = result.iloc[0]
        assert row["n_raters"] == 1
        assert row["n_remove"] == 1
        assert row["decision"] == "remove"


class TestWriteChatJsonl:
    """Tests for write_chat_jsonl."""

    def test_chat_record_has_system_user_assistant(self, tmp_path: Path) -> None:
        """Each JSONL line includes system, user, and assistant messages."""
        frame = pd.DataFrame(
            [
                {
                    "message_id": "post-1",
                    "original_text": "alpha",
                    "mirror_text": "beta",
                    "decision": "keep",
                    "keep_remove_label": 0,
                    "n_raters": 1,
                    "n_remove": 0,
                    "split": "train",
                    "in_unanimous": False,
                }
            ]
        )
        jsonl_path = tmp_path / "chat_all_posts.jsonl"

        write_chat_jsonl(frame, jsonl_path)

        with jsonl_path.open(encoding="utf-8") as handle:
            record = json.loads(handle.readline())

        roles = [msg["role"] for msg in record["messages"]]
        assert roles == ["system", "user", "assistant"]
        assert record["message_id"] == "post-1"
        assert record["messages"][2]["content"] == "keep"


class TestWriteAllPosts:
    """Tests for write_all_posts."""

    def test_csv_round_trip_columns(self, tmp_path: Path) -> None:
        """Written CSV preserves canonical columns."""
        frame = pd.DataFrame(
            [
                {
                    "message_id": "a",
                    "original_text": "o",
                    "mirror_text": "m",
                    "decision": "keep",
                    "keep_remove_label": 0,
                    "n_raters": 2,
                    "n_remove": 0,
                    "split": "train",
                    "in_unanimous": True,
                }
            ]
        )
        csv_path = tmp_path / "all_posts.csv"

        write_all_posts(frame, csv_path)
        loaded = pd.read_csv(csv_path)

        assert list(loaded.columns) == list(frame.columns)
