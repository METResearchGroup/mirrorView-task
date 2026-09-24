"""Create chat JSONL files from Part 3 split CSVs.

Reuses chat helpers from ``experiments.finetune_qwen_model_2026_08_08``.

Run from root: PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.src.create_chat_dataset import (
    row_to_chat_record,
    write_chat_jsonl,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"

CHAT_OUTPUTS = (
    (EXPERIMENT_ROOT / "experiment1_unanimous/data/train.csv", EXPERIMENT_ROOT / "experiment1_unanimous/data/chat_train.jsonl"),
    (EXPERIMENT_ROOT / "experiment2_modal/data/train.csv", EXPERIMENT_ROOT / "experiment2_modal/data/chat_train.jsonl"),
    (EXPERIMENT_ROOT / "experiment3_modal_size_matched/data/train.csv", EXPERIMENT_ROOT / "experiment3_modal_size_matched/data/chat_train.jsonl"),
    (DATA_DIR / "test_unanimous.csv", DATA_DIR / "chat_test_unanimous.jsonl"),
    (DATA_DIR / "test_modal.csv", DATA_DIR / "chat_test_modal.jsonl"),
)


def create_chat_datasets(force: bool) -> None:
    """Write chat JSONL for all train and shared test CSVs.

    Parameters
    ----------
    force
        Overwrite existing JSONL outputs when True.
    """
    for csv_path, jsonl_path in CHAT_OUTPUTS:
        if not csv_path.is_file():
            raise FileNotFoundError(csv_path)
        row_count = write_chat_jsonl(csv_path, jsonl_path, force=force)
        print(f"Wrote {jsonl_path} ({row_count} rows)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Create chat JSONL files from Part 3 split CSVs."
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
    create_chat_datasets(force=bool(args.force))


if __name__ == "__main__":
    main()
