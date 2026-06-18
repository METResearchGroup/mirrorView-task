"""Batched Perspective API TOXICITY scorer."""

from __future__ import annotations

import asyncio
import json
from typing import Literal

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from tqdm import tqdm

from experiments.fetch_reddit_pushshift_dump_2026_06_15.api_budget import (
    api_calls_remaining,
    budget_exhausted,
    record_api_calls,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import (
    PERSPECTIVE_BATCH_SIZE,
    PERSPECTIVE_DELAY_SECONDS,
    PERSPECTIVE_MAX_RETRIES,
)
from experiments.fetch_reddit_pushshift_dump_2026_06_15.models import (
    CommentToScore,
    ToxicityScore,
)
from lib.load_env_vars import EnvVarsContainer


def get_google_client():
    return discovery.build(
        "commentanalyzer",
        "v1alpha1",
        developerKey=EnvVarsContainer.get_env_var("GOOGLE_API_KEY", required=True),
        discoveryServiceUrl=(
            "https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1"
        ),
        static_discovery=False,
    )


def create_perspective_request(text: str) -> dict:
    return {
        "comment": {"text": text},
        "languages": ["en"],
        "requestedAttributes": {"TOXICITY": {}},
    }


def _extract_toxicity(response: dict | None) -> dict | None:
    if response is None:
        return None
    if "error" in response:
        return None
    try:
        prob = response["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
    except (KeyError, TypeError):
        return None
    return {"prob_toxic": prob}


async def process_perspective_batch(requests: list[dict]) -> list[dict | None]:
    if not requests:
        return []

    original_len = len(requests)
    allowed = min(original_len, api_calls_remaining())
    if allowed == 0:
        return [None] * original_len

    requests_to_send = requests[:allowed]

    google_client = get_google_client()
    batch = google_client.new_batch_http_request()
    responses: list[dict | None] = []

    def callback(_request_id, response, exception):
        if exception is not None:
            responses.append(None)
            return
        response_obj = json.loads(json.dumps(response))
        if "error" in response_obj:
            responses.append(None)
            return
        responses.append(_extract_toxicity(response_obj))

    for request in requests_to_send:
        batch.add(google_client.comments().analyze(body=request), callback=callback)

    try:
        batch.execute()
        record_api_calls(len(requests_to_send))
    except HttpError:
        record_api_calls(len(requests_to_send))
        responses = [None] * allowed

    if len(responses) < allowed:
        responses.extend([None] * (allowed - len(responses)))
    if original_len > allowed:
        responses.extend([None] * (original_len - allowed))
    return responses


async def process_perspective_batch_with_retries(
    requests: list[dict],
    *,
    max_retries: int = PERSPECTIVE_MAX_RETRIES,
    initial_delay: float = 1.0,
    retry_strategy: Literal["batch", "individual"] = "individual",
) -> list[dict | None]:
    if retry_strategy not in ("batch", "individual"):
        raise ValueError(
            f"Invalid retry_strategy: {retry_strategy}. "
            "Must be either 'batch' or 'individual'."
        )

    if not requests:
        return []

    responses = await process_perspective_batch(requests)
    current_delay = initial_delay
    attempt = 1

    if retry_strategy == "batch":
        while attempt < max_retries and None in responses:
            await asyncio.sleep(current_delay)
            responses = await process_perspective_batch(requests)
            current_delay *= 2
            attempt += 1
    else:
        failed_indices = [i for i, response in enumerate(responses) if response is None]
        while failed_indices and attempt < max_retries:
            await asyncio.sleep(current_delay)
            retry_requests = [requests[i] for i in failed_indices]
            retry_responses = await process_perspective_batch(retry_requests)
            for original_idx, retry_response in zip(failed_indices, retry_responses):
                if retry_response is not None:
                    responses[original_idx] = retry_response
            failed_indices = [i for i, response in enumerate(responses) if response is None]
            current_delay *= 2
            attempt += 1

    return responses


def _chunk(items: list[CommentToScore], size: int) -> list[list[CommentToScore]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _run_batch_scoring_async(
    comments: list[CommentToScore],
) -> list[ToxicityScore]:
    batches = _chunk(comments, PERSPECTIVE_BATCH_SIZE)
    all_scores: list[ToxicityScore] = []

    progress = tqdm(
        batches,
        desc="Perspective inference",
        unit="batch",
        total=len(batches),
    )
    for batch_index, batch in enumerate(progress):
        if budget_exhausted():
            for remaining in batches[batch_index:]:
                for item in remaining:
                    all_scores.append(
                        ToxicityScore(
                            comment_id=item.comment_id,
                            prob_toxic=None,
                            was_successfully_labeled=False,
                            reason="api_budget_exhausted",
                        )
                    )
            break

        requests = [create_perspective_request(item.text) for item in batch]
        responses = await process_perspective_batch_with_retries(
            requests,
            retry_strategy="individual",
        )
        for item, response in zip(batch, responses):
            if response is None:
                all_scores.append(
                    ToxicityScore(
                        comment_id=item.comment_id,
                        prob_toxic=None,
                        was_successfully_labeled=False,
                        reason="perspective_api_failed",
                    )
                )
            else:
                all_scores.append(
                    ToxicityScore(
                        comment_id=item.comment_id,
                        prob_toxic=response["prob_toxic"],
                        was_successfully_labeled=True,
                    )
                )
        if progress.n < progress.total and not budget_exhausted():
            await asyncio.sleep(PERSPECTIVE_DELAY_SECONDS)

    return all_scores


def run_batch_scoring(comments: list[CommentToScore]) -> list[ToxicityScore]:
    """Score comments in batches with tqdm progress and individual retries."""

    if not comments:
        return []
    return asyncio.run(_run_batch_scoring_async(comments))
