"""Run experiment 2 study-plus-criteria completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --summarize
"""

from __future__ import annotations

import argparse
import json
import traceback
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment1.run import (
    APPEND_MODE,
    UTF8,
    _load_model,
    _load_posts,
    _read_jsonl,
    _remaining_posts,
    _require_both_models,
    _require_trace_file,
    _selected_models,
    _strip_infrastructure,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment1.summarize import (
    summarize_tokens,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.artifacts import (
    download_if_missing,
    upload_under_prefix,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DEEPSEEK_MODEL_ID,
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    FULL_MAX_NEW_TOKENS,
    PROMPT_ARM_CRITERIA,
    QWEN_MODEL_ID,
    STATUS_INFRASTRUCTURE,
    TRACE_UPLOAD_EVERY,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    TraceRecord,
    complete_post,
    generation_seed,
    trace_to_dict,
)
from lib.constants import REPO_ROOT

ADD_CRITERIA = True
TOKEN_SUMMARY_FILENAME = "token_summary.csv"
EXPERIMENT2_S3_PREFIX = f"{EXPERIMENT_S3_PREFIX}/experiment2/"
EXPERIMENT2_OUTPUT_DIR = EXPERIMENT_DIR / "experiment2" / "outputs"
EXPERIMENT1_OUTPUT_DIR = EXPERIMENT_DIR / "experiment1" / "outputs"


@dataclass(frozen=True)
class PlannedCompletion:
    """Matched experiment 2 fields for one post and model."""

    post_id: str
    model_id: str
    post_1_role: str
    post_2_role: str
    generation_seed: int
    add_criteria: bool
    prompt_arm: str


def planned_completion_fields(
    cohort_row: Mapping[str, object],
    exp1_trace: Mapping[str, object] | None,
) -> PlannedCompletion:
    """Return pair order and seed matched to experiment 1 when a trace exists.

    Parameters
    ----------
    cohort_row
        Cohort fields plus ``model_id``. Used when ``exp1_trace`` is None.
    exp1_trace
        Experiment 1 jsonl row for the same post and model, if present.
    """
    if exp1_trace is not None:
        return _from_exp1_trace(exp1_trace)
    return _from_cohort_row(cohort_row)


def _from_exp1_trace(exp1_trace: Mapping[str, object]) -> PlannedCompletion:
    """Copy identity, pair order, and seed from an experiment 1 trace row."""
    return PlannedCompletion(
        str(exp1_trace["post_id"]),
        str(exp1_trace["model_id"]),
        str(exp1_trace["post_1_role"]),
        str(exp1_trace["post_2_role"]),
        int(exp1_trace["generation_seed"]),
        ADD_CRITERIA,
        PROMPT_ARM_CRITERIA,
    )


def _from_cohort_row(cohort_row: Mapping[str, object]) -> PlannedCompletion:
    """Fall back to the cohort pair order and generation_seed(post_id)."""
    post_id = str(cohort_row["post_id"])
    return PlannedCompletion(
        post_id,
        str(cohort_row["model_id"]),
        str(cohort_row["post_1_role"]),
        str(cohort_row["post_2_role"]),
        generation_seed(post_id),
        ADD_CRITERIA,
        PROMPT_ARM_CRITERIA,
    )


def main() -> None:
    args = _parse_args()
    if args.summarize:
        _summarize()
        return
    _run_full(args)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("qwen", "deepseek", "both"), default="both")
    parser.add_argument("--summarize", action="store_true")
    return parser.parse_args()


def _run_full(args: argparse.Namespace) -> None:
    posts = _load_posts(None)
    max_new_tokens = FULL_MAX_NEW_TOKENS
    for model_id in _selected_models(args.model):
        print(f"thinking_enabled=true model_id={model_id}")
        _run_model(posts, model_id, max_new_tokens)


def _run_model(
    posts: list[dict[str, object]],
    model_id: str,
    max_new_tokens: int,
) -> None:
    sink = _trace_path(model_id)
    _strip_infrastructure(sink)
    remaining = _remaining_posts(posts, sink, False)
    try:
        if remaining:
            _generate_remaining(remaining, sink, model_id, max_new_tokens)
    finally:
        if sink.is_file():
            _upload_output(sink)


def _generate_remaining(
    remaining: list[dict[str, object]],
    sink: Path,
    model_id: str,
    max_new_tokens: int,
) -> None:
    tokenizer, model = _load_model(model_id)
    exp1_by_post = _exp1_trace_index(model_id)
    sink.parent.mkdir(parents=True, exist_ok=True)
    with sink.open(APPEND_MODE, encoding=UTF8) as handle:
        for index, post in enumerate(remaining, start=1):
            _write_one_trace(
                handle, post, model_id, max_new_tokens, tokenizer, model, exp1_by_post
            )
            handle.flush()
            if index % TRACE_UPLOAD_EVERY == 0:
                _upload_output(sink)


def _exp1_trace_index(model_id: str) -> dict[str, dict[str, object]]:
    path = EXPERIMENT1_OUTPUT_DIR / _trace_filename(model_id)
    if not path.is_file():
        try:
            download_if_missing(path, str(path.relative_to(REPO_ROOT)))
        except FileNotFoundError:
            return {}
    rows = _read_jsonl(path)
    return {str(row["post_id"]): row for row in rows if str(row["model_id"]) == model_id}


def _write_one_trace(
    handle: object,
    post: dict[str, object],
    model_id: str,
    max_new_tokens: int,
    tokenizer: object,
    model: object,
    exp1_by_post: dict[str, dict[str, object]],
) -> None:
    planned = planned_completion_fields(
        {**post, "model_id": model_id}, exp1_by_post.get(str(post["post_id"]))
    )
    aligned = {**post, "post_1_role": planned.post_1_role, "post_2_role": planned.post_2_role}
    record = _complete_or_infrastructure(
        aligned, model_id, max_new_tokens, tokenizer, model
    )
    handle.write(json.dumps(trace_to_dict(record)) + "\n")
    print(f"post_id={record.post_id} thinking_token_count={record.thinking_token_count}")


def _summarize() -> None:
    traces = _load_both_model_traces()
    summary = summarize_tokens(traces)
    path = EXPERIMENT2_OUTPUT_DIR / TOKEN_SUMMARY_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    print(f"rows={len(summary)} prompt_arm={PROMPT_ARM_CRITERIA}")
    _upload_output(path)


def _load_both_model_traces() -> pd.DataFrame:
    qwen_path = _trace_path(QWEN_MODEL_ID)
    deepseek_path = _trace_path(DEEPSEEK_MODEL_ID)
    _require_trace_file(qwen_path)
    _require_trace_file(deepseek_path)
    rows = _read_jsonl(qwen_path) + _read_jsonl(deepseek_path)
    frame = pd.DataFrame(rows)
    _require_both_models(frame)
    return frame


def _trace_path(model_id: str) -> Path:
    return EXPERIMENT2_OUTPUT_DIR / _trace_filename(model_id)


def _trace_filename(model_id: str) -> str:
    name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
    return f"traces_{name}.jsonl"


def _complete_or_infrastructure(
    post: dict[str, object],
    model_id: str,
    max_new_tokens: int,
    tokenizer: object,
    model: object,
) -> TraceRecord:
    try:
        return complete_post(post, model_id, ADD_CRITERIA, max_new_tokens, tokenizer, model)
    except Exception:
        traceback.print_exc()
        return _infrastructure_record(post, model_id, max_new_tokens)


def _infrastructure_record(
    post: dict[str, object], model_id: str, max_new_tokens: int
) -> TraceRecord:
    return TraceRecord(
        str(post["post_id"]),
        str(post["group"]),
        model_id,
        PROMPT_ARM_CRITERIA,
        str(post["post_1_role"]),
        str(post["post_2_role"]),
        generation_seed(str(post["post_id"])),
        STATUS_INFRASTRUCTURE,
        0,
        "",
        "",
        max_new_tokens,
    )


def _upload_output(path: Path) -> None:
    """Upload under the experiment 2 prefix. put_new when absent, else replace."""
    upload_under_prefix(path, EXPERIMENT2_S3_PREFIX)


if __name__ == "__main__":
    main()
