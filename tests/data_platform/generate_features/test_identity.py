from __future__ import annotations

from data_platform.generate_features.identity import identity_for_spec
from data_platform.generate_features.registry import FEATURE_REGISTRY
from lib.constants import DEFAULT_LLM_MODEL


class TestIdentityForSpec:
    """Tests for identity_for_spec()."""

    def test_llm_feature_uses_default_model_and_prompt_hash(self) -> None:
        """Given an LLM feature spec, when hashing identity, then model id and prompt hash are set."""
        spec = FEATURE_REGISTRY["is_political"]

        result = identity_for_spec(spec)

        assert result.model_id == DEFAULT_LLM_MODEL
        assert result.prompt_hash is not None
        assert len(result.prompt_hash) == 64

    def test_prompt_hash_changes_when_prompt_changes(self) -> None:
        """Given two different prompts, when hashing, then the hashes differ."""
        spec = FEATURE_REGISTRY["is_political"]
        other = FEATURE_REGISTRY["is_likely_spam"]

        first = identity_for_spec(spec)
        second = identity_for_spec(other)

        assert first.prompt_hash != second.prompt_hash

    def test_toxic_feature_uses_perspective_without_prompt_hash(self) -> None:
        """Given the Perspective feature, when hashing identity, then model id is perspective-api."""
        spec = FEATURE_REGISTRY["is_toxic_tiered"]

        result = identity_for_spec(spec)

        assert result.model_id == "perspective-api"
        assert result.prompt_hash is None
