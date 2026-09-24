"""Batched Jev scorer with rate limiting, retries, resume, and smoke CLI.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py --smoke --limit 100 --view pair
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse
import hashlib
import json
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel
from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import latency, pricing
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import (
    POSTS_STATE_KEY,
    QUESTION_ID_PREFIX,
    VIEW_MIRROR,
    VIEW_ORIGINAL,
    VIEW_PAIR,
    build_noul_instruction,
    build_questions,
    render_state_text,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries import AUTH_ERROR_TYPES, run_with_retries
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets import get_jev_api_key

JEV_MODEL_ID = "jev-1.13.0"
BATCH_SIZE = 10
WORKER_THREADS = 8
MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT = 1000
MAX_EXTRA_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
REQUEST_TIMEOUT_SECONDS = 120.0
SMOKE_SEED = 20260924
SMOKE_LIMIT_DEFAULT = 100

PREDICTIONS_FILENAME = "predictions.jsonl"
REQUESTS_FILENAME = "requests.jsonl"
DEADLETTER_FILENAME = "deadletter.jsonl"
SMOKE_SUMMARY_FILENAME = "smoke_summary.json"

COHORT_PARQUET = (
    _REPO_ROOT
    / "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet"
)
VALID_VIEWS = (VIEW_PAIR, VIEW_ORIGINAL, VIEW_MIRROR)


class PostTask(BaseModel):
    """One post queued for Jev scoring with rendered state text and gold label."""

    post_id: str
    state_text: str
    gold_label: int


class BatchResult(BaseModel):
    """Per-batch Jev response with remove probabilities and token usage."""

    probabilities: list[float]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model_version: str


class PostPrediction(BaseModel):
    """Serialized per-post prediction with latency, cost, and token attribution."""

    post_id: str
    view: str
    gold_label: int
    probability_remove: float
    instruction_sha256: str | None = None
    batch_size: int
    request_index: int
    position_in_request: int
    n_posts_in_request: int
    request_latency_ms: float
    per_post_latency_ms: float
    request_input_tokens: int
    request_output_tokens: int
    per_post_input_tokens: float
    per_post_output_tokens: float
    estimated_cost_usd: float
    model_version: str
    attempts: int


class SmokeSummary(BaseModel):
    """Aggregate smoke-run stats for latency, cost, and token usage."""

    view: str
    add_criteria: bool
    n_posts: int
    n_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    latency_ms_p50: float
    latency_ms_p90: float
    latency_ms_p99: float
    per_post_latency_ms_p50: float
    per_post_latency_ms_p90: float
    per_post_latency_ms_p99: float


@dataclass(frozen=True)
class RequestRecord:
    """Audit record for one Jev API request during a scoring pass."""

    request_id: str
    ablation_id: str
    batch_index: int
    post_ids: list[str]
    n_posts: int
    attempt: int
    status: str
    error_type: str | None
    started_at_utc: str
    latency_ms: float
    latency_per_post_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model: str
    instruction_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping of request audit fields."""
        return {
            "request_id": self.request_id,
            "ablation_id": self.ablation_id,
            "batch_index": self.batch_index,
            "post_ids": self.post_ids,
            "n_posts": self.n_posts,
            "attempt": self.attempt,
            "status": self.status,
            "error_type": self.error_type,
            "started_at_utc": self.started_at_utc,
            "latency_ms": self.latency_ms,
            "latency_per_post_ms": self.latency_per_post_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "model": self.model,
            "instruction_sha256": self.instruction_sha256,
        }


@dataclass(frozen=True)
class BatchWorkResult:
    """Predictions and request audit record produced from one scored batch."""

    batch_index: int
    predictions: list[PostPrediction]
    request_record: RequestRecord


