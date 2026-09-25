"""Merge a LoRA adapter into Qwen3.5 4B and save full weights for vLLM.

Run from root::

    PYTHONPATH=. uv run python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/merge_adapter.py \\
      --adapter-dir /path/to/adapter --merged-dir /path/to/merged
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import (
    MODEL_ID,
)


def _require_hf_token() -> str:
    """Return HF_TOKEN or exit."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is required but missing or empty.")
    return token


def merge_adapter_to_dir(
    model_id: str,
    adapter_dir: Path,
    merged_dir: Path,
    hf_token: str,
) -> None:
    """Load base weights, apply the adapter, merge, and save.

    Parameters
    ----------
    model_id
        Hugging Face model id for the base checkpoint.
    adapter_dir
        Local directory with PEFT adapter weights.
    merged_dir
        Destination directory for merged model + tokenizer.
    hf_token
        Hugging Face API token for gated models.
    """
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    merged_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        token=hf_token,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16
    device_map = "auto" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=hf_token,
        torch_dtype=dtype,
        trust_remote_code=True,
        device_map=device_map,
    )
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    model = model.merge_and_unload()
    model.save_pretrained(str(merged_dir))
    tokenizer.save_pretrained(str(merged_dir))
    print(f"Wrote merged model to {merged_dir}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Merge a LoRA adapter into the base model for vLLM serving."
    )
    parser.add_argument(
        "--model-id",
        default=MODEL_ID,
        help=f"Hugging Face base model id (default: {MODEL_ID}).",
    )
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        required=True,
        help="Local PEFT adapter directory.",
    )
    parser.add_argument(
        "--merged-dir",
        type=Path,
        required=True,
        help="Output directory for merged weights and tokenizer.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    hf_token = _require_hf_token()
    merge_adapter_to_dir(
        model_id=str(args.model_id),
        adapter_dir=args.adapter_dir,
        merged_dir=args.merged_dir,
        hf_token=hf_token,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
