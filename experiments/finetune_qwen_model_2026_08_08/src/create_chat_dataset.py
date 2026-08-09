"""Create chat JSONL files from balanced train/test CSVs.

Each line is ``{"message_id", "messages": [system, user, assistant]}`` with
assistant content equal to the gold ``decision`` (``keep`` or ``remove``).

Run from root: PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py --force
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.src.prompt import (
    SYSTEM_CONTENT,
    generate_user_prompt,
)

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
    decision = str(row["decision"]).lower().strip()
    if decision not in {"keep", "remove"}:
        raise ValueError(f"Unexpected decision={decision!r} for {row['message_id']}")
    user_content = generate_user_prompt(
        post_1_text=str(row["original_text"]),
        post_2_text=str(row["mirror_text"]),
    )
    if "Allow Or Remove?" in user_content:
        raise ValueError("Vendored prompt still contains study closing line.")
    return {
        "message_id": str(row["message_id"]),
        "messages": [
            {"role": "system", "content": SYSTEM_CONTENT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": decision},
        ],
    }


def write_chat_jsonl(csv_path: Path, jsonl_path: Path, force: bool) -> int:
    """Convert a split CSV to chat JSONL.

    Parameters
    ----------
    csv_path
        Source ``train.csv`` or ``test.csv``.
    jsonl_path
        Destination JSONL path.
    force
        Overwrite when True.

    Returns
    -------
    int
        Number of rows written.
    """
    if jsonl_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {jsonl_path}; pass --force."
        )
    frame = pd.read_csv(csv_path)
    records = [row_to_chat_record(row) for _, row in frame.iterrows()]
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


def create_chat_datasets(data_dir: Path, force: bool) -> None:
    """Write ``chat_train.jsonl`` and ``chat_test.jsonl`` under ``data_dir``."""
    mapping = (
        ("train.csv", "chat_train.jsonl"),
        ("test.csv", "chat_test.jsonl"),
    )
    for csv_name, jsonl_name in mapping:
        csv_path = data_dir / csv_name
        if not csv_path.is_file():
            raise FileNotFoundError(csv_path)
        n = write_chat_jsonl(csv_path, data_dir / jsonl_name, force=force)
        print(f"Wrote {data_dir / jsonl_name} ({n} rows)")


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
