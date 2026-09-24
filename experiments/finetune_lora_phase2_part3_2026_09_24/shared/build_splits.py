"""Build post-level splits and balanced train/test CSVs for Part 3 LoRA fine-tuning.

Run from root: PYTHONPATH=. uv run python experiments/finetune_lora_phase2_part3_2026_09_24/shared/build_splits.py --force
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.src.build_splits import (
    RANDOM_SEED as P_RANDOM_SEED,
    TRAIN_FRACTION as P_TRAIN_FRACTION,
    balance_keep_remove,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_ROOT / "data"
RANDOM_SEED = P_RANDOM_SEED
TRAIN_FRACTION = P_TRAIN_FRACTION
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
    """Assign each modal post to train or test (stratified by modal label).

    Parameters
    ----------
    modal_df
        Modal keep/remove label frame.
    unanimous_post_ids
        Post ids present in the unanimous-min3 label CSV.
    train_fraction
        Fraction of each class assigned to train (integer cut).
    seed
        Shuffle seed within each class.

    Returns
    -------
    pd.DataFrame
        Manifest with ``post_id``, ``split``, ``modal_label``, ``in_unanimous``.
    """
    decisions = modal_df["decision"].astype(str).str.lower().str.strip()
    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    for label in ("keep", "remove"):
        class_df = modal_df.loc[decisions == label].sample(
            frac=1.0,
            random_state=seed,
        )
        n_class = len(class_df)
        n_train = int(train_fraction * n_class)
        train_parts.append(class_df.iloc[:n_train])
        test_parts.append(class_df.iloc[n_train:])
    assigned = pd.concat(
        [
            pd.concat(train_parts, ignore_index=True).assign(split="train"),
            pd.concat(test_parts, ignore_index=True).assign(split="test"),
        ],
        ignore_index=True,
    )
    manifest = pd.DataFrame(
        {
            "post_id": assigned["message_id"].astype(str),
            "split": assigned["split"],
            "modal_label": assigned["decision"]
            .astype(str)
            .str.lower()
            .str.strip(),
            "in_unanimous": assigned["message_id"]
            .astype(str)
            .isin(unanimous_post_ids),
        }
    )
    return manifest.reset_index(drop=True)


def write_split_manifest(manifest_df: pd.DataFrame, output_path: Path, force: bool) -> None:
    """Write ``split_manifest.csv``.

    Parameters
    ----------
    manifest_df
        Post-level split manifest.
    output_path
        Destination CSV path.
    force
        Overwrite when True.
    """
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {output_path}; pass --force."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_df.to_csv(output_path, index=False)


def balance_split_posts(
    label_df: pd.DataFrame,
    post_ids: set[str],
    seed: int,
) -> pd.DataFrame:
    """Balance rows for posts in ``post_ids`` using all removes plus sampled keeps.

    Parameters
    ----------
    label_df
        Label frame with ``message_id`` and ``decision``.
    post_ids
        Posts to include in this split.
    seed
        Sampling seed.

    Returns
    -------
    pd.DataFrame
        Balanced frame with required output columns.
    """
    split_df = label_df.loc[label_df["message_id"].astype(str).isin(post_ids)].copy()
    balanced = balance_keep_remove(split_df, seed=seed)
    return balanced[list(REQUIRED_COLUMNS)].reset_index(drop=True)


def _validate_split_frame(frame: pd.DataFrame, name: str) -> None:
    """Require required columns, unique ``message_id``, and balanced keep/remove.

    Parameters
    ----------
    frame
        Split frame to validate.
    name
        Label used in ``ValueError`` messages.

    Raises
    ------
    ValueError
        If columns are missing, ids repeat, or keep/remove counts differ.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")
    if not frame["message_id"].is_unique:
        raise ValueError(f"{name} has duplicate message_id values")
    decisions = frame["decision"].astype(str).str.lower().str.strip()
    n_keep = int((decisions == "keep").sum())
    n_remove = int((decisions == "remove").sum())
    if n_keep != n_remove:
        raise ValueError(
            f"{name} is not balanced: keep={n_keep} remove={n_remove}"
        )


