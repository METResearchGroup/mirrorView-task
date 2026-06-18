"""Unit tests for session API call budget."""

from experiments.fetch_reddit_pushshift_dump_2026_06_15 import api_budget
from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import MAX_SESSION_API_CALLS


def test_record_api_calls_respects_session_cap():
    api_budget.reset_session_budget()
    api_budget.record_api_calls(40_000)
    assert api_budget.api_calls_used() == 40_000
    assert api_budget.api_calls_remaining() == MAX_SESSION_API_CALLS - 40_000
    api_budget.record_api_calls(MAX_SESSION_API_CALLS)
    assert api_budget.api_calls_used() == MAX_SESSION_API_CALLS
    assert api_budget.budget_exhausted() is True
    assert api_budget.grant_api_calls(10) == 0
