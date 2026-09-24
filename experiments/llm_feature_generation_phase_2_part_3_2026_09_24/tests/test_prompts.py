"""Tests for discovery and downstream LLM prompt builders."""

from __future__ import annotations

import json

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    MAX_KEEP_FEATURES_PER_BATCH,
    MAX_REMOVE_FEATURES_PER_BATCH,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
    FEATURE_GENERATION_SYSTEM_PROMPT,
    build_feature_generation_messages,
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
