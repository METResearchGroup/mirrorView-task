"""Tests for candidate proposal guards."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    MAX_OPTIMIZED_COMPONENT_CHARS,
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.guards import (
    check_candidate_guards,
)


class TestGuards:
    """Tests for check_candidate_guards."""

    def test_length_cap_rejects_long_study_instruction(self) -> None:
        """Study instruction over 4000 characters is rejected as length_cap."""
        candidate = {STUDY_COMPONENT_KEY: "x" * (MAX_OPTIMIZED_COMPONENT_CHARS + 1)}
        result = check_candidate_guards(candidate, train_post_texts=[])
        assert result.ok is False
        assert result.reason == "length_cap"

    def test_train_substring_rejects_memorized_quote(self) -> None:
        """40+ character train substring in candidate triggers train_substring."""
        unique = "UNIQUE40CHARSUBSTRINGXXXXXXXXXXXXXXXXXXX"
        assert len(unique) >= 40
        train_texts = [f"prefix {unique} suffix"]
        candidate = {STUDY_COMPONENT_KEY: f"instruction contains {unique} inside"}
        result = check_candidate_guards(candidate, train_post_texts=train_texts)
        assert result.ok is False
        assert result.reason == "train_substring"
