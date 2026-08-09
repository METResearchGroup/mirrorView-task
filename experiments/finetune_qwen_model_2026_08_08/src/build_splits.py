"""Build balanced keep/remove train/test CSV splits for Qwen LoRA fine-tuning.

Loads ``STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3``, keeps all
remove rows, samples an equal number of keep rows (``seed=1``), then does a
per-class 80/20 split so both splits stay 1:1.

Run from root: PYTHONPATH=. uv run python experiments/finetune_qwen_model_2026_08_08/src/build_splits.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3

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
)


def balance_keep_remove(source_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Return all removes plus an equal random sample of keeps.

    Parameters
    ----------
    source_df
        Unanimous min-3 keep/remove frame.
    seed
        Sampling seed.

    Returns
    -------
    pd.DataFrame
        Balanced frame with equal keep and remove counts.
    """
    decisions = source_df["decision"].astype(str).str.lower().str.strip()
    remove_df = source_df.loc[decisions == "remove"].copy()
    keep_df = source_df.loc[decisions == "keep"].copy()
    n_remove = len(remove_df)
    if n_remove == 0:
        raise ValueError("Source dataset has zero remove rows.")
    if len(keep_df) < n_remove:
        raise ValueError(
            f"Need {n_remove} keep rows but only found {len(keep_df)}."
        )
    keep_sampled = keep_df.sample(n=n_remove, random_state=seed, replace=False)
    balanced = pd.concat([remove_df, keep_sampled], ignore_index=True)
    return balanced


def stratified_balanced_split(
    balanced_df: pd.DataFrame,
    train_fraction: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split each class independently so train/test stay class-balanced.

    Parameters
    ----------
    balanced_df
        Class-balanced keep/remove frame.
    train_fraction
        Fraction of each class assigned to train (integer cut).
    seed
        Shuffle seed within each class.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        ``(train_df, test_df)``.
    """
    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    decisions = balanced_df["decision"].astype(str).str.lower().str.strip()
    for label in ("keep", "remove"):
        class_df = balanced_df.loc[decisions == label].sample(
            frac=1.0,
            random_state=seed,
        )
        n_class = len(class_df)
        n_train = int(train_fraction * n_class)
        train_parts.append(class_df.iloc[:n_train])
        test_parts.append(class_df.iloc[n_train:])
    train_df = (
        pd.concat(train_parts, ignore_index=True)
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )
    test_df = (
        pd.concat(test_parts, ignore_index=True)
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )
    return train_df, test_df


def _validate_outputs(train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
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
    """Load registry data, balance, split, and write CSVs.

    Parameters
    ----------
    output_dir
        Destination directory for ``train.csv`` / ``test.csv``.
    seed
        Random seed for sampling and splitting.
    force
        Overwrite existing outputs when True.
    """
    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    if not force and (train_path.exists() or test_path.exists()):
        raise FileExistsError(
            f"Refusing to overwrite existing splits in {output_dir}; pass --force."
        )
    source_df = load_dataset(
        STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3,
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
        description="Build balanced keep/remove train/test CSV splits."
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
