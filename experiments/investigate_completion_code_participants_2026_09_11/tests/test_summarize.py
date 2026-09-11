"""Tests for summarize_session() and recommendation_for()."""

import pandas as pd

from experiments.investigate_completion_code_participants_2026_09_11.summarize import (
    recommendation_for,
    scored_moderation_frame,
    session_is_complete,
    summarize_session,
)


def _row(**overrides: object) -> dict[str, object]:
    row = {
        "trial_type": "instructions",
        "trial_index": 0,
        "time_elapsed": 1000,
        "post_id": "",
        "decision": "",
        "prolific_id": "pid_test",
        "consented": 1,
        "attention_check_passed": 1,
        "attention_check_selected": "Q3|Q4|Q5|Q6",
        "party_group": "democrat",
        "condition": "training_assisted",
        "phase1_pair_reflection_text": "",
        "age": "",
        "political_ideology": "",
        "attitude_reduce_abortion": "",
    }
    row.update(overrides)
    return row


def _complete_frame() -> pd.DataFrame:
    rows = [_row(trial_index=0)]
    for index in range(20):
        rows.append(
            _row(
                trial_type="moderation-trial",
                trial_index=index + 1,
                post_id=f"post-{index:02d}",
                decision="keep" if index < 15 else "remove",
                time_elapsed=2000 + index,
            )
        )
    rows.append(
        _row(
            trial_type="survey-html-form",
            trial_index=21,
            phase1_pair_reflection_text="I compared the pair and allowed both when the tone stayed civil.",
            time_elapsed=5000,
        )
    )
    rows.append(_row(trial_type="survey-html-form", trial_index=22, age=40, time_elapsed=6000))
    rows.append(
        _row(
            trial_type="survey-html-form",
            trial_index=23,
            political_ideology=2,
            time_elapsed=7000,
        )
    )
    rows.append(
        _row(
            trial_type="survey-html-form",
            trial_index=24,
            attitude_reduce_abortion=10,
            time_elapsed=8000,
        )
    )
    return pd.DataFrame(rows)


class TestScoredModerationFrame:
    """Tests for scored_moderation_frame()."""

    def test_drops_practice_trial_with_empty_post_id(self) -> None:
        """Verifies an empty post_id moderation row is not scored."""
        frame = pd.DataFrame(
            [
                _row(trial_type="moderation-trial", post_id="", decision="keep"),
                _row(trial_type="moderation-trial", post_id="post-00", decision="keep"),
            ]
        )

        result = scored_moderation_frame(frame)

        assert len(result) == 1
        assert result.iloc[0]["post_id"] == "post-00"


class TestSummarizeSession:
    """Tests for summarize_session()."""

    def test_complete_session_is_complete(self) -> None:
        """Verifies 20 scored posts plus end surveys count as complete."""
        result = summarize_session(_complete_frame(), "pid_test")

        assert result.n_scored_moderation == 20
        assert result.unique_scored_posts == 20
        assert result.has_reflection is True
        assert result.reflection_word_count == 12
        assert result.is_complete is True
        assert dict(result.decision_counts) == {"keep": 15, "remove": 5}

    def test_missing_trials_is_not_complete(self) -> None:
        """Verifies ten scored posts fail completeness."""
        frame = _complete_frame()
        drop_ids = {f"post-{index:02d}" for index in range(10, 20)}
        frame = frame[~frame["post_id"].astype(str).isin(drop_ids)].copy()

        result = summarize_session(frame, "pid_test")

        assert result.n_scored_moderation == 10
        assert result.is_complete is False


class TestSessionIsComplete:
    """Tests for session_is_complete()."""

    def test_requires_consent(self) -> None:
        """Verifies consented=0 fails completeness."""
        summary = summarize_session(_complete_frame(), "pid_test")
        expected = summary.__dict__.copy()
        expected["consented"] = 0
        expected["is_complete"] = False
        incomplete = type(summary)(**expected)

        result = session_is_complete(incomplete)

        assert result is False


class TestRecommendationFor:
    """Tests for recommendation_for()."""

    def test_approve_when_complete_and_posts_match(self) -> None:
        """Verifies a complete matching session is approve."""
        session = summarize_session(_complete_frame(), "pid_test")

        result = recommendation_for(
            assignment_found=True, session=session, posts_match=True
        )

        assert result == "approve"

    def test_no_saved_session_when_assigned_but_no_csv(self) -> None:
        """Verifies an assignment with no CSV is no_saved_session."""
        result = recommendation_for(
            assignment_found=True, session=None, posts_match=None
        )

        assert result == "no_saved_session"
