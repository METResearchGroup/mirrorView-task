"""Tests for request-start rate limiter."""

from __future__ import annotations

from unittest.mock import patch

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import (
    WINDOW_SECONDS,
    RequestStartLimiter,
)


class TestRequestStartLimiter:
    """Tests for RequestStartLimiter."""

    def test_third_wait_blocks_until_window_slides(self) -> None:
        monotonic_values = iter([0.0, 0.0, 0.0, WINDOW_SECONDS])
        sleep_calls: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        limiter = RequestStartLimiter(max_starts_per_minute=2)
        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter.time.monotonic",
            side_effect=lambda: next(monotonic_values),
        ), patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter.time.sleep",
            side_effect=fake_sleep,
        ):
            limiter.wait()
            limiter.wait()
            limiter.wait()

        assert sleep_calls == [WINDOW_SECONDS]
