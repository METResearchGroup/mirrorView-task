"""Tests for discovery and downstream LLM prompt builders."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    MAX_KEEP_FEATURES_PER_BATCH,
    MAX_REMOVE_FEATURES_PER_BATCH,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
    FEATURE_GENERATION_SYSTEM_PROMPT,
    LABEL_SYSTEM_PROMPT_MAX_CHARS,
    _LABELING_ENTRY_KEYS,
    assert_labeling_system_prompt_clean,
    build_feature_generation_messages,
    build_labeling_prompt,
    labeling_system_prompt,
    project_codebook_for_labeling,
    serialize_labeling_codebook_json,
)


def _mixed_batch() -> dict[str, object]:
    keep_posts = [
        {
            "message_id": "p1",
            "original_text": "Original keep",
            "mirror_text": "Mirror keep",
        }
    ]
    remove_posts = [
        {
            "message_id": "p2",
            "original_text": "Original remove",
            "mirror_text": "Mirror remove",
        }
    ]
    return {
        "batch_id": 0,
        "keep_posts": keep_posts,
        "remove_posts": remove_posts,
    }


def _payloads_from_messages(messages: list[dict[str, str]]) -> list[dict[str, object]]:
    user_content = messages[1]["content"]
    keep_json = user_content.split("Keep-rated posts:")[1].split("Remove-rated posts:")[0]
    remove_json = user_content.split("Remove-rated posts:")[1]
    return json.loads(keep_json.strip()) + json.loads(remove_json.strip())


def _sample_label_codebook_entry() -> dict[str, object]:
    return {
        "feature_id": "cb_001",
        "name": "informal slang",
        "definition": "The post uses informal slang or colloquial phrasing.",
        "positive_examples": [{"post_id": "p1", "text": "lol this is wild"}],
        "negative_examples": [{"post_id": "p2", "text": "The committee met on Tuesday."}],
        "source_definition": "Remove posts that use slang",
        "member_feature_ids": ["mixed_1"],
    }


def test_original_only_hides_mirror() -> None:
    """original_only payloads include original_text only."""
    messages = build_feature_generation_messages(_mixed_batch(), arm="original_only")
    payloads = _payloads_from_messages(messages)
    for payload in payloads:
        assert "original_text" in payload
        assert "mirror_text" not in payload


def test_mirror_only_hides_original() -> None:
    """mirror_only payloads include mirror_text only."""
    messages = build_feature_generation_messages(_mixed_batch(), arm="mirror_only")
    payloads = _payloads_from_messages(messages)
    for payload in payloads:
        assert "mirror_text" in payload
        assert "original_text" not in payload


def test_paired_includes_both() -> None:
    """paired payloads include both original and mirror text."""
    messages = build_feature_generation_messages(_mixed_batch(), arm="paired")
    payloads = _payloads_from_messages(messages)
    for payload in payloads:
        assert "original_text" in payload
        assert "mirror_text" in payload


def test_prompt_mentions_max_eight_features() -> None:
    """System prompt states the per-group feature caps."""
    assert str(MAX_KEEP_FEATURES_PER_BATCH) in FEATURE_GENERATION_SYSTEM_PROMPT
    assert str(MAX_REMOVE_FEATURES_PER_BATCH) in FEATURE_GENERATION_SYSTEM_PROMPT


class TestLabelingCodebookProjection:
    """Tests for labeling prompt codebook projection."""

    def test_projected_entries_use_only_allowed_keys(self) -> None:
        projected = project_codebook_for_labeling([_sample_label_codebook_entry()])
        assert set(projected[0].keys()) == _LABELING_ENTRY_KEYS

    def test_labeling_system_prefix_is_identical_across_posts(self) -> None:
        codebook = [_sample_label_codebook_entry()]
        first = build_labeling_prompt(codebook, "alpha", "original")[0]["content"]
        second = build_labeling_prompt(codebook, "beta", "mirror")[0]["content"]
        assert first == second

    def test_labeling_system_prompt_has_no_outcome_leakage(self) -> None:
        codebook = [_sample_label_codebook_entry()]
        system_prompt = labeling_system_prompt(codebook)
        assert_labeling_system_prompt_clean(codebook, system_prompt)

    def test_approved_codebook_system_prompt_under_ceiling(self) -> None:
        codebook_path = (
            Path(__file__).resolve().parents[1]
            / "outputs/shared/codebook/approved_2026-09-24T15-12-23/codebook.json"
        )
        if not codebook_path.is_file():
            pytest.skip("approved codebook artifact not present")
        features = json.loads(codebook_path.read_text(encoding="utf-8"))["features"]
        system_prompt = labeling_system_prompt(features)
        assert len(system_prompt) < LABEL_SYSTEM_PROMPT_MAX_CHARS
        assert_labeling_system_prompt_clean(features, system_prompt)

    def test_serialized_codebook_is_byte_stable(self) -> None:
        codebook = [_sample_label_codebook_entry(), {**_sample_label_codebook_entry(), "feature_id": "cb_002"}]
        first = serialize_labeling_codebook_json(codebook)
        second = serialize_labeling_codebook_json(list(reversed(codebook)))
        assert first == second
