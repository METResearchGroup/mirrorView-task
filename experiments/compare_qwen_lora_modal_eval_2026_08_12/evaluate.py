"""Score baseline, unanimous LoRA, and modal LoRA preds into RESULTS.md.

Intended CLI (filled in Step 2)::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py \\
      --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \\
      --write-results experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint. Implemented in Step 2."""
    raise NotImplementedError("evaluate.py is implemented in Step 2")


if __name__ == "__main__":
    main(sys.argv[1:])
