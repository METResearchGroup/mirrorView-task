"""Mocked Perspective API batch scoring tests."""

from unittest.mock import AsyncMock, patch

from experiments.fetch_reddit_pushshift_dump_2026_06_15 import api_budget
from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import CommentToScore
from experiments.fetch_reddit_pushshift_dump_2026_06_15.perspective import run_batch_scoring


@patch(
    "experiments.fetch_reddit_pushshift_dump_2026_06_15.perspective.process_perspective_batch_with_retries",
    new_callable=AsyncMock,
)
def test_run_batch_scoring_preserves_order(mock_retry):
    api_budget.reset_session_budget()
    mock_retry.return_value = [
        {"prob_toxic": 0.9},
        None,
    ]
    comments = [
        CommentToScore(comment_id="a", text="first comment long enough"),
        CommentToScore(comment_id="b", text="second comment long enough"),
    ]
    scores = run_batch_scoring(comments)
    assert len(scores) == 2
    assert scores[0].comment_id == "a"
    assert scores[0].prob_toxic == 0.9
    assert scores[0].was_successfully_labeled is True
    assert scores[1].comment_id == "b"
    assert scores[1].was_successfully_labeled is False
