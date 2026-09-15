"""Run experiment 1 study-prompt completions.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_FILENAME,
    COHORT_OUTPUT_DIR,
    DEEPSEEK_MODEL_ID,
    EXPERIMENT_DIR,
    FULL_MAX_NEW_TOKENS,
    QWEN_MODEL_ID,
    SMOKE_LIMIT,
    SMOKE_MAX_NEW_TOKENS,
    STATUS_VALID,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    complete_post,
    trace_to_dict,
)

MODEL_CHOICES = {
    "qwen": QWEN_MODEL_ID,
    "deepseek": DEEPSEEK_MODEL_ID,
}
ADD_CRITERIA = False
UTF8 = "utf-8"
WRITE_MODE = "w"
APPEND_MODE = "a"


def main() -> None:
    args = _parse_args()
    posts = _load_posts(args.limit if args.smoke else None)
    models = _selected_models(args.model)
    max_new_tokens = SMOKE_MAX_NEW_TOKENS if args.smoke else FULL_MAX_NEW_TOKENS
    for model_id in models:
        print(f"thinking_enabled=true model_id={model_id}")
        _run_model(posts, model_id, args.smoke, max_new_tokens)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--limit", type=int, default=SMOKE_LIMIT)
    parser.add_argument("--model", choices=("qwen", "deepseek", "both"), default="both")
    parser.add_argument("--summarize", action="store_true")
    return parser.parse_args()


def _selected_models(choice: str) -> tuple[str, ...]:
    if choice == "both":
        return (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID)
    return (MODEL_CHOICES[choice],)


def _load_posts(limit: int | None) -> list[dict[str, object]]:
    path = COHORT_OUTPUT_DIR / COHORT_FILENAME
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(path)
    if limit is not None:
        frame = frame.head(limit)
    return frame.to_dict(orient="records")


def _run_model(
    posts: list[dict[str, object]],
    model_id: str,
    smoke: bool,
    max_new_tokens: int,
) -> None:
    sink = _trace_path(model_id, smoke)
    remaining = _remaining_posts(posts, sink, smoke)
    if not remaining:
        return
    tokenizer, model = _load_model(model_id)
    sink.parent.mkdir(parents=True, exist_ok=True)
    mode = WRITE_MODE if smoke else APPEND_MODE
    with sink.open(mode, encoding=UTF8) as handle:
        for post in remaining:
            _write_one_trace(handle, post, model_id, smoke, max_new_tokens, tokenizer, model)


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


def _write_one_trace(
    handle: object,
    post: dict[str, object],
    model_id: str,
    smoke: bool,
    max_new_tokens: int,
    tokenizer: object,
    model: object,
) -> None:
    record = complete_post(post, model_id, ADD_CRITERIA, max_new_tokens, tokenizer, model)
    handle.write(json.dumps(trace_to_dict(record)) + "\n")
    _require_valid_smoke(record, smoke)
    print(f"post_id={record.post_id} thinking_token_count={record.thinking_token_count}")


def _require_valid_smoke(record: object, smoke: bool) -> None:
    if not smoke:
        return
    if record.status != STATUS_VALID or record.thinking_token_count <= 0:
        raise RuntimeError(
            f"smoke failed status={record.status} count={record.thinking_token_count}"
        )


def _trace_path(model_id: str, smoke: bool) -> Path:
    name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
    folder = "smoke" if smoke else "outputs"
    return EXPERIMENT_DIR / "experiment1" / folder / f"traces_{name}.jsonl"


def _load_model(model_id: str) -> tuple[object, object]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("GPU required; use hf_job_command from jobs.py")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto"
    )
    return tokenizer, model


if __name__ == "__main__":
    main()
