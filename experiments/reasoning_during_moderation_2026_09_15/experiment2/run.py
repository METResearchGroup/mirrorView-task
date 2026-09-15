"""Run experiment 2 study-plus-criteria completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment2/run.py --summarize
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.reasoning_during_moderation_2026_09_15.experiment1.run import (
    APPEND_MODE,
    UTF8,
    _load_model,
    _load_posts,
    _read_jsonl,
    _remaining_posts,
    _selected_models,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    FULL_MAX_NEW_TOKENS,
    OUTPUT_S3_BUCKET,
    PROMPT_ARM_CRITERIA,
    QWEN_MODEL_ID,
    SMOKE_LIMIT,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    complete_post,
    generation_seed,
    trace_to_dict,
)
from lib.constants import REPO_ROOT

ADD_CRITERIA = True
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
    """Return pair order and seed matched to experiment 1 when a trace exists."""
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
    parser.add_argument("--limit", type=int, default=SMOKE_LIMIT)
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
    remaining = _remaining_posts(posts, sink, False)
    if remaining:
        _generate_remaining(remaining, sink, model_id, max_new_tokens)
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
        for post in remaining:
            _write_one_trace(
                handle, post, model_id, max_new_tokens, tokenizer, model, exp1_by_post
            )


def _exp1_trace_index(model_id: str) -> dict[str, dict[str, object]]:
    path = EXPERIMENT1_OUTPUT_DIR / _trace_filename(model_id)
    if not path.is_file():
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
    record = complete_post(aligned, model_id, ADD_CRITERIA, max_new_tokens, tokenizer, model)
    handle.write(json.dumps(trace_to_dict(record)) + "\n")
    print(f"post_id={record.post_id} thinking_token_count={record.thinking_token_count}")


def _summarize() -> None:
    raise NotImplementedError


def _trace_path(model_id: str) -> Path:
    return EXPERIMENT2_OUTPUT_DIR / _trace_filename(model_id)


def _trace_filename(model_id: str) -> str:
    name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
    return f"traces_{name}.jsonl"


def _upload_output(path: Path) -> None:
    """Upload under the experiment 2 prefix. put_new when absent, else replace."""
    key = str(path.relative_to(REPO_ROOT))
    _require_experiment2_key(key)
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    existing = store.get(key)
    body = path.read_bytes()
    if existing is None:
        store.put_new(key, body)
        return
    store.replace(key, body, etag=existing.etag)


def _require_experiment2_key(key: str) -> None:
    if not key.startswith(EXPERIMENT2_S3_PREFIX):
        raise ValueError(f"refusing S3 key outside {EXPERIMENT2_S3_PREFIX}: {key}")


if __name__ == "__main__":
    main()
