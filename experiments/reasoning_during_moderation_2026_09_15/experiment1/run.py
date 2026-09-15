"""Run experiment 1 study-prompt completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment1.summarize import (
    summarize_tokens,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.artifacts import (
    download_if_missing,
    upload_under_prefix,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_FILENAME,
    COHORT_OUTPUT_DIR,
    COHORT_S3_KEY,
    DEEPSEEK_MODEL_ID,
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    FULL_MAX_NEW_TOKENS,
    INFERENCE_ENGINE,
    PROMPT_ARM_STUDY,
    QWEN_MODEL_ID,
    SMOKE_LIMIT,
    SMOKE_MAX_NEW_TOKENS,
    STATUS_INFRASTRUCTURE,
    STATUS_VALID,
    VLLM_CHUNK_SIZE,
    VLLM_OUTPUT_DIRNAME,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    TraceRecord,
    chunk_posts,
    complete_posts,
    generation_seed,
    load_engine,
    trace_to_dict,
)
from lib.constants import REPO_ROOT

MODEL_CHOICES = {
    "qwen": QWEN_MODEL_ID,
    "deepseek": DEEPSEEK_MODEL_ID,
}
ADD_CRITERIA = False
UTF8 = "utf-8"
WRITE_MODE = "w"
APPEND_MODE = "a"
TOKEN_SUMMARY_FILENAME = "token_summary.csv"
EXPERIMENT1_S3_PREFIX = f"{EXPERIMENT_S3_PREFIX}/experiment1/"
EXPERIMENT1_OUTPUT_DIR = EXPERIMENT_DIR / "experiment1" / "outputs"


def main() -> None:
    args = _parse_args()
    if args.summarize:
        _summarize()
        return
    posts = _load_posts(args.limit if args.smoke else None)
    models = _selected_models(args.model)
    default_cap = SMOKE_MAX_NEW_TOKENS if args.smoke else FULL_MAX_NEW_TOKENS
    max_new_tokens = args.max_new_tokens if args.max_new_tokens is not None else default_cap
    for model_id in models:
        print(
            f"thinking_enabled=true inference_engine={INFERENCE_ENGINE} "
            f"model_id={model_id} chunk_size={args.chunk_size}"
        )
        _run_model(posts, model_id, args.smoke, max_new_tokens, args.chunk_size)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--limit", type=int, default=SMOKE_LIMIT)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=VLLM_CHUNK_SIZE)
    parser.add_argument("--model", choices=("qwen", "deepseek", "both"), default="both")
    parser.add_argument("--summarize", action="store_true")
    return parser.parse_args()


def _selected_models(choice: str) -> tuple[str, ...]:
    if choice == "both":
        return (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID)
    return (MODEL_CHOICES[choice],)


def _load_posts(limit: int | None) -> list[dict[str, object]]:
    path = COHORT_OUTPUT_DIR / COHORT_FILENAME
    download_if_missing(path, COHORT_S3_KEY)
    frame = pd.read_parquet(path)
    if limit is not None:
        frame = frame.head(limit)
    return frame.to_dict(orient="records")


def _run_model(
    posts: list[dict[str, object]],
    model_id: str,
    smoke: bool,
    max_new_tokens: int,
    chunk_size: int,
) -> None:
    sink = _trace_path(model_id, smoke)
    if not smoke:
        _strip_infrastructure(sink)
    remaining = _remaining_posts(posts, sink, smoke)
    try:
        if remaining:
            _generate_remaining(
                remaining, sink, model_id, smoke, max_new_tokens, chunk_size
            )
    finally:
        if sink.is_file():
            _upload_output(sink)


def _generate_remaining(
    remaining: list[dict[str, object]],
    sink: Path,
    model_id: str,
    smoke: bool,
    max_new_tokens: int,
    chunk_size: int,
) -> None:
    tokenizer, llm = load_engine(model_id)
    sink.parent.mkdir(parents=True, exist_ok=True)
    mode = WRITE_MODE if smoke else APPEND_MODE
    with sink.open(mode, encoding=UTF8) as handle:
        for chunk_index, chunk in enumerate(chunk_posts(remaining, chunk_size)):
            started = time.perf_counter()
            records = _complete_chunk_or_infrastructure(
                chunk, model_id, smoke, max_new_tokens, tokenizer, llm
            )
            elapsed = time.perf_counter() - started
            think_tokens = sum(record.thinking_token_count for record in records)
            tok_s = think_tokens / elapsed if elapsed > 0 else 0.0
            print(
                f"chunk={chunk_index} n={len(chunk)} elapsed_s={elapsed:.1f} "
                f"think_tokens={think_tokens} think_tok_s={tok_s:.1f}"
            )
            for record in records:
                handle.write(json.dumps(trace_to_dict(record)) + "\n")
                _require_valid_smoke(record, smoke)
                print(
                    f"post_id={record.post_id} thinking_token_count={record.thinking_token_count}"
                )
            handle.flush()
            _upload_output(sink)


def _summarize() -> None:
    traces = _load_both_model_traces()
    summary = summarize_tokens(traces)
    path = EXPERIMENT1_OUTPUT_DIR / TOKEN_SUMMARY_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    print(f"rows={len(summary)} prompt_arm={PROMPT_ARM_STUDY}")
    _upload_output(path)


def _load_both_model_traces() -> pd.DataFrame:
    qwen_path = _trace_path(QWEN_MODEL_ID, False)
    deepseek_path = _trace_path(DEEPSEEK_MODEL_ID, False)
    _require_trace_file(qwen_path)
    _require_trace_file(deepseek_path)
    rows = _read_jsonl(qwen_path) + _read_jsonl(deepseek_path)
    frame = pd.DataFrame(rows)
    _require_both_models(frame)
    return frame


def _require_trace_file(path: Path) -> None:
    if not path.is_file():
        download_if_missing(path, str(path.relative_to(REPO_ROOT)))
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"missing traces; run both models first: {path}")


def _require_both_models(frame: pd.DataFrame) -> None:
    present = set(frame["model_id"].tolist())
    missing = {QWEN_MODEL_ID, DEEPSEEK_MODEL_ID} - present
    if missing:
        raise ValueError(f"summary requires both models, missing {missing}")


def _upload_output(path: Path) -> None:
    """Upload under the experiment 1 prefix. put_new when absent, else replace."""
    upload_under_prefix(path, EXPERIMENT1_S3_PREFIX)


def _remaining_posts(
    posts: list[dict[str, object]], sink: Path, smoke: bool
) -> list[dict[str, object]]:
    if smoke:
        return posts
    done = _done_post_ids(sink)
    return [post for post in posts if str(post["post_id"]) not in done]


def _done_post_ids(sink: Path) -> set[str]:
    if not sink.is_file():
        return set()
    return {str(row["post_id"]) for row in _read_jsonl(sink)}


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding=UTF8) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _strip_infrastructure(sink: Path) -> None:
    if not sink.is_file():
        return
    rows = [
        row for row in _read_jsonl(sink) if str(row["status"]) != STATUS_INFRASTRUCTURE
    ]
    with sink.open(WRITE_MODE, encoding=UTF8) as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _complete_chunk_or_infrastructure(
    posts: list[dict[str, object]],
    model_id: str,
    smoke: bool,
    max_new_tokens: int,
    tokenizer: object,
    llm: object,
) -> list[TraceRecord]:
    try:
        return complete_posts(
            posts, model_id, ADD_CRITERIA, max_new_tokens, tokenizer, llm
        )
    except Exception:
        traceback.print_exc()
        if smoke:
            raise
        return [_infrastructure_record(post, model_id, max_new_tokens) for post in posts]


def _infrastructure_record(
    post: dict[str, object], model_id: str, max_new_tokens: int
) -> TraceRecord:
    return TraceRecord(
        str(post["post_id"]),
        str(post["group"]),
        model_id,
        PROMPT_ARM_STUDY,
        str(post["post_1_role"]),
        str(post["post_2_role"]),
        generation_seed(str(post["post_id"])),
        STATUS_INFRASTRUCTURE,
        0,
        "",
        "",
        max_new_tokens,
    )


def _require_valid_smoke(record: object, smoke: bool) -> None:
    if not smoke:
        return
    if record.status != STATUS_VALID or record.thinking_token_count <= 0:
        raise RuntimeError(
            f"smoke failed status={record.status} count={record.thinking_token_count}"
        )


def _trace_path(model_id: str, smoke: bool) -> Path:
    name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
    if smoke:
        return EXPERIMENT_DIR / "experiment1" / "smoke" / f"traces_{name}.jsonl"
    return (
        EXPERIMENT_DIR
        / "experiment1"
        / "outputs"
        / VLLM_OUTPUT_DIRNAME
        / f"traces_{name}.jsonl"
    )


if __name__ == "__main__":
    main()
