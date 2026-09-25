"""Tests for study-instruction scoring with post-only state."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import (
    score_batch_with_study_instruction,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    PAIR_TASK_INSTRUCTION,
    POSTS_STATE_KEY,
    render_posts_only_state,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.tests.conftest import (
    FakeTypeSafeClient,
    FakeUsage,
)


class TestScoreBatchWithStudyInstruction:
    """Tests for score_batch_with_study_instruction."""

    def test_pair_post_only_state_and_study_in_shared_instruction(self) -> None:
        post_only_state = render_posts_only_state("pair", "post-a", "post-b", "original")
        client = FakeTypeSafeClient(
            answers={0: 0.6},
            usage=FakeUsage(input_tokens=10, output_tokens=1),
        )
        study_text = "STUDY"

        score_batch_with_study_instruction(
            client,
            [post_only_state],
            "pair",
            study_instruction=study_text,
        )

        call = client.calls[0]
        assert "STUDY" not in call["state"][POSTS_STATE_KEY][0]
        post_instruction = call["questions"]["post_0"].instructions
        assert PAIR_TASK_INSTRUCTION in post_instruction
        assert post_instruction.startswith(f"Consider `{POSTS_STATE_KEY}[0]`. ")
        assert study_text in post_instruction
