"""Exceptions for rebuilt GEPA Jev scoring failures.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_jev_failure_stops.py -q
"""

from __future__ import annotations


class JevScoringFailed(RuntimeError):
    """Raised when Jev scoring exhausts retries and the job must stop."""

    def __init__(
        self,
        message: str,
        *,
        post_id: str | None = None,
        batch_idx: int | None = None,
    ) -> None:
        super().__init__(message)
        self.post_id = post_id
        self.batch_idx = batch_idx
