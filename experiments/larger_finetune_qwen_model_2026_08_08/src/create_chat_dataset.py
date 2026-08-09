"""Create chat JSONL files from balanced train/test CSVs.

Reuses chat helpers from ``experiments.finetune_qwen_model_2026_08_08``.

Run from root: PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.src.create_chat_dataset import (
    create_chat_datasets,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Create chat_train.jsonl and chat_test.jsonl from CSV splits."
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help="Directory containing train.csv / test.csv.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing JSONL outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    create_chat_datasets(data_dir=Path(args.data_dir), force=bool(args.force))


if __name__ == "__main__":
    main()
