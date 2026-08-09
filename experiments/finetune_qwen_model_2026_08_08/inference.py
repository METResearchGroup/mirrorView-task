"""Run greedy keep/remove inference for baseline or LoRA-adapter modes.

Writes prediction CSVs with columns:
message_id, decision, keep_remove_label, raw_generation,
predicted_decision, predicted_label.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_qwen_model_2026_08_08/inference.py \\
      --chat-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_test.jsonl \\
      --output-csv /tmp/test_labels.csv \\
      --mode baseline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from enum import Enum
from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import (
    MAX_NEW_TOKENS,
    gold_label_from_decision,
    parse_generation,
)
from experiments.finetune_qwen_model_2026_08_08.src.train_config import MODEL_ID

PRED_COLUMNS = (
    "message_id",
    "decision",
    "keep_remove_label",
    "raw_generation",
    "predicted_decision",
    "predicted_label",
)


class InferMode(str, Enum):
    """Inference arm."""

    BASELINE = "baseline"
    ADAPTER = "adapter"


def _require_hf_token() -> str:
    """Return HF_TOKEN or exit."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is required but missing or empty.")
    return token


def load_chat_records(path: Path) -> list[dict]:
    """Load chat JSONL records."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if "message_id" not in payload or "messages" not in payload:
                raise ValueError(f"{path}:{line_number} missing required keys")
            rows.append(payload)
    return rows


def messages_for_generation(messages: list[dict]) -> list[dict]:
    """Return system+user turns only (drop assistant gold)."""
    return [m for m in messages if m.get("role") in {"system", "user"}]


def gold_decision_from_messages(messages: list[dict]) -> str:
    """Extract assistant gold decision."""
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return str(message.get("content", "")).lower().strip()
    raise ValueError("Chat record missing assistant gold turn")


def run_inference(
    chat_jsonl: Path,
    output_csv: Path,
    mode: InferMode,
    adapter_dir: Path | None,
    limit: int | None,
    upload_preds: bool,
) -> None:
    """Generate predictions and write the prediction CSV."""
    hf_token = _require_hf_token()
    if mode is InferMode.ADAPTER and adapter_dir is None:
        raise SystemExit("--adapter-dir is required for --mode adapter")
    if mode is InferMode.BASELINE and adapter_dir is not None:
        raise SystemExit("--adapter-dir must not be set for --mode baseline")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    records = load_chat_records(chat_jsonl)
    if limit is not None:
        records = records[: int(limit)]

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        token=hf_token,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        token=hf_token,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto",
    )
    if mode is InferMode.ADAPTER:
        assert adapter_dir is not None
        model = PeftModel.from_pretrained(model, str(adapter_dir))
    model.eval()

    rows: list[dict] = []
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
        inputs = tokenizer(prompt_text, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        new_tokens = output_ids[0, inputs["input_ids"].shape[-1] :]
        raw_generation = tokenizer.decode(new_tokens, skip_special_tokens=True)
        parsed = parse_generation(raw_generation)
        rows.append(
            {
                "message_id": message_id,
                "decision": gold_decision,
                "keep_remove_label": gold_label,
                "raw_generation": raw_generation,
                "predicted_decision": parsed.predicted_decision,
                "predicted_label": (
                    ""
                    if parsed.predicted_label is None
                    else int(parsed.predicted_label)
                ),
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=list(PRED_COLUMNS))
    frame.to_csv(output_csv, index=False)
    print(f"Wrote {output_csv} ({len(frame)} rows)")

    if upload_preds:
        _maybe_upload_preds(output_csv.parent)


def _maybe_upload_preds(local_dir: Path) -> None:
    """Upload prediction directory when PREDS_S3_URI is set."""
    preds_s3_uri = os.environ.get("PREDS_S3_URI", "").strip()
    if not preds_s3_uri:
        return
    from experiments.finetune_qwen_model_2026_08_08.src.s3_upload import (
        upload_directory,
    )

    region = os.environ.get("AWS_REGION", "us-east-2")
    upload_directory(local_dir, preds_s3_uri, region=region)


def run_both_splits(
    data_dir: Path,
    output_dir: Path,
    mode: InferMode,
    adapter_dir: Path | None,
    limit: int | None,
) -> None:
    """Write train_labels.csv and test_labels.csv for one arm."""
    for split_name, jsonl_name in (
        ("train", "chat_train.jsonl"),
        ("test", "chat_test.jsonl"),
    ):
        run_inference(
            chat_jsonl=data_dir / jsonl_name,
            output_csv=output_dir / f"{split_name}_labels.csv",
            mode=mode,
            adapter_dir=adapter_dir,
            limit=limit,
            upload_preds=False,
        )
    _maybe_upload_preds(output_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Greedy keep/remove inference (baseline or adapter)."
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in InferMode],
        required=True,
        help="baseline (no adapter) or adapter.",
    )
    parser.add_argument(
        "--chat-jsonl",
        default=None,
        help="Single chat JSONL input (mutually exclusive with --both-splits).",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Output CSV for single-split mode.",
    )
    parser.add_argument(
        "--both-splits",
        action="store_true",
        help="Score chat_train and chat_test from --data-dir into --output-dir.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory with chat_train.jsonl / chat_test.jsonl for --both-splits.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for train_labels.csv / test_labels.csv (--both-splits).",
    )
    parser.add_argument(
        "--adapter-dir",
        default=None,
        help="PEFT adapter directory (required for --mode adapter).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row cap for smoke runs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    mode = InferMode(args.mode)
    adapter_dir = Path(args.adapter_dir) if args.adapter_dir else None

    if args.both_splits:
        if not args.data_dir or not args.output_dir:
            raise SystemExit(
                "--both-splits requires --data-dir and --output-dir"
            )
        run_both_splits(
            data_dir=Path(args.data_dir),
            output_dir=Path(args.output_dir),
            mode=mode,
            adapter_dir=adapter_dir,
            limit=args.limit,
        )
        return

    if not args.chat_jsonl or not args.output_csv:
        raise SystemExit(
            "Single-split mode requires --chat-jsonl and --output-csv"
        )
    run_inference(
        chat_jsonl=Path(args.chat_jsonl),
        output_csv=Path(args.output_csv),
        mode=mode,
        adapter_dir=adapter_dir,
        limit=args.limit,
        upload_preds=True,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
