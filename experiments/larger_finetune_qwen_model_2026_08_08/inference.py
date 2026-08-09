"""Run greedy keep/remove inference by wrapping the prior experiment CLI.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/larger_finetune_qwen_model_2026_08_08/inference.py \\
      --chat-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_test.jsonl \\
      --output-csv /tmp/larger_test_labels.csv \\
      --mode baseline
"""

from __future__ import annotations

import sys

from experiments.finetune_qwen_model_2026_08_08.inference import main as _prior_main


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint that delegates to the prior inference implementation."""
    _prior_main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
