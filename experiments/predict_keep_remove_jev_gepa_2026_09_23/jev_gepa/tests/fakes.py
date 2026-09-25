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
    _batch_call_index: int = 0

    def __call__(
        self,
        client: Any,
        state_texts: list[str],
        view: str,
        *,
        instruction: str | None = None,
    ) -> BatchResult:
        self.calls.append(
            {
                "client": client,
                "state_texts": list(state_texts),
                "view": view,
                "instruction": instruction,
            }
        )
        if self.raise_on_post_index is not None and len(state_texts) == 1:
            post_index = self._batch_call_index
            self._batch_call_index += 1
            if post_index == self.raise_on_post_index:
                raise ValueError(f"scorer failed for post index {post_index}")
        if self.raise_on_post_index is not None and len(state_texts) > 1:
            raise ValueError(f"scorer failed for batch size {len(state_texts)}")

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


@dataclass
class FakeReflectionLM:
    """Records reflection calls and returns a fixed instruction mutation."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    mutated_instruction: str = "mutated instruction text"

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append({"args": args, "kwargs": kwargs})
        return self.mutated_instruction
