"""Build post-level splits and balanced train/test CSVs for Part 3 LoRA fine-tuning.

Run from root: PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py --force
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"
RANDOM_SEED = 1
TRAIN_FRACTION = 0.8
REQUIRED_COLUMNS = (
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
)


@dataclass(frozen=True)
class SplitCounts:
    """Row counts produced by ``build_and_write_splits``."""

    modal_posts: int
    unanimous_posts: int
    exp1_train_rows: int
    exp2_train_rows: int
    exp3_train_rows: int
    test_unanimous_rows: int
    test_modal_rows: int


def post_level_split(
    modal_df: pd.DataFrame,
    unanimous_post_ids: set[str],
    train_fraction: float,
    seed: int,
) -> pd.DataFrame:
    """Assign each modal post to train or test (stratified by modal label)."""
    ...


def write_split_manifest(manifest_df: pd.DataFrame, output_path: Path, force: bool) -> None:
    """Write ``split_manifest.csv``."""
    ...


def balance_split_posts(
    label_df: pd.DataFrame,
    post_ids: set[str],
    seed: int,
) -> pd.DataFrame:
    """Balance rows for posts in ``post_ids`` using all removes plus sampled keeps."""
    ...


def sample_experiment_three_train(
    exp2_train_df: pd.DataFrame,
    exp1_train_df: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    """Sample modal train rows to match Experiment 1 balanced counts."""
    ...


def write_split_csv(
    frame: pd.DataFrame,
    output_path: Path,
    force: bool,
) -> None:
    """Validate and write one train or test CSV."""
    ...


def build_and_write_splits(force: bool, seed: int) -> SplitCounts:
    """Load labels, split posts, balance, and write all CSV outputs."""
    ...


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build post-level splits and balanced train/test CSVs."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CSV outputs.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help="Random seed (default: 1).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    counts = build_and_write_splits(force=bool(args.force), seed=int(args.seed))
    print(f"modal_posts={counts.modal_posts}")
    print(f"unanimous_posts={counts.unanimous_posts}")
    print(f"exp1_train_rows={counts.exp1_train_rows}")
    print(f"exp2_train_rows={counts.exp2_train_rows}")
    print(f"exp3_train_rows={counts.exp3_train_rows}")
    print(f"test_unanimous_rows={counts.test_unanimous_rows}")
    print(f"test_modal_rows={counts.test_modal_rows}")


if __name__ == "__main__":
    main()
