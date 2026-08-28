"""Google Perspective API client for toxicity scoring.

Run from the repo root:

    PYTHONPATH=. uv run python ml_tooling/perspective_api.py
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from lib.load_env_vars import EnvVarsContainer

P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger(__name__)

PERSPECTIVE_API_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
TOXICITY_ATTRIBUTE = "TOXICITY"

MAX_ATTEMPTS = 8
INITIAL_DELAY = 2.0
MAX_DELAY = 120.0
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})


def _is_retryable_perspective_error(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRYABLE_HTTP_STATUSES
    if isinstance(exc, urllib.error.URLError):
        return True
    return False


def retry_perspective_request(
    max_attempts: int = MAX_ATTEMPTS,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry Perspective API calls on transient HTTP errors and rate limits."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_delay, max=max_delay),
        retry=retry_if_exception(_is_retryable_perspective_error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _post_perspective_request(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@retry_perspective_request()
def _post_perspective_request_with_retry(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _post_perspective_request(url, payload)


def get_toxicity_prob(text: str) -> float:
    """Return the Perspective API toxicity probability for a single text string."""
    api_key = EnvVarsContainer.get_env_var("GOOGLE_API_KEY", required=True)
    payload = {
        "comment": {"text": text},
        "languages": ["en"],
        "requestedAttributes": {TOXICITY_ATTRIBUTE: {}},
    }
    url = f"{PERSPECTIVE_API_URL}?key={api_key}"

    try:
        body = _post_perspective_request_with_retry(url, payload)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Perspective API request failed with status {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Perspective API request failed: {exc.reason}") from exc

    try:
        return float(body["attributeScores"][TOXICITY_ATTRIBUTE]["summaryScore"]["value"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unexpected Perspective API response shape: {body}") from exc


if __name__ == "__main__":
    samples = [
        "Thanks for sharing this thoughtful update.",
        "You are an idiot and nobody likes you.",
    ]
    for text in samples:
        print(f"{get_toxicity_prob(text):.4f}  {text!r}")
