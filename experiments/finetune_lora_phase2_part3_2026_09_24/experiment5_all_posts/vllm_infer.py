"""Batched vLLM keep/remove inference on merged Qwen3.5 4B weights.

Run from root::

    PYTHONPATH=. uv run python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/vllm_infer.py \\
      --chat-jsonl path/to/chat.jsonl --model-dir path/to/merged --output-csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import (
    CHAT_TEMPLATE_KWARGS,
    CHUNK_SIZE,
    MODEL_ID,
    PRED_COLUMNS,
    SAMPLING_MAX_TOKENS,
    SAMPLING_TEMPERATURE,
    VLLM_DTYPE,
    VLLM_ENABLE_PREFIX_CACHING,
    VLLM_GPU_MEMORY_UTILIZATION,
    VLLM_MAX_MODEL_LEN,
    VLLM_MAX_NUM_SEQS,
    VLLM_TRUST_REMOTE_CODE,
)
from experiments.finetune_qwen_model_2026_08_08.inference import (
    gold_decision_from_messages,
    load_chat_records,
    messages_for_generation,
)
from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    gold_label_from_decision,
    parse_generation,
)
from experiments.finetune_qwen_model_2026_08_08.train import _bind_chat_template_kwargs


@dataclass(frozen=True)
class PromptRecord:
    """One rendered prompt with gold metadata."""

    message_id: str
    gold_decision: str
    gold_label: int
    prompt_text: str


def _require_hf_token() -> str:
    """Return HF_TOKEN or exit."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is required but missing or empty.")
    return token


def render_prompts(
    records: Sequence[dict[str, Any]],
    tokenizer: Any,
    chat_template_kwargs: dict[str, Any] | None = None,
) -> list[PromptRecord]:
    """Render chat prompts without the assistant gold turn.

    Parameters
    ----------
    records
        Chat JSONL rows with ``message_id`` and ``messages``.
    tokenizer
        Hugging Face tokenizer with ``apply_chat_template``.
    chat_template_kwargs
        Optional kwargs merged into each template call (for example
        ``enable_thinking=False``).

    Returns
    -------
    list[PromptRecord]
        Rendered prompts in input order.
    """
    kwargs = chat_template_kwargs if chat_template_kwargs is not None else CHAT_TEMPLATE_KWARGS
    tokenizer = _bind_chat_template_kwargs(tokenizer, kwargs)
    rendered: list[PromptRecord] = []
    for record in records:
        message_id = str(record["message_id"])
        messages = record["messages"]
        gold_decision = gold_decision_from_messages(messages)
        gold_label = gold_label_from_decision(gold_decision)
        prompt_messages = messages_for_generation(messages)
        prompt_text = tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        rendered.append(
            PromptRecord(
                message_id=message_id,
                gold_decision=gold_decision,
                gold_label=gold_label,
                prompt_text=str(prompt_text),
            )
        )
    return rendered


def rows_from_generations(
    prompts: Sequence[PromptRecord],
    raw_generations: Sequence[str],
) -> list[dict[str, Any]]:
    """Build prediction rows from parallel prompt and generation lists.

    Parameters
    ----------
    prompts
        Metadata for each request.
    raw_generations
        Model output text per prompt, same length as ``prompts``.

    Returns
    -------
    list[dict]
        Rows matching ``PRED_COLUMNS``.

    Raises
    ------
    ValueError
        If lengths differ.
    """
    if len(prompts) != len(raw_generations):
        raise ValueError(
            f"prompt count {len(prompts)} != generation count {len(raw_generations)}"
        )
    rows: list[dict[str, Any]] = []
    for prompt, raw in zip(prompts, raw_generations, strict=True):
        parsed = parse_generation(raw)
        rows.append(
            {
                "message_id": prompt.message_id,
                "decision": prompt.gold_decision,
                "keep_remove_label": prompt.gold_label,
                "raw_generation": raw,
                "predicted_decision": parsed.predicted_decision,
                "predicted_label": (
                    ""
                    if parsed.predicted_label is None
                    else int(parsed.predicted_label)
                ),
            }
        )
    return rows


