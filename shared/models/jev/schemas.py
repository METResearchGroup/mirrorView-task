"""Typed result of one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.schemas import JevResult; print(JevResult.__name__)"
"""

from __future__ import annotations


class JevResult:
    """Noul probabilities, usage, and request metadata from one Jev call."""

    def noul(self, question_id: str) -> float:
        """Return P(yes) for one Noul question."""
        raise NotImplementedError

    @property
    def total_tokens(self) -> int:
        """Input plus output tokens."""
        raise NotImplementedError
