"""Unified retry decorators for transient ingestion API errors."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import httpx
import prawcore.exceptions
import tweepy
from atproto_client.exceptions import (
    InvokeTimeoutError,
    NetworkError,
    RequestException,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
INITIAL_DELAY = 2.0
MAX_DELAY = 120.0


def make_retry_decorator(
    is_retryable_fn: Callable[[BaseException], bool],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Build a tenacity retry decorator for exceptions matching is_retryable_fn."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_delay, max=max_delay),
        retry=retry_if_exception(is_retryable_fn),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def is_retryable_bluesky_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError | httpx.RequestError):
        return True
    if isinstance(exc, InvokeTimeoutError | NetworkError):
        return True
    if isinstance(exc, RequestException):
        response = exc.response
        if response is None:
            return False
        return response.status_code == 429
    return False


def is_retryable_reddit_error(exc: BaseException) -> bool:
    if isinstance(exc, prawcore.exceptions.TooManyRequests):
        return True
    if isinstance(exc, prawcore.exceptions.ServerError):
        return True
    if isinstance(exc, prawcore.exceptions.RequestException):
        response = getattr(exc, "response", None)
        if response is None:
            return True
        return response.status_code in {429, 500, 502, 503, 504}
    return False


def is_retryable_twitter_error(exc: BaseException) -> bool:
    if isinstance(exc, tweepy.TooManyRequests):
        return True
    if isinstance(exc, tweepy.TwitterServerError):
        return True
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError | httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


def retry_bluesky_request(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry Bluesky page fetches on transient HTTP errors and 429 rate limits."""
    return make_retry_decorator(
        is_retryable_bluesky_error,
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
    )


def retry_reddit_request(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry Reddit fetches on transient HTTP errors and 429 rate limits."""
    return make_retry_decorator(
        is_retryable_reddit_error,
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
    )


def retry_twitter_request(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry Twitter fetches on transient HTTP errors and 429 rate limits."""
    return make_retry_decorator(
        is_retryable_twitter_error,
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
    )
