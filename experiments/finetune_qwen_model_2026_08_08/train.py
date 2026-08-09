"""Fine-tune Qwen3-4B-Instruct with PEFT LoRA via TRL SFTTrainer.

Loads only ``chat_train.jsonl`` (never chat_test). Uses bf16 LoRA (not QLoRA),
assistant-only loss, and logs to W&B project ``mirrorview-finetune-qwen-2026-08-08``.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_qwen_model_2026_08_08/train.py \\
      --train-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \\
      --output-dir /tmp/qwen_lora_out \\
      [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.src.train_config import (
    TrainHyperparams,
    default_hyperparams,
)


def _require_hf_token() -> str:
    """Return HF_TOKEN or exit with a clear error."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is required but missing or empty.")
    return token


def _require_wandb_api_key() -> str:
    """Return WANDB_API_KEY via EnvVarsContainer (required for real train)."""
    from lib.load_env_vars import EnvVarsContainer

    return EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)


def _set_seeds(seed: int) -> None:
    """Seed python/random/numpy/torch for reproducibility."""
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def _count_jsonl_rows(path: Path) -> int:
    """Count non-empty JSONL lines."""
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _load_chat_messages(path: Path) -> list[dict]:
    """Load conversational records; keep only the messages field for SFT."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if "messages" not in payload:
                raise ValueError(f"{path}:{line_number} missing messages")
            rows.append({"messages": payload["messages"]})
    return rows


def print_dry_run_config(
    train_jsonl: Path,
    output_dir: Path,
    hyperparams: TrainHyperparams,
) -> None:
    """Print resolved training config without downloading the model."""
    row_count = _count_jsonl_rows(train_jsonl)
    print("dry-run: training config")
    print(f"  model_id: {hyperparams.model_id}")
    print(f"  train_jsonl: {train_jsonl.resolve()} (rows={row_count})")
    print(f"  output_dir: {output_dir.resolve()}")
    print(f"  seed: {hyperparams.seed}")
    print(f"  num_train_epochs: {hyperparams.num_train_epochs}")
    print(f"  learning_rate: {hyperparams.learning_rate}")
    print(f"  lr_scheduler_type: {hyperparams.lr_scheduler_type}")
    print(f"  warmup_ratio: {hyperparams.warmup_ratio}")
    print(
        f"  per_device_train_batch_size: {hyperparams.per_device_train_batch_size}"
    )
    print(
        f"  gradient_accumulation_steps: {hyperparams.gradient_accumulation_steps}"
    )
    print(f"  max_seq_length: {hyperparams.max_seq_length}")
    # Explicit TRL assistant/completion masking flag (must stay True).
    print(f"  assistant_only_loss: {hyperparams.assistant_only_loss}")
    print(
        f"  lora: r={hyperparams.lora_r} alpha={hyperparams.lora_alpha} "
        f"dropout={hyperparams.lora_dropout} "
        f"targets={list(hyperparams.lora_target_modules)}"
    )
    print(f"  wandb_project: {hyperparams.wandb_project}")
    print(f"  precision: bf16 (no 4-bit quant)")


def run_training(
    train_jsonl: Path,
    output_dir: Path,
    hyperparams: TrainHyperparams,
    max_steps: int | None,
) -> None:
    """Execute LoRA SFT on chat_train only."""
    hf_token = _require_hf_token()
    wandb_key = _require_wandb_api_key()
    os.environ["WANDB_API_KEY"] = wandb_key
    os.environ["WANDB_PROJECT"] = hyperparams.wandb_project

    _set_seeds(hyperparams.seed)

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(
        hyperparams.model_id,
        token=hf_token,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        hyperparams.model_id,
        token=hf_token,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )

    peft_config = LoraConfig(
        r=hyperparams.lora_r,
        lora_alpha=hyperparams.lora_alpha,
        lora_dropout=hyperparams.lora_dropout,
        bias=hyperparams.lora_bias,
        task_type=hyperparams.lora_task_type,
        target_modules=list(hyperparams.lora_target_modules),
    )

    train_rows = _load_chat_messages(train_jsonl)
    train_dataset = Dataset.from_list(train_rows)

    sft_kwargs: dict = {
        "output_dir": str(output_dir),
        "num_train_epochs": hyperparams.num_train_epochs,
        "learning_rate": hyperparams.learning_rate,
        "lr_scheduler_type": hyperparams.lr_scheduler_type,
        "warmup_ratio": hyperparams.warmup_ratio,
        "per_device_train_batch_size": hyperparams.per_device_train_batch_size,
        "gradient_accumulation_steps": hyperparams.gradient_accumulation_steps,
        "max_length": hyperparams.max_seq_length,
        # Assistant-only loss: compute loss only on assistant turns.
        "assistant_only_loss": hyperparams.assistant_only_loss,
        "bf16": True,
        "logging_steps": 1,
        "save_strategy": "epoch",
        "report_to": ["wandb"],
        "seed": hyperparams.seed,
        "dataset_text_field": None,
    }
    if max_steps is not None:
        sft_kwargs["max_steps"] = int(max_steps)

    sft_config = SFTConfig(**sft_kwargs)

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    output_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Saved adapter to {output_dir.resolve()}")

    adapter_s3_uri = os.environ.get("ADAPTER_S3_URI", "").strip()
    if adapter_s3_uri:
        from experiments.finetune_qwen_model_2026_08_08.src.s3_upload import (
            upload_directory,
        )

        region = os.environ.get("AWS_REGION", "us-east-2")
        upload_directory(output_dir, adapter_s3_uri, region=region)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen3-4B with PEFT LoRA (TRL SFTTrainer)."
    )
    parser.add_argument(
        "--train-jsonl",
        required=True,
        help="Path to chat_train.jsonl (train only).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write the LoRA adapter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate paths and print config; do not download/train.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional smoke override for trainer max_steps.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    train_jsonl = Path(args.train_jsonl)
    output_dir = Path(args.output_dir)
    if not train_jsonl.is_file():
        raise SystemExit(f"train JSONL not found: {train_jsonl}")
    if "chat_test" in train_jsonl.name:
        raise SystemExit("Refusing to train on chat_test.jsonl.")

    hyperparams = default_hyperparams()
    if not hyperparams.assistant_only_loss:
        raise SystemExit("assistant_only_loss must be True.")

    if args.dry_run:
        print_dry_run_config(train_jsonl, output_dir, hyperparams)
        return

    run_training(
        train_jsonl=train_jsonl,
        output_dir=output_dir,
        hyperparams=hyperparams,
        max_steps=args.max_steps,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
