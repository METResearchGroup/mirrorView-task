"""Call Jev once per request, with rate limiting and transient-error retries.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.scorer import JevScorer, build_jev_scorer, parse_response; print(JevScorer.__name__)"
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_typesafe import (
    ClassifierRequest,
    ClassifierResponse,
    TypeSafeClassifier,
)
from langchain_typesafe.client import (
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeInternalServerError,
    TypeSafeRateLimitError,
)

from shared.models.jev.constants import JEV_MODEL_ID, JEV_RETRY_BACKOFF_SECONDS
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
    raise NotImplementedError


class JevScorer:
    """Send one ``ClassifierRequest`` at a time. Safe to share across threads."""

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
        """Call Jev once, retrying only transient errors.

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
        raise NotImplementedError

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
        raise NotImplementedError


def build_jev_scorer(model_id: str = JEV_MODEL_ID) -> JevScorer:
    """Build the real scorer: pinned classifier, shared limiter, real clock."""
    raise NotImplementedError
