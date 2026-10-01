"""Typed result of one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.schemas import JevResult; print(JevResult.__name__)"
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class JevResult(BaseModel):
    """Yes-or-no probabilities, token usage, and request metadata from one Jev call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1)
    request_id: str | None
    nouls: dict[str, Annotated[float, Field(ge=0.0, le=1.0)]] = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)
    attempts: int = Field(ge=1)

    def noul(self, question_id: str) -> float:
        """Return P(yes) for one Noul question.

        Parameters
        ----------
        question_id
            Noul question ID requested on the classifier call.

        Returns
        -------
        float
            Probability of yes for ``question_id``.

        Raises
        ------
        KeyError
            When the result has no answer for ``question_id``.
        """
        return self.nouls[question_id]

    @property
    def total_tokens(self) -> int:
        """Input plus output tokens."""
        return self.input_tokens + self.output_tokens
