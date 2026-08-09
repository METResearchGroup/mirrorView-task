"""Fine-tune Qwen3-4B-Instruct with PEFT LoRA via the prior experiment helpers.

Uses the same TRL/PEFT path as ``experiments.finetune_qwen_model_2026_08_08``,
with W&B project ``mirrorview-larger-finetune-qwen-2026-08-08``.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/larger_finetune_qwen_model_2026_08_08/train.py \\
      --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \\
      --output-dir /tmp/qwen_lora_larger_out \\
      [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.train import (
    parse_args,
    print_dry_run_config,
    run_training,
)
from experiments.larger_finetune_qwen_model_2026_08_08.src.train_config import (
    default_hyperparams,
)


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
