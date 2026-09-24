"""Create chat JSONL files from Part 3 split CSVs.

Reuses chat helpers from ``experiments.finetune_qwen_model_2026_08_08``.

Run from root: PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/create_chat_dataset.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"


def row_to_chat_record(row: pd.Series) -> dict:
    """Build one chat JSONL record from a split CSV row.

    Parameters
    ----------
    row
        Row with ``message_id``, ``original_text``, ``mirror_text``, ``decision``.

    Returns
    -------
    dict
        Chat record with ``message_id`` and three-role ``messages``.
    """
    raise NotImplementedError


def write_chat_jsonl(csv_path: Path, jsonl_path: Path, force: bool) -> int:
    """Convert a split CSV to chat JSONL.

    Parameters
    ----------
    csv_path
        Source train or test CSV.
    jsonl_path
        Destination JSONL path.
    force
        Overwrite when True.

    Returns
    -------
    int
        Number of rows written.
    """
    raise NotImplementedError


def create_chat_datasets(force: bool) -> None:
    """Write chat JSONL for all train and shared test CSVs.

    Parameters
    ----------
    force
        Overwrite existing JSONL outputs when True.
    """
    raise NotImplementedError


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