def build_client(api_key: str) -> TypeSafeClient:
    """RetryPolicy(max_retries=0), timeout REQUEST_TIMEOUT_SECONDS, model JEV_MODEL_ID."""
    return TypeSafeClient(
        api_key=api_key,
        model=JEV_MODEL_ID,
        retry=RetryPolicy(max_retries=0),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def _build_questions_with_instruction(
    n_posts: int,
    view: str,
    instruction: str,
) -> dict[str, Noul]:
    return {
        f"{QUESTION_ID_PREFIX}{index}": Noul(
            instructions=f"Consider `{POSTS_STATE_KEY}[{index}]`. {instruction}"
        )
        for index in range(n_posts)
    }


def _effective_instruction_text(instruction: str | None, view: str) -> str:
    if instruction is not None:
        return instruction
    return build_noul_instruction(0, view)


def instruction_sha256(instruction: str | None, view: str) -> str:
    """Return SHA-256 hex digest of the effective instruction text for a view."""
    text = _effective_instruction_text(instruction, view)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def score_batch(
    client: TypeSafeClient,
    state_texts: list[str],
    view: str,
    *,
    instruction: str | None = None,
) -> BatchResult:
    """Score a batch via client.system_one; answer.noul is P(remove)."""
    state = {POSTS_STATE_KEY: list(state_texts)}
    if instruction is None:
        questions = build_questions(len(state_texts), view)
    else:
        questions = _build_questions_with_instruction(len(state_texts), view, instruction)

    @latency.timed
    def _call() -> Any:
        return client.system_one(state=state, questions=questions, model=JEV_MODEL_ID)

    response, latency_ms = _call()
    probabilities: list[float] = []
    for index in range(len(state_texts)):
        question_id = f"{QUESTION_ID_PREFIX}{index}"
        answer = response.answers.get(question_id)
        if answer is None:
            raise KeyError(f"missing answer for {question_id}")
        probabilities.append(float(answer.noul))

    input_tokens = int(response.usage.input_tokens or 0)
    output_tokens = int(response.usage.output_tokens or 0)
    model_version = str(getattr(response, "model", JEV_MODEL_ID) or JEV_MODEL_ID)
    return BatchResult(
        probabilities=probabilities,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_version=model_version,
    )


def make_batches(tasks: list[PostTask], batch_size: int = BATCH_SIZE) -> list[list[PostTask]]:
    """Partition post tasks into fixed-size batches for Jev scoring."""
    return [tasks[index : index + batch_size] for index in range(0, len(tasks), batch_size)]


def seen_post_ids(
    predictions_path: Path,
    *,
    instruction: str | None,
    view: str,
) -> set[str]:
    """Resume: return post_ids already scored for the current instruction.

    Legacy prediction rows without ``instruction_sha256`` are treated as matching
    only when ``instruction`` is ``None`` (seed / baseline runs).
    """
    if not predictions_path.is_file():
        return set()
    expected_hash = instruction_sha256(instruction, view)
    seen: set[str] = set()
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            record_hash = payload.get("instruction_sha256")
            if record_hash is None:
                if instruction is None:
                    seen.add(str(payload["post_id"]))
            elif record_hash == expected_hash:
                seen.add(str(payload["post_id"]))
    return seen


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _build_predictions(
    batch: list[PostTask],
    batch_index: int,
    view: str,
    batch_result: BatchResult,
    attempts: int,
    instruction_hash: str,
) -> list[PostPrediction]:
    n_posts = len(batch)
    per_post_latency_ms = batch_result.latency_ms / n_posts
    per_post_input_tokens = batch_result.input_tokens / n_posts
    per_post_output_tokens = batch_result.output_tokens / n_posts
    estimated_cost_usd = pricing.estimate_jev_cost_usd(
        batch_result.input_tokens,
        batch_result.output_tokens,
    )
    predictions: list[PostPrediction] = []
    for position, (task, probability) in enumerate(zip(batch, batch_result.probabilities)):
        predictions.append(
            PostPrediction(
                post_id=task.post_id,
                view=view,
                gold_label=task.gold_label,
                probability_remove=probability,
                batch_size=BATCH_SIZE,
                request_index=batch_index,
                position_in_request=position,
                n_posts_in_request=n_posts,
                request_latency_ms=batch_result.latency_ms,
                per_post_latency_ms=per_post_latency_ms,
                request_input_tokens=batch_result.input_tokens,
                request_output_tokens=batch_result.output_tokens,
                per_post_input_tokens=per_post_input_tokens,
                per_post_output_tokens=per_post_output_tokens,
                estimated_cost_usd=estimated_cost_usd / n_posts,
                model_version=batch_result.model_version,
                attempts=attempts,
                instruction_sha256=instruction_hash,
            )
        )
    return predictions


def _make_request_record(
    *,
    ablation_id: str,
    view: str,
    batch_index: int,
    batch: list[PostTask],
    attempt: int,
    status: str,
    error_type: str | None,
    started_at_utc: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    instruction_hash: str,
) -> RequestRecord:
    n_posts = len(batch)
    latency_per_post_ms = latency_ms / n_posts if n_posts else 0.0
    request_key = ablation_id or view
    return RequestRecord(
        request_id=f"{request_key}:{batch_index}:{attempt}",
        ablation_id=ablation_id,
        batch_index=batch_index,
        post_ids=[task.post_id for task in batch],
        n_posts=n_posts,
        attempt=attempt,
        status=status,
        error_type=error_type,
        started_at_utc=started_at_utc,
        latency_ms=latency_ms,
        latency_per_post_ms=latency_per_post_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=pricing.estimate_jev_cost_usd(input_tokens, output_tokens),
        model=JEV_MODEL_ID,
        instruction_sha256=instruction_hash,
    )


def _process_batch(
    *,
    batch_index: int,
    batch: list[PostTask],
    view: str,
    api_key: str,
    rate_limiter: RequestStartLimiter,
    instruction: str | None,
    ablation_id: str,
    instruction_hash: str,
) -> BatchWorkResult:
    client_local = threading.local()

    def _client_for_thread() -> TypeSafeClient:
        client = getattr(client_local, "client", None)
        if client is None:
            client = build_client(api_key)
            client_local.client = client
        return client

    client = _client_for_thread()
    started_at_utc = datetime.now(timezone.utc).isoformat()
    attempts = 0
    last_error: Exception | None = None

    def _attempt() -> BatchResult:
        nonlocal attempts
        attempts += 1
        rate_limiter.wait()
        return score_batch(client, [task.state_text for task in batch], view, instruction=instruction)

    try:
        batch_result = run_with_retries(_attempt)
    except Exception as exc:
        last_error = exc
        request_record = _make_request_record(
            ablation_id=ablation_id,
            view=view,
            batch_index=batch_index,
            batch=batch,
            attempt=attempts,
            status="error",
            error_type=type(exc).__name__,
            started_at_utc=started_at_utc,
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            instruction_hash=instruction_hash,
        )
        raise _BatchProcessingError(request_record, exc) from exc

    request_record = _make_request_record(
        ablation_id=ablation_id,
        view=view,
        batch_index=batch_index,
        batch=batch,
        attempt=attempts,
        status="ok",
        error_type=None,
        started_at_utc=started_at_utc,
        latency_ms=batch_result.latency_ms,
        input_tokens=batch_result.input_tokens,
        output_tokens=batch_result.output_tokens,
        instruction_hash=instruction_hash,
    )
    predictions = _build_predictions(
        batch,
        batch_index,
        view,
        batch_result,
        attempts,
        instruction_hash,
    )
    return BatchWorkResult(
        batch_index=batch_index,
        predictions=predictions,
        request_record=request_record,
    )


class _BatchProcessingError(Exception):
    def __init__(self, request_record: RequestRecord, original: Exception) -> None:
        super().__init__(str(original))
        self.request_record = request_record
        self.original = original


def _summarize_predictions(
    predictions: list[PostPrediction],
    *,
    view: str,
    add_criteria: bool,
) -> SmokeSummary:
    request_latencies: list[float] = []
    per_post_latencies: list[float] = []
    request_input_tokens = 0
    request_output_tokens = 0
    for prediction in predictions:
        if prediction.position_in_request != 0:
            continue
        request_latencies.append(prediction.request_latency_ms)
        per_post_latencies.append(prediction.per_post_latency_ms)
        request_input_tokens += prediction.request_input_tokens
        request_output_tokens += prediction.request_output_tokens
    unique_request_indices = sorted({prediction.request_index for prediction in predictions})
    total_cost_usd = sum(prediction.estimated_cost_usd for prediction in predictions)
    return SmokeSummary(
        view=view,
        add_criteria=add_criteria,
        n_posts=len(predictions),
        n_requests=len(unique_request_indices),
        total_input_tokens=request_input_tokens,
        total_output_tokens=request_output_tokens,
        total_cost_usd=total_cost_usd,
        latency_ms_p50=latency.percentile_ms(request_latencies, 0.5),
        latency_ms_p90=latency.percentile_ms(request_latencies, 0.9),
        latency_ms_p99=latency.percentile_ms(request_latencies, 0.99),
        per_post_latency_ms_p50=latency.percentile_ms(per_post_latencies, 0.5),
        per_post_latency_ms_p90=latency.percentile_ms(per_post_latencies, 0.9),
        per_post_latency_ms_p99=latency.percentile_ms(per_post_latencies, 0.99),
    )


def run_scoring_pass(
    tasks: list[PostTask],
    output_dir: Path,
    *,
    view: str,
    api_key: str,
    max_starts_per_minute: int = MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
    instruction: str | None = None,
    ablation_id: str = "",
    add_criteria: bool = False,
) -> SmokeSummary:
    """Score tasks with threading, rate limiting, retries, and resume.

    Each completed batch appends to ``predictions.jsonl`` and ``requests.jsonl`` so
    a crash can resume. Resume ignores prediction rows whose ``instruction_sha256``
    does not match the current instruction; legacy rows without that field match
    only when ``instruction`` is ``None``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / PREDICTIONS_FILENAME
    requests_path = output_dir / REQUESTS_FILENAME
    deadletter_path = output_dir / DEADLETTER_FILENAME

    already_seen = seen_post_ids(
        predictions_path,
        instruction=instruction,
        view=view,
    )
    pending_tasks = [task for task in tasks if task.post_id not in already_seen]
    batches = make_batches(pending_tasks)
    if not batches:
        existing_predictions = _load_predictions(
            predictions_path,
            instruction=instruction,
            view=view,
        )
        return _summarize_predictions(
            existing_predictions,
            view=view,
            add_criteria=add_criteria,
        )

    rate_limiter = RequestStartLimiter(max_starts_per_minute)
    instruction_hash = instruction_sha256(instruction, view)

    with ThreadPoolExecutor(max_workers=WORKER_THREADS) as executor:
        futures: dict[Future[BatchWorkResult], int] = {}
        for batch_index, batch in enumerate(batches):
            future = executor.submit(
                _process_batch,
                batch_index=batch_index,
                batch=batch,
                view=view,
                api_key=api_key,
                rate_limiter=rate_limiter,
                instruction=instruction,
                ablation_id=ablation_id,
                instruction_hash=instruction_hash,
            )
            futures[future] = batch_index

        pending = set(futures)
        try:
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.remove(future)
                    try:
                        work_result = future.result()
                    except _BatchProcessingError as exc:
                        _append_jsonl(deadletter_path, [exc.request_record.to_dict()])
                    except AUTH_ERROR_TYPES:
                        for other_future in pending:
                            other_future.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise
                    except Exception:
                        for other_future in pending:
                            other_future.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise
                    else:
                        _append_jsonl(
                            predictions_path,
                            [prediction.model_dump() for prediction in work_result.predictions],
                        )
                        _append_jsonl(
                            requests_path,
                            [work_result.request_record.to_dict()],
                        )
        finally:
            executor.shutdown(wait=True, cancel_futures=False)

    all_predictions = _load_predictions(
        predictions_path,
        instruction=instruction,
        view=view,
    )
    return _summarize_predictions(
        all_predictions,
        view=view,
        add_criteria=add_criteria,
    )


def _load_predictions(
    predictions_path: Path,
    *,
    instruction: str | None,
    view: str,
) -> list[PostPrediction]:
    if not predictions_path.is_file():
        return []
    expected_hash = instruction_sha256(instruction, view)
    predictions: list[PostPrediction] = []
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            record_hash = payload.get("instruction_sha256")
            if record_hash is None:
                if instruction is not None:
                    continue
            elif record_hash != expected_hash:
                continue
            predictions.append(PostPrediction.model_validate(payload))
    return predictions


def _load_cohort_parquet(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"cohort parquet missing at {path}; run Step 2 splits first"
        )
    return pd.read_parquet(path)


def _sample_smoke_tasks(
    cohort: pd.DataFrame,
    *,
    view: str,
    limit: int,
    add_criteria: bool,
) -> list[PostTask]:
    if len(cohort) < limit:
        raise ValueError(f"cohort has only {len(cohort)} posts; need {limit}")
    rng = np.random.default_rng(SMOKE_SEED)
    chosen_indices = rng.choice(cohort.index.to_numpy(), size=limit, replace=False)
    sampled = cohort.loc[chosen_indices]
    tasks: list[PostTask] = []
    for row in sampled.itertuples():
        state_text = render_state_text(
            view,
            str(row.original_text),
            str(row.mirror_text),
            str(row.post_1_role),
            add_criteria=add_criteria,
        )
        tasks.append(
            PostTask(
                post_id=str(row.post_id),
                state_text=state_text,
                gold_label=int(row.label),
            )
        )
    return tasks


def _write_smoke_summary(output_dir: Path, summary: SmokeSummary) -> Path:
    output_path = output_dir / SMOKE_SUMMARY_FILENAME
    output_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> None:
    """Smoke CLI for batched Jev scoring."""
    parser = argparse.ArgumentParser(description="Batched Jev scorer")
    parser.add_argument("--smoke", action="store_true", help="Run smoke scoring pass")
    parser.add_argument("--limit", type=int, default=SMOKE_LIMIT_DEFAULT)
    parser.add_argument("--view", choices=VALID_VIEWS, required=True)
    parser.add_argument("--add-criteria", action="store_true")
    parser.add_argument(
        "--rate-cap",
        type=int,
        default=MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
        help="Max request starts per minute",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.smoke:
        parser.error("--smoke is required for this entrypoint")

    cohort = _load_cohort_parquet(COHORT_PARQUET)
    tasks = _sample_smoke_tasks(
        cohort,
        view=args.view,
        limit=args.limit,
        add_criteria=args.add_criteria,
    )
    predictions_path = args.output_dir / PREDICTIONS_FILENAME
    already_seen = seen_post_ids(
        predictions_path,
        instruction=None,
        view=args.view,
    )
    pending_count = sum(1 for task in tasks if task.post_id not in already_seen)

    api_key = get_jev_api_key()
    summary = run_scoring_pass(
        tasks,
        args.output_dir,
        view=args.view,
        api_key=api_key,
        max_starts_per_minute=args.rate_cap,
        add_criteria=args.add_criteria,
    )
    _write_smoke_summary(args.output_dir, summary)

    n_new_requests = (pending_count + BATCH_SIZE - 1) // BATCH_SIZE if pending_count else 0
    print(
        "smoke "
        f"view={args.view} "
        f"add_criteria={str(args.add_criteria).lower()} "
        f"n_requests={summary.n_requests} "
        f"n_new_requests={n_new_requests} "
        f"total_cost_usd={summary.total_cost_usd:.6f} "
        f"p50_ms={summary.latency_ms_p50:.2f}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])  # pragma: no cover
