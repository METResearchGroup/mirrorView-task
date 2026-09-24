"""Test doubles for Jev GEPA adapter and optimize runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import BatchResult


@dataclass
class FakeJevBatchScorer:
    """Callable matching score_batch; records instruction and returns fixed probabilities."""

    probabilities_by_batch: list[list[float]] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    raise_on_post_index: int | None = None

    def __call__(
        self,
        client: Any,
        state_texts: list[str],
        view: str,
        *,
        instruction: str | None = None,
    ) -> BatchResult:
        raise NotImplementedError


@dataclass
class FakeReflectionLM:
    """Records reflection calls and returns a fixed instruction mutation."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    mutated_instruction: str = "mutated instruction text"

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError
