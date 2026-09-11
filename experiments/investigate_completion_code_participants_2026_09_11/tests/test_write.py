"""Tests for write_results_md()."""

from pathlib import Path

from experiments.investigate_completion_code_participants_2026_09_11.constants import (
    AssignmentRecord,
    COMPLETION_CODE,
    InvestigationResult,
    ParticipantFinding,
    SessionFile,
    SessionSummary,
)
from experiments.investigate_completion_code_participants_2026_09_11.write import (
    write_results_md,
)


def _finding() -> ParticipantFinding:
    return ParticipantFinding(
        prolific_id="671be80dd312fef1ab1d7c31",
        assignment=AssignmentRecord(
            prolific_id="671be80dd312fef1ab1d7c31",
            found=True,
            created_at="2026_09_10-23:24:32",
            study_iteration_id="mirrorview_2026_09_09",
            assignment_id="democrat-training_assisted-0614",
            political_party="democrat",
            condition="training_assisted",
            assignment_s3_key="precomputed_assignments/x.csv",
        ),
        session_files=(
            SessionFile(
                key="data/prolific/data_1.csv",
                last_modified="2026-09-10 23:35:10+00:00",
                size=100,
            ),
        ),
        session=SessionSummary(
            prolific_id="671be80dd312fef1ab1d7c31",
            n_rows=33,
            n_scored_moderation=20,
            unique_scored_posts=20,
            scored_post_ids=tuple(f"p{i}" for i in range(20)),
            decision_counts=(("keep", 15), ("remove", 5)),
            attention_check_passed=1,
            attention_check_selected="Q3|Q4|Q5|Q6",
            consented=1,
            party_group="democrat",
            condition="training_assisted",
            has_reflection=True,
            reflection_word_count=58,
            has_demographics=True,
            has_ideology=True,
            has_attitudes=True,
            time_elapsed_ms=691803.0,
            trial_index_max=32,
            is_complete=True,
        ),
        assigned_post_ids=tuple(f"p{i}" for i in range(20)),
        posts_match_assignment=True,
        recommendation="approve",
    )


class TestWriteResultsMd:
    """Tests for write_results_md()."""

    def test_names_completion_code_and_approve(self, tmp_path: Path) -> None:
        """Verifies the report names the completion code and the approve recommendation."""
        result = InvestigationResult(
            findings=(_finding(),),
            prolific_csv_count=1096,
            findings_s3_uri="s3://mirrorview-experimental-artifacts/experiments/investigate_completion_code_participants_2026_09_11/findings.json",
            findings_sha256="abc",
            results_path=tmp_path / "RESULTS.md",
        )

        path = write_results_md(result, tmp_path)
        text = path.read_text()

        assert COMPLETION_CODE in text
        assert "approve" in text
        assert "671be80dd312fef1ab1d7c31" in text
        assert "democrat-training_assisted-0614" in text
