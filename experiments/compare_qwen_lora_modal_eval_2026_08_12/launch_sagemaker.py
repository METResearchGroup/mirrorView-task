"""Launch SageMaker adapter inference for the unanimous LoRA on modal data.

Intended CLI (filled in Step 3)::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \\
      --mode infer_unanimous_adapter [--dry-run] [--wait]
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint. Implemented in Step 3."""
    raise NotImplementedError("launch_sagemaker.py is implemented in Step 3")


if __name__ == "__main__":
    main(sys.argv[1:])
