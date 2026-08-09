"""Build balanced keep/remove train/test CSV splits from modal labels.

Loads ``STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS``, then reuses balance/split
helpers from ``experiments.finetune_qwen_model_2026_08_08``.

Run from root: PYTHONPATH=. uv run python experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.finetune_qwen_model_2026_08_08.src.build_splits import (
    RANDOM_SEED,
    TRAIN_FRACTION,
    balance_keep_remove,
    stratified_balanced_split,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"
REQUIRED_COLUMNS = (
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
)


def _validate_outputs(train_df, test_df) -> None:
    """Raise if split contracts are violated."""
    for name, frame in (("train", train_df), ("test", test_df)):
        missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
        if missing:
            raise ValueError(f"{name} missing columns: {missing}")
        if not frame["message_id"].is_unique:
            raise ValueError(f"{name} has duplicate message_id values")
        dec = frame["decision"].astype(str).str.lower().str.strip()
        n_keep = int((dec == "keep").sum())
        n_remove = int((dec == "remove").sum())
        if n_keep != n_remove:
            raise ValueError(
                f"{name} is not balanced: keep={n_keep} remove={n_remove}"
            )


def build_and_write_splits(output_dir: Path, seed: int, force: bool) -> None:
    """Load modal labels, balance, split, and write CSVs."""
    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    if not force and (train_path.exists() or test_path.exists()):
        raise FileExistsError(
            f"Refusing to overwrite existing splits in {output_dir}; pass --force."
        )
    source_df = load_dataset(
        STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS,
        low_memory=False,
    )
    balanced = balance_keep_remove(source_df, seed=seed)
    train_df, test_df = stratified_balanced_split(
        balanced,
        train_fraction=TRAIN_FRACTION,
        seed=seed,
    )
    _validate_outputs(train_df, test_df)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    print(f"Wrote {train_path} ({len(train_df)} rows)")
    print(f"Wrote {test_path} ({len(test_df)} rows)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build balanced modal keep/remove train/test CSV splits."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DATA_DIR),
        help="Directory for train.csv and test.csv.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help="Random seed (default: 1).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CSV outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    build_and_write_splits(
        output_dir=Path(args.output_dir),
        seed=int(args.seed),
        force=bool(args.force),
    )


if __name__ == "__main__":
    main()
