"""Tests for Jev Noul instruction builders."""

from __future__ import annotations

from typesafe_sdk import Noul

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    build_noul_instruction,
    build_questions,
)


class TestBuildNoulInstruction:
    def test_pair_view_references_posts_slot(self) -> None:
        instruction = build_noul_instruction(3, "pair")

        assert instruction.startswith("Consider `posts[3]`. ")
        assert "posts[3]" in instruction
        assert "pair of posts" in instruction

    def test_original_view_references_single_post(self) -> None:
        instruction = build_noul_instruction(0, "original")

        assert instruction.startswith("Consider `posts[0]`. ")
        assert "posts[0]" in instruction
        assert "one political social media post" in instruction
        assert "pair" not in instruction.lower()


class TestBuildQuestions:
    def test_mirror_view_builds_post_questions(self) -> None:
        questions = build_questions(2, "mirror")

        assert set(questions) == {"post_0", "post_1"}
        for question_id, question in questions.items():
            index = int(question_id.split("_", maxsplit=1)[1])
            assert isinstance(question, Noul)
            assert question.instructions.startswith(f"Consider `posts[{index}]`. ")
