"""Test doubles for rebuilt Jev GEPA adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import BatchResult


@dataclass
class FakeStudyFlipBatchScorer:
    """Callable matching score_batch_with_study_instruction."""

    probabilities_by_batch: list[list[float]] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    _batch_call_index: int = 0

    def __call__(
        self,
        client: Any,
        state_texts: list[str],
        view: str,
        *,
        study_instruction: str,
        task_instruction: str | None = None,
    ) -> BatchResult:
        self.calls.append(
            {
                "client": client,
                "state_texts": list(state_texts),
                "view": view,
                "study_instruction": study_instruction,
                "task_instruction": task_instruction,
            }
        )
        if self.probabilities_by_batch is None:
            probabilities = [0.5 for _ in state_texts]
        else:
            if self._batch_call_index >= len(self.probabilities_by_batch):
                raise IndexError("no probabilities configured for batch call")
            probabilities = list(self.probabilities_by_batch[self._batch_call_index])
            if len(probabilities) != len(state_texts):
                raise ValueError("probability count does not match batch size")
            self._batch_call_index += 1
        return BatchResult(
            probabilities=probabilities,
            latency_ms=1.0,
            input_tokens=10,
            output_tokens=5,
            model_version="fake-jev",
        )
