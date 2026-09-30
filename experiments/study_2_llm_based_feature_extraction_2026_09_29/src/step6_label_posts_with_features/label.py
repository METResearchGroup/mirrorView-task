"""Label pairs with Jev, with retries, resume, and dead letters."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    JEV_RETRY_BACKOFF_SECONDS,
    MAX_FEATURES_PER_JEV_REQUEST,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.jev import (
    JevScorer,
    RequestStartLimiter,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step6_label_posts_with_features.prompt import (
    render_feature_instruction,
    render_pair_state,
)


@dataclass(frozen=True)
class PairLabelResult:
    """One finished pair, including token use and how many tries it took."""

    post_id: str
    probabilities: dict[str, float]
    input_tokens: int
    output_tokens: int
    latency_ms: float
    n_requests: int
    attempts: int


def chunk_feature_keys(keys: list[str], max_per_request: int) -> list[list[str]]:
    """Split sorted feature keys into request-sized chunks.

    Parameters
    ----------
    keys
        Feature keys in the order they should be sent.
    max_per_request
        Maximum questions in one Jev request.

    Returns
    -------
    list[list[str]]
        Contiguous chunks. The last chunk may be shorter.
    """
    if max_per_request <= 0:
        raise ValueError("max_per_request must be positive")
    return [keys[index : index + max_per_request] for index in range(0, len(keys), max_per_request)]


def features_sha256(label_to_detail: dict[str, dict[str, str]]) -> str:
    """Hash the feature list so a later edit relabels every pair.

    Parameters
    ----------
    label_to_detail
        Approved or draft feature mapping.

    Returns
    -------
    str
        SHA-256 hex digest of the JSON object with sorted keys.
    """
    payload = json.dumps(label_to_detail, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def label_pair(
    scorer: JevScorer,
    pair: pd.Series,
    label_to_detail: dict[str, dict[str, str]],
    limiter: RequestStartLimiter,
    sleep_fn: Callable[[float], None],
) -> PairLabelResult:
    """Score one pair, retrying the whole pair up to three more times.

    Parameters
    ----------
    scorer
        Jev scorer. Callers should use one scorer per thread.
    pair
        Row with ``post_id``, ``original_text``, and ``mirror_text``.
    label_to_detail
        Feature key to name and description.
    limiter
        Shared request-start limiter.
    sleep_fn
        Sleep used between retries.

    Returns
    -------
    PairLabelResult
        Probabilities for every feature key.

    Raises
    ------
    Exception
        When every attempt fails. The last error is raised.
    """
    keys = sorted(label_to_detail)
    chunks = chunk_feature_keys(keys, MAX_FEATURES_PER_JEV_REQUEST)
    state = render_pair_state(str(pair["original_text"]), str(pair["mirror_text"]))
    last_error: Exception | None = None
    for attempt_index, backoff in enumerate((0.0, *JEV_RETRY_BACKOFF_SECONDS)):
        if backoff:
            sleep_fn(backoff)
        try:
            probabilities: dict[str, float] = {}
            input_tokens = 0
            output_tokens = 0
            latency_ms = 0.0
            for chunk in chunks:
                limiter.wait()
                instructions = {
                    key: render_feature_instruction(label_to_detail[key]) for key in chunk
                }
                response = scorer.score(state, instructions)
                probabilities.update(response.probabilities)
                input_tokens += response.input_tokens
                output_tokens += response.output_tokens
                latency_ms += response.latency_ms
            return PairLabelResult(
                post_id=str(pair["post_id"]),
                probabilities=probabilities,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                n_requests=len(chunks),
                attempts=attempt_index + 1,
            )
        except Exception as error:  # noqa: BLE001
            last_error = error
    assert last_error is not None
    raise last_error


def labeled_post_ids(predictions_path: Path, sha: str) -> set[str]:
    """Return post ids already labeled with the current feature-list hash.

    Parameters
    ----------
    predictions_path
        JSONL predictions file. Missing file means nothing is labeled.
    sha
        Current ``features_sha256`` value.

    Returns
    -------
    set[str]
        Post ids whose line matches ``sha``.
    """
    if not predictions_path.is_file():
        return set()
    labeled: set[str] = set()
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("features_sha256") == sha:
            labeled.add(str(row["post_id"]))
    return labeled


def run_labeling(
    pairs: pd.DataFrame,
    scorer_factory: Callable[[], JevScorer],
    label_to_detail: dict[str, dict[str, str]],
    predictions_path: Path,
    deadletter_path: Path,
    limiter: RequestStartLimiter,
    sleep_fn: Callable[[float], None],
    max_workers: int,
) -> list[PairLabelResult]:
    """Label pending pairs and append each result as it finishes.

    Parameters
    ----------
    pairs
        Pairs to consider, with ``post_id``.
    scorer_factory
        Builds one Jev scorer. Called once per worker thread.
    label_to_detail
        Feature list to score.
    predictions_path
        JSONL file of finished pairs. Created if missing.
    deadletter_path
        JSONL file of pairs that exhausted retries.
    limiter
        Shared start limiter.
    sleep_fn
        Sleep used between retries.
    max_workers
        Thread pool size.

    Returns
    -------
    list[PairLabelResult]
        Results written during this call. Already labeled pairs are skipped.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sha = features_sha256(label_to_detail)
    done = labeled_post_ids(predictions_path, sha)
    pending = pairs.loc[~pairs["post_id"].astype(str).isin(done)]
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    deadletter_path.parent.mkdir(parents=True, exist_ok=True)
    write_lock = threading.Lock()
    local = threading.local()

    def _scorer() -> JevScorer:
        if not hasattr(local, "scorer"):
            local.scorer = scorer_factory()
        return local.scorer

    def _work(row: pd.Series) -> PairLabelResult | None:
        try:
            result = label_pair(_scorer(), row, label_to_detail, limiter, sleep_fn)
        except Exception as error:  # noqa: BLE001
            record = {
                "post_id": str(row["post_id"]),
                "features_sha256": sha,
                "error": str(error),
                "attempts": 1 + len(JEV_RETRY_BACKOFF_SECONDS),
            }
            with write_lock:
                with deadletter_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return None
        record = {
            "post_id": result.post_id,
            "features_sha256": sha,
            "probabilities": result.probabilities,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "latency_ms": result.latency_ms,
            "n_requests": result.n_requests,
            "attempts": result.attempts,
        }
        with write_lock:
            with predictions_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return result

    if pending.empty:
        return []
    results: list[PairLabelResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_work, row) for _, row in pending.iterrows()]
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
    return results
