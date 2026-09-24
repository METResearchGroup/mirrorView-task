"""Tests for Jev retry helper."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from typesafe_sdk import TypeSafeAuthenticationError

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries import run_with_retries


class TestRunWithRetries:
    """Tests for run_with_retries."""

    def test_retries_then_returns(self) -> None:
        calls = {"count": 0}

        def fn() -> int:
            calls["count"] += 1
            if calls["count"] < 3:
                raise ValueError("temporary")
            return 7

        with patch("experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries.time.sleep"):
            result = run_with_retries(fn, max_extra_attempts=3)

        assert result == 7
        assert calls["count"] == 3

    def test_auth_error_fails_fast(self) -> None:
        calls = {"count": 0}

        def fn() -> int:
            calls["count"] += 1
            raise TypeSafeAuthenticationError(401, {}, httpx.Headers(), message="bad key")

        with patch("experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries.time.sleep") as sleep_mock:
            with pytest.raises(TypeSafeAuthenticationError):
                run_with_retries(fn)

        assert calls["count"] == 1
        sleep_mock.assert_not_called()