def sample_experiment_three_train(
    exp2_train_df: pd.DataFrame,
    exp1_train_df: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    """Sample modal train rows to match Experiment 1 balanced counts.

    Parameters
    ----------
    exp2_train_df
        Balanced modal train frame.
    exp1_train_df
        Balanced unanimous train frame (target counts).
    seed
        Sampling seed.

    Returns
    -------
    pd.DataFrame
        Size-matched balanced modal train frame.
    """
    exp1_decisions = exp1_train_df["decision"].astype(str).str.lower().str.strip()
    n_remove = int((exp1_decisions == "remove").sum())
    n_keep = int((exp1_decisions == "keep").sum())
    exp2_decisions = exp2_train_df["decision"].astype(str).str.lower().str.strip()
    remove_pool = exp2_train_df.loc[exp2_decisions == "remove"]
    keep_pool = exp2_train_df.loc[exp2_decisions == "keep"]
    if len(remove_pool) < n_remove:
        raise ValueError(
            f"Need {n_remove} remove rows but only found {len(remove_pool)}."
        )
    if len(keep_pool) < n_keep:
        raise ValueError(
            f"Need {n_keep} keep rows but only found {len(keep_pool)}."
        )
    remove_sample = remove_pool.sample(n=n_remove, random_state=seed, replace=False)
    keep_sample = keep_pool.sample(n=n_keep, random_state=seed, replace=False)
    sampled = pd.concat([remove_sample, keep_sample], ignore_index=True)
    return sampled[list(REQUIRED_COLUMNS)].reset_index(drop=True)


def write_split_csv(
    frame: pd.DataFrame,
    output_path: Path,
    force: bool,
) -> None:
    """Validate and write one train or test CSV.

    Parameters
    ----------
    frame
        Balanced split frame.
    output_path
        Destination CSV path.
    force
        Overwrite when True.
    """
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {output_path}; pass --force."
        )
    _validate_split_frame(frame, output_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame[list(REQUIRED_COLUMNS)].to_csv(output_path, index=False)


def build_and_write_splits(force: bool, seed: int) -> SplitCounts:
    """Load labels, split posts, balance, and write all CSV outputs.

    Parameters
    ----------
    force
        Overwrite existing outputs when True.
    seed
        Random seed for splitting, balancing, and sampling.

    Returns
    -------
    SplitCounts
        Row counts for each written output.
    """
    modal_df = load_dataset(STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS, low_memory=False)
    unanimous_df = load_dataset(
        STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3,
        low_memory=False,
    )
    unanimous_post_ids = set(unanimous_df["message_id"].astype(str))
    manifest = post_level_split(
        modal_df,
        unanimous_post_ids,
        train_fraction=TRAIN_FRACTION,
        seed=seed,
    )
    manifest_path = DATA_DIR / "split_manifest.csv"
    write_split_manifest(manifest, manifest_path, force=force)

    train_ids = set(manifest.loc[manifest["split"] == "train", "post_id"])
    test_ids = set(manifest.loc[manifest["split"] == "test", "post_id"])

    exp1_train = balance_split_posts(unanimous_df, train_ids, seed=seed)
    exp2_train = balance_split_posts(modal_df, train_ids, seed=seed)
    test_unanimous = balance_split_posts(unanimous_df, test_ids, seed=seed)
    test_modal = balance_split_posts(modal_df, test_ids, seed=seed)
    exp3_train = sample_experiment_three_train(exp2_train, exp1_train, seed=seed)

    outputs = {
        DATA_DIR / "test_unanimous.csv": test_unanimous,
        DATA_DIR / "test_modal.csv": test_modal,
        EXPERIMENT_ROOT / "experiment1_unanimous/data/train.csv": exp1_train,
        EXPERIMENT_ROOT / "experiment2_modal/data/train.csv": exp2_train,
        EXPERIMENT_ROOT
        / "experiment3_modal_size_matched/data/train.csv": exp3_train,
    }
    for output_path, frame in outputs.items():
        write_split_csv(frame, output_path, force=force)

    return SplitCounts(
        modal_posts=len(modal_df),
        unanimous_posts=len(unanimous_df),
        exp1_train_rows=len(exp1_train),
        exp2_train_rows=len(exp2_train),
        exp3_train_rows=len(exp3_train),
        test_unanimous_rows=len(test_unanimous),
        test_modal_rows=len(test_modal),
    )


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
