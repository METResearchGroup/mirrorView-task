"""Call Jev once per request, with rate limiting and transient-error retries.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.scorer import JevScorer, build_jev_scorer, parse_response; print(JevScorer.__name__)"
"""

from __future__ import annotations

import time
from collections.abc import Callable

from langchain_typesafe import (
    ClassifierRequest,
    ClassifierResponse,
    Noul,
    TypeSafeClassifier,
)
from langchain_typesafe.client import (
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeInternalServerError,
    TypeSafeRateLimitError,
)

from shared.models.jev.client import build_jev_classifier
from shared.models.jev.constants import (
    JEV_MAX_REQUESTS_PER_MINUTE,
    JEV_MODEL_ID,
    JEV_RETRY_BACKOFF_SECONDS,
)
from shared.models.jev.rate_limit import RequestStartLimiter
from shared.models.jev.schemas import JevResult

_RETRYABLE_ERRORS = (
    TypeSafeRateLimitError,
    TypeSafeInternalServerError,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
)


def parse_response(
    request: ClassifierRequest,
    response: ClassifierResponse,
    expected_model: str,
    latency_ms: float,
    attempts: int,
) -> JevResult:
    """Convert one classifier response into a ``JevResult``.

    Parameters
    ----------
    request
        Classifier input whose Noul question IDs must be answered.
    response
        Classifier response to validate and convert.
    expected_model
        Model ID the classifier was pinned to.
    latency_ms
        Elapsed time of the successful attempt, in milliseconds.
    attempts
        Number of attempts used, including the successful one.

    Returns
    -------
    JevResult
        Probabilities for the requested Noul questions, plus usage.

    Raises
    ------
    KeyError
        When a requested Noul question has no answer.
    ValueError
        When Jev answered with a model other than ``expected_model``.
    """
    if response.model != expected_model:
        raise ValueError(f"expected model {expected_model}, got {response.model}")
    noul_ids = [
        question_id
        for question_id, question in request["questions"].items()
        if isinstance(question, Noul)
    ]
    answers = response.nouls
    missing = [question_id for question_id in noul_ids if question_id not in answers]
    if missing:
        raise KeyError(f"missing Noul answers for {missing}")
    return JevResult(
        model=response.model,
        request_id=response.request_id,
        nouls={question_id: answers[question_id].noul for question_id in noul_ids},
        input_tokens=response.usage.input_tokens or 0,
        output_tokens=response.usage.output_tokens or 0,
        latency_ms=latency_ms,
        attempts=attempts,
    )


class JevScorer:
    """Send one ``ClassifierRequest`` at a time, and share one scorer across threads."""

    def __init__(
        self,
        classifier: TypeSafeClassifier,
        limiter: RequestStartLimiter,
        clock: Callable[[], float],
        sleep_fn: Callable[[float], None],
        backoff_seconds: tuple[float, ...] = JEV_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._classifier = classifier
        self._limiter = limiter
        self._clock = clock
        self._sleep_fn = sleep_fn
        self._backoff_seconds = backoff_seconds

    def score(self, request: ClassifierRequest) -> JevResult:
        """Send one request to Jev, and retry only after a transient error.

        Parameters
        ----------
        request
            Classifier input with state and questions.

        Returns
        -------
        JevResult
            Validated probabilities and usage from the accepted response.

        Raises
        ------
        TypeSafeAPIError
            Non-retryable API errors are raised at once. Retryable errors are
            raised after the last backoff.
        KeyError, ValueError
            From ``parse_response``. Never retried.
        """
        max_attempts = 1 + len(self._backoff_seconds)
        for attempt in range(1, max_attempts + 1):
            self._limiter.wait()
            started = self._clock()
            try:
                response = self._classifier.invoke(request)
            except _RETRYABLE_ERRORS as error:
                if attempt == max_attempts:
                    raise
                self._sleep_fn(self._retry_delay(error, attempt))
                continue
            latency_ms = (self._clock() - started) * 1000.0
            return parse_response(
                request,
                response,
                self._classifier.model,
                latency_ms,
                attempt,
            )
        raise AssertionError("unreachable")

    def _retry_delay(self, error: Exception, attempt: int) -> float:
        """Use the fixed backoff, or the server's retry-after when it is longer.

        Parameters
        ----------
        error
            Retryable error from the attempt that just failed.
        attempt
            One-based attempt number that just failed.

        Returns
        -------
        float
            Seconds to wait before the next attempt.
        """
        delay = self._backoff_seconds[attempt - 1]
        retry_after_ms = getattr(error, "retry_after_ms", None)
        if retry_after_ms is not None:
            delay = max(delay, retry_after_ms / 1000.0)
        return delay


def build_jev_scorer(model_id: str = JEV_MODEL_ID) -> JevScorer:
    """Build the scorer with the pinned classifier, a shared limiter, and ``time.perf_counter`` for latency.

    Parameters
    ----------
    model_id
        TypeSafe model ID to pin. Defaults to the shared Jev model constant.

    Returns
    -------
    JevScorer
        Scorer that uses the pinned classifier, the shared limiter, and ``time.perf_counter``.
    """
    limiter = RequestStartLimiter(
        JEV_MAX_REQUESTS_PER_MINUTE,
        time.monotonic,
        time.sleep,
    )
    return JevScorer(
        build_jev_classifier(model_id),
        limiter,
        time.perf_counter,
        time.sleep,
    )
