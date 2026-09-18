"""Score one jsPsych session CSV for completion."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from experiments.investigate_completion_code_participants_2026_09_11.constants import (
    AGE_COLUMN,
    ATTENTION_PASSED_COLUMN,
    ATTENTION_SELECTED_COLUMN,
    ATTITUDE_COLUMN,
    CONDITION_COLUMN,
    CONSENTED_COLUMN,
    DECISION_COLUMN,
    EXPECTED_SCORED_TRIALS,
    IDEOLOGY_COLUMN,
    MODERATION_TRIAL_TYPE,
    PARTY_GROUP_COLUMN,
    POST_ID_COLUMN,
    PROLIFIC_ID_COLUMN,
    REFLECTION_COLUMN,
    SessionSummary,
    TIME_ELAPSED_COLUMN,
    TRIAL_INDEX_COLUMN,
    TRIAL_TYPE_COLUMN,
)


def scored_moderation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return moderation rows with a non-empty post id (excludes the practice trial)."""
    if frame.empty:
        return frame
    trial_type = frame[TRIAL_TYPE_COLUMN].astype(str)
    post_id = frame[POST_ID_COLUMN].fillna("").astype(str).str.strip()
    mask = (trial_type == MODERATION_TRIAL_TYPE) & (post_id != "")
    return frame.loc[mask].copy()


def summarize_session(frame: pd.DataFrame, prolific_id: str) -> SessionSummary:
    """Build a completeness summary for one participant CSV."""
    scored = scored_moderation_frame(frame)
    scored_ids = tuple(
        scored[POST_ID_COLUMN].astype(str).str.strip().tolist()
    )
    decisions = scored[DECISION_COLUMN].fillna("").astype(str).str.strip()
    decision_counts = tuple(sorted(Counter(decisions.tolist()).items()))
    reflection_text = _first_nonempty_str(frame, REFLECTION_COLUMN)
    summary_without_complete = SessionSummary(
        prolific_id=prolific_id,
        n_rows=len(frame),
        n_scored_moderation=len(scored),
        unique_scored_posts=len(set(scored_ids)),
        scored_post_ids=scored_ids,
        decision_counts=decision_counts,
        attention_check_passed=_first_int(frame, ATTENTION_PASSED_COLUMN),
        attention_check_selected=_first_nonempty_str(frame, ATTENTION_SELECTED_COLUMN),
        consented=_first_int(frame, CONSENTED_COLUMN),
        party_group=_first_nonempty_str(frame, PARTY_GROUP_COLUMN),
        condition=_first_nonempty_str(frame, CONDITION_COLUMN),
        has_reflection=reflection_text is not None,
        reflection_word_count=_word_count(reflection_text),
        has_demographics=_has_nonempty(frame, AGE_COLUMN),
        has_ideology=_has_nonempty(frame, IDEOLOGY_COLUMN),
        has_attitudes=_has_nonempty(frame, ATTITUDE_COLUMN),
        time_elapsed_ms=_max_float(frame, TIME_ELAPSED_COLUMN),
        trial_index_max=_max_int(frame, TRIAL_INDEX_COLUMN),
        is_complete=False,
    )
    return SessionSummary(
        **{
            **summary_without_complete.__dict__,
            "is_complete": session_is_complete(summary_without_complete),
        }
    )


def session_is_complete(summary: SessionSummary) -> bool:
    """Return True when the session has 20 scored trials and the end surveys."""
    all_scored_have_decisions = (
        sum(count for decision, count in summary.decision_counts if decision)
        == EXPECTED_SCORED_TRIALS
    )
    return (
        summary.n_scored_moderation == EXPECTED_SCORED_TRIALS
        and summary.unique_scored_posts == EXPECTED_SCORED_TRIALS
        and all_scored_have_decisions
        and summary.consented == 1
        and summary.attention_check_passed is not None
        and summary.has_reflection
        and summary.has_demographics
        and summary.has_ideology
        and summary.has_attitudes
    )


def recommendation_for(
    *,
    assignment_found: bool,
    session: SessionSummary | None,
    posts_match: bool | None,
) -> str:
    """Return approve, incomplete, or no_saved_session."""
    if session is None:
        return "no_saved_session" if assignment_found else "no_record"
    if session.is_complete and posts_match:
        return "approve"
    if session.is_complete and posts_match is None:
        return "approve"
    return "incomplete"


def prolific_id_in_frame(frame: pd.DataFrame, prolific_id: str) -> bool:
    """Return True when any row has this prolific id."""
    if PROLIFIC_ID_COLUMN not in frame.columns:
        return False
    values = frame[PROLIFIC_ID_COLUMN].fillna("").astype(str)
    return bool((values == prolific_id).any())


def _first_nonempty_str(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame.columns:
        return None
    values = frame[column].dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return None
    return str(values.iloc[0])


def _first_int(frame: pd.DataFrame, column: str) -> int | None:
    if column not in frame.columns:
        return None
    values = frame[column].dropna()
    if values.empty:
        return None
    return int(values.iloc[0])


def _has_nonempty(frame: pd.DataFrame, column: str) -> bool:
    return _first_nonempty_str(frame, column) is not None


def _max_float(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns or frame[column].dropna().empty:
        return None
    return float(frame[column].max())


def _max_int(frame: pd.DataFrame, column: str) -> int | None:
    if column not in frame.columns or frame[column].dropna().empty:
        return None
    return int(frame[column].max())


def _word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(text.split())
