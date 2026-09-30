"""Jev client wrapper for Study 2 feature labeling."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    JEV_MODEL_ID,
    JEV_REQUEST_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class JevResponse:
    """Probabilities and usage from one Jev request."""

    probabilities: dict[str, float]
    input_tokens: int
    output_tokens: int
    latency_ms: float


class JevScorer:
    """Score one pair against a set of feature questions."""

    def __init__(
        self,
        client: Any,
        question_factory: Callable[[str], Any],
        clock: Callable[[], float],
    ) -> None:
        self._client = client
        self._question_factory = question_factory
        self._clock = clock

    def score(self, state: dict[str, str], instructions: dict[str, str]) -> JevResponse:
        """Call Jev once and return one probability per question id.

        Parameters
        ----------
        state
            Mapping passed as the ``state`` argument. This experiment uses one
            key, ``pair``.
        instructions
            Question id to Noul instruction text.

        Returns
        -------
        JevResponse
            Probabilities in ``[0, 1]`` plus token counts and latency.

        Raises
        ------
        KeyError
            When Jev omits a requested question id.
        ValueError
            When a probability is outside 0 to 1.
        """
        questions = {
            question_id: self._question_factory(text)
            for question_id, text in instructions.items()
        }
        started = self._clock()
        response = self._client.system_one(
            state=state,
            questions=questions,
            model=JEV_MODEL_ID,
        )
        latency_ms = (self._clock() - started) * 1000.0
        probabilities: dict[str, float] = {}
        for question_id in instructions:
            answer = response.answers.get(question_id)
            if answer is None:
                raise KeyError(f"missing answer for {question_id}")
            value = float(answer.noul)
            if value < 0.0 or value > 1.0:
                raise ValueError(f"probability outside 0 to 1 for {question_id}: {value}")
            probabilities[question_id] = value
        usage = response.usage
        return JevResponse(
            probabilities=probabilities,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        )


def build_jev_scorer(api_key: str) -> JevScorer:
    """Build a scorer with the TypeSafe client imported inside this function.

    Parameters
    ----------
    api_key
        TypeSafe API key. Not logged.

    Returns
    -------
    JevScorer
        Client configured with no SDK retries and the experiment timeout.
    """
    from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

    client = TypeSafeClient(
        api_key=api_key,
        model=JEV_MODEL_ID,
        retry=RetryPolicy(max_retries=0),
        timeout=JEV_REQUEST_TIMEOUT_SECONDS,
    )
    return JevScorer(
        client=client,
        question_factory=lambda text: Noul(instructions=text),
        clock=time.perf_counter,
    )


class RequestStartLimiter:
    """Allow at most a fixed number of request starts per minute."""

    def __init__(
        self,
        max_per_minute: int,
        clock: Callable[[], float],
        sleep_fn: Callable[[float], None],
    ) -> None:
        if max_per_minute <= 0:
            raise ValueError("max_per_minute must be positive")
        self._max_per_minute = max_per_minute
        self._clock = clock
        self._sleep_fn = sleep_fn
        self._lock = threading.Lock()
        self._start_times: list[float] = []

    def wait(self) -> None:
        """Block until another request is allowed to start."""
        while True:
            with self._lock:
                now = self._clock()
                cutoff = now - 60.0
                self._start_times = [stamp for stamp in self._start_times if stamp > cutoff]
                if len(self._start_times) < self._max_per_minute:
                    self._start_times.append(now)
                    return
                sleep_seconds = self._start_times[0] + 60.0 - now
            if sleep_seconds > 0:
                self._sleep_fn(sleep_seconds)