def load_existing_message_ids(output_csv: Path) -> set[str]:
    """Return message ids already present in an on-disk prediction CSV."""
    if not output_csv.is_file():
        return set()
    seen: set[str] = set()
    with output_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return set()
        for row in reader:
            message_id = row.get("message_id")
            if message_id:
                seen.add(str(message_id))
    return seen


def append_rows(output_csv: Path, rows: Sequence[dict[str, Any]]) -> None:
    """Append prediction rows, writing the header when the file is new."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_csv.is_file() or output_csv.stat().st_size == 0
    with output_csv.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PRED_COLUMNS))
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in PRED_COLUMNS})


def records_pending_resume(
    records: Sequence[dict[str, Any]],
    output_csv: Path,
) -> list[dict[str, Any]]:
    """Return input records whose message_id is not already in ``output_csv``."""
    existing = load_existing_message_ids(output_csv)
    return [record for record in records if str(record["message_id"]) not in existing]


def load_vllm_engine(model_dir: Path) -> tuple[Any, Any, Any]:
    """Load vLLM LLM, tokenizer, and sampling params for a merged model."""
    import torch
    from vllm import LLM
    from vllm import SamplingParams

    if not torch.cuda.is_available():
        raise RuntimeError("GPU required for vLLM inference.")

    kwargs: dict[str, Any] = {
        "model": str(model_dir),
        "dtype": VLLM_DTYPE,
        "max_model_len": VLLM_MAX_MODEL_LEN,
        "gpu_memory_utilization": VLLM_GPU_MEMORY_UTILIZATION,
        "enable_prefix_caching": VLLM_ENABLE_PREFIX_CACHING,
        "max_num_seqs": VLLM_MAX_NUM_SEQS,
        "trust_remote_code": VLLM_TRUST_REMOTE_CODE,
        "language_model_only": True,
    }
    try:
        llm = LLM(**kwargs)
    except TypeError:
        kwargs.pop("language_model_only", None)
        llm = LLM(**kwargs)

    sampling = SamplingParams(
        temperature=SAMPLING_TEMPERATURE,
        max_tokens=SAMPLING_MAX_TOKENS,
    )
    tokenizer = llm.get_tokenizer()
    return llm, tokenizer, sampling


def default_vllm_generate(
    llm: Any,
    sampling: Any,
    prompt_texts: Sequence[str],
) -> list[str]:
    """Run vLLM generate on a batch of prompt strings."""
    outputs = llm.generate(list(prompt_texts), sampling)
    generations: list[str] = []
    for output in outputs:
        text = output.outputs[0].text if output.outputs else ""
        generations.append(str(text))
    return generations


def run_chunked_inference(
    prompts: Sequence[PromptRecord],
    output_csv: Path,
    generate_fn: Callable[[Sequence[str]], Sequence[str]],
    chunk_size: int = CHUNK_SIZE,
) -> int:
    """Generate predictions in chunks and append to CSV.

    Parameters
    ----------
    prompts
        Rendered prompts to score.
    output_csv
        Destination CSV (resume-safe append).
    generate_fn
        Callable mapping a batch of prompt strings to raw generations.
    chunk_size
        Batch size per generate call.

    Returns
    -------
    int
        Number of rows written in this call.
    """
    written = 0
    for start in range(0, len(prompts), chunk_size):
        chunk = prompts[start : start + chunk_size]
        texts = [item.prompt_text for item in chunk]
        raw_generations = list(generate_fn(texts))
        rows = rows_from_generations(chunk, raw_generations)
        append_rows(output_csv, rows)
        written += len(rows)
    return written


def maybe_upload_preds(output_csv: Path) -> None:
    """Upload the prediction CSV parent when ``PREDS_S3_URI`` is set."""
    preds_s3_uri = os.environ.get("PREDS_S3_URI", "").strip()
    if not preds_s3_uri:
        return
    from experiments.finetune_qwen_model_2026_08_08.src.s3_upload import (
        upload_directory,
    )

    region = os.environ.get("AWS_REGION", "us-east-2")
    upload_directory(output_csv.parent, preds_s3_uri, region=region)


def run_vllm(
    chat_jsonl: Path,
    model_dir: Path,
    output_csv: Path,
    model_id: str = MODEL_ID,
    chat_template_kwargs: dict[str, Any] | None = None,
    chunk_size: int = CHUNK_SIZE,
    generate_fn: Callable[[Sequence[str]], Sequence[str]] | None = None,
    upload_preds: bool = True,
) -> int:
    """Score a chat JSONL file with vLLM (or an injected generate function).

    Parameters
    ----------
    chat_jsonl
        Input JSONL with gold assistant turns.
    model_dir
        Local merged model directory for vLLM.
    output_csv
        Resume-safe CSV destination.
    model_id
        Hugging Face id used only to load the tokenizer when ``generate_fn``
        is provided (unit tests). Ignored when vLLM loads the engine.
    chat_template_kwargs
        Optional chat-template kwargs override.
    chunk_size
        Requests per vLLM batch.
    generate_fn
        Optional fake generator for tests; when omitted, vLLM is loaded.
    upload_preds
        When True, honor ``PREDS_S3_URI`` after inference completes.

    Returns
    -------
    int
        Number of rows written during this invocation.
    """
    records = load_chat_records(chat_jsonl)
    pending_records = records_pending_resume(records, output_csv)
    if not pending_records:
        print(f"No pending rows; {output_csv} already complete.")
        if upload_preds:
            maybe_upload_preds(output_csv)
        return 0

    if generate_fn is None:
        llm, tokenizer, sampling = load_vllm_engine(model_dir)

        def _generate(texts: Sequence[str]) -> list[str]:
            return default_vllm_generate(llm, sampling, texts)

        bound_generate: Callable[[Sequence[str]], Sequence[str]] = _generate
        tokenizer_for_render = tokenizer
    else:
        from transformers import AutoTokenizer

        hf_token = _require_hf_token()
        tokenizer_for_render = AutoTokenizer.from_pretrained(
            model_id,
            token=hf_token,
            trust_remote_code=True,
        )
        if tokenizer_for_render.pad_token is None:
            tokenizer_for_render.pad_token = tokenizer_for_render.eos_token
        bound_generate = generate_fn

    prompts = render_prompts(
        pending_records,
        tokenizer_for_render,
        chat_template_kwargs=chat_template_kwargs,
    )
    written = run_chunked_inference(
        prompts,
        output_csv,
        generate_fn=bound_generate,
        chunk_size=chunk_size,
    )
    print(f"Wrote {written} rows to {output_csv}")
    if upload_preds:
        maybe_upload_preds(output_csv)
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Batched vLLM inference for all-posts keep/remove scoring."
    )
    parser.add_argument("--chat-jsonl", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument(
        "--chat-template-kwargs-json",
        default=None,
        help="Optional JSON object for apply_chat_template kwargs.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip PREDS_S3_URI upload even when set.",
    )
    return parser.parse_args(argv)


def _parse_chat_template_kwargs_json(raw: str | None) -> dict[str, Any] | None:
    if raw is None or not raw.strip():
        return None
    parsed = json.loads(raw)
    if parsed is None:
        return None
    if not isinstance(parsed, dict):
        raise SystemExit("--chat-template-kwargs-json must be a JSON object")
    return parsed


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    template_kwargs = _parse_chat_template_kwargs_json(args.chat_template_kwargs_json)
    run_vllm(
        chat_jsonl=args.chat_jsonl,
        model_dir=args.model_dir,
        output_csv=args.output_csv,
        model_id=str(args.model_id),
        chat_template_kwargs=template_kwargs,
        upload_preds=not args.no_upload,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
