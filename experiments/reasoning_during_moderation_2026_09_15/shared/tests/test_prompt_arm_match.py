"""Tests for planned_completion_fields() and criteria-only prompt insertion."""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment2.run import (
    planned_completion_fields,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    CLOSING_LINE,
    POST_1_LABEL,
    POST_2_LABEL,
    PROMPT_ARM_CRITERIA,
    QWEN_MODEL_ID,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.prompt import (
    render_prompt,
)

MATCHED_SEED = 123
ORIGINAL_TEXT = "original post"
MIRROR_TEXT = "mirror post"


class TestPromptArmMatch:
    """Tests for planned_completion_fields and criteria prompt insertion."""

    def test_copies_experiment1_pair_order_and_seed(self) -> None:
        """Verifies experiment 2 reuses experiment 1 roles, seed, and criteria arm."""
        cohort_row = {
            "post_id": "p1",
            "model_id": QWEN_MODEL_ID,
            "post_1_role": ROLE_ORIGINAL,
            "post_2_role": ROLE_MIRROR,
        }
        exp1_trace = {
            "post_id": "p1",
            "model_id": QWEN_MODEL_ID,
            "post_1_role": ROLE_MIRROR,
            "post_2_role": ROLE_ORIGINAL,
            "generation_seed": MATCHED_SEED,
        }
        expected_role = ROLE_MIRROR
        expected_seed = MATCHED_SEED

        result = planned_completion_fields(cohort_row, exp1_trace)

        assert result.post_1_role == expected_role
        assert result.generation_seed == expected_seed
        assert result.add_criteria is True
        assert result.prompt_arm == PROMPT_ARM_CRITERIA

    def test_criteria_addendum_is_only_inserted_block(self) -> None:
        """Verifies the addendum is the only difference versus the study prompt."""
        without_criteria = render_prompt(
            ORIGINAL_TEXT, MIRROR_TEXT, ROLE_ORIGINAL, False
        )
        with_criteria = render_prompt(
            ORIGINAL_TEXT, MIRROR_TEXT, ROLE_ORIGINAL, True
        )
        stripped = with_criteria.replace(KEEP_REMOVE_FEATURES_ADDENDUM, "", 1)

        assert KEEP_REMOVE_FEATURES_ADDENDUM in with_criteria
        assert stripped == without_criteria
        assert f"{POST_1_LABEL} {ORIGINAL_TEXT}" in with_criteria
        assert f"{POST_2_LABEL} {MIRROR_TEXT}" in with_criteria
        assert with_criteria.rstrip().endswith(CLOSING_LINE)
