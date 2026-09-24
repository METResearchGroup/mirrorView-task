"""Stratified splits and GEPA subset sampling for cohort A.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse
import hashlib
import json
from dataclasses import dataclass
import pandas as pd
from sklearn.model_selection import train_test_split

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import artifacts
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    PAIR_ORDER_SEED,
    aggregate_post_labels,
    attach_pair_order,
    build_cohort_a,
    dedupe_participant_post,
    filter_scored_trials,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import (
    WandbRunSpec,
    init_run,
    log_artifact,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

SPLIT_SEED = 20260924
TEST_FRACTION = 0.20
DEV_FRACTION = 0.10
GEPA_VAL_SIZE = 300
GEPA_VAL_PER_CLASS = 150
GEPA_TRAIN_MAX = 2000
GEPA_TRAIN_PER_CLASS_CAP = 1000
COHORT_PARQUET = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet"
)
SPLIT_HASH_JSON = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/split_hash.json"
)
S3_DATA_KEY = "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / "predict_keep_remove_jev_gepa_2026_09_23"
OUTPUT_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "label",
    "majority_decision",
    "n_raters",
    "n_keep",
    "n_remove",
    "remove_share",
    "is_unanimous",
    "sampled_stance",
    "sample_toxicity_type",
    "post_1_role",
    "post_2_role",
    "split",
    "gepa_subset",
)
# 14,941 was the pre-dedupe probe; dedupe-first cohort A is 14,955 posts.
EXPECTED_COHORT_POSTS = 14955
EXPECTED_COHORT_KEEP = 11775
EXPECTED_COHORT_REMOVE = 3180
EXPECTED_UNANIMOUS = 4939
EXPECTED_TEST = 2991
EXPECTED_DEV = 1496
EXPECTED_GEPA_POOL = 10468
EXPECTED_GEPA_VAL = 300
EXPECTED_GEPA_TRAIN = 2000


@dataclass(frozen=True)
class CohortCounts:
    """Cohort A size summary."""

    n_posts: int
    n_keep: int
    n_remove: int
    n_unanimous: int


@dataclass(frozen=True)
class SplitCounts:
    """Split and GEPA subset sizes."""

    test: int
    dev: int
    gepa_pool: int
    gepa_val: int
    gepa_train: int


def stratify_key(row: pd.Series) -> str:
    """Return f\"{label}:{sampled_stance}:{sample_toxicity_type}\"."""
    return f"{row['label']}:{row['sampled_stance']}:{row['sample_toxicity_type']}"


def assign_splits(cohort: pd.DataFrame, seed: int = SPLIT_SEED) -> pd.DataFrame:
    """Add split column test|dev|gepa_pool using iterative stratified holdout.

    Hold out test at 20%, then dev at 10% of the original cohort (12.5% of remainder).

    Parameters
    ----------
    cohort
        Cohort A frame.
    seed
        Random seed for stratified sampling.

    Returns
    -------
    pandas.DataFrame
        Cohort with a ``split`` column.
    """
    labeled = cohort.copy()
    labeled["_stratify_key"] = labeled.apply(stratify_key, axis=1)
    remainder, test = train_test_split(
        labeled,
        test_size=TEST_FRACTION,
        stratify=labeled["_stratify_key"],
        random_state=seed,
    )
    dev_fraction_of_remainder = DEV_FRACTION / (1.0 - TEST_FRACTION)
    pool, dev = train_test_split(
        remainder,
        test_size=dev_fraction_of_remainder,
        stratify=remainder["_stratify_key"],
        random_state=seed,
    )
    test = test.assign(split="test")
    dev = dev.assign(split="dev")
    pool = pool.assign(split="gepa_pool")
    combined = pd.concat([test, dev, pool], ignore_index=True)
    return combined.drop(columns=["_stratify_key"])


def sample_gepa_subsets(pool: pd.DataFrame, seed: int = SPLIT_SEED) -> pd.DataFrame:
    """From gepa_pool rows add gepa_subset column none|val|train.

    Parameters
    ----------
    pool
        Rows with ``split == 'gepa_pool'``.
    seed
        Random seed for balanced sampling.

    Returns
    -------
    pandas.DataFrame
        Frame with ``gepa_subset`` populated.
    """
    sampled = pool.copy()
    sampled["gepa_subset"] = "none"
    pool_rows = sampled["split"].eq("gepa_pool")
    pool_frame = sampled.loc[pool_rows].copy()
    val_ids: set[str] = set()
    train_ids: set[str] = set()
    for label, per_class_cap in ((0, GEPA_VAL_PER_CLASS), (1, GEPA_VAL_PER_CLASS)):
        class_rows = pool_frame.loc[pool_frame["label"].eq(label)]
        take = min(per_class_cap, len(class_rows))
        if take == 0:
            continue
        chosen = class_rows.sample(n=take, random_state=seed + label)
        val_ids.update(chosen["post_id"].astype(str))
    for label, per_class_cap in ((0, GEPA_TRAIN_PER_CLASS_CAP), (1, GEPA_TRAIN_PER_CLASS_CAP)):
        class_rows = pool_frame.loc[
            pool_frame["label"].eq(label) & ~pool_frame["post_id"].astype(str).isin(val_ids)
        ]
        take = min(per_class_cap, len(class_rows))
        if take == 0:
            continue
        chosen = class_rows.sample(n=take, random_state=seed + 10 + label)
        train_ids.update(chosen["post_id"].astype(str))
    sampled.loc[sampled["post_id"].astype(str).isin(val_ids), "gepa_subset"] = "val"
    sampled.loc[sampled["post_id"].astype(str).isin(train_ids), "gepa_subset"] = "train"
    return sampled


def compute_split_hash(frame: pd.DataFrame) -> str:
    """SHA-256 hex of sorted post_id, split, gepa_subset tuples plus SPLIT_SEED.

    Parameters
    ----------
    frame
        Final cohort frame with split assignments.

    Returns
    -------
    str
        Hex digest.
    """
    tuples = sorted(
        (
            str(row.post_id),
            str(row.split),
            str(row.gepa_subset),
        )
        for row in frame[["post_id", "split", "gepa_subset"]].itertuples(index=False)
    )
    payload = f"{SPLIT_SEED}:{tuples!r}".encode()
    return hashlib.sha256(payload).hexdigest()


def write_outputs(
    frame: pd.DataFrame,
    split_hash: str,
    experiment_dir: Path,
) -> tuple[Path, Path]:
    """Write parquet and split_hash.json with counts and built_at timestamp.

    Parameters
    ----------
    frame
        Final cohort frame.
    split_hash
        Deterministic split hash.
    experiment_dir
        Experiment root directory.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        Parquet and JSON output paths.
    """
    output_dir = experiment_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / COHORT_PARQUET.name
    json_path = output_dir / SPLIT_HASH_JSON.name
    ordered = frame[list(OUTPUT_COLUMNS)].copy()
    ordered.to_parquet(parquet_path, index=False)
    cohort_counts = _cohort_counts_from_frame(frame)
    split_counts = _split_counts_from_frame(frame)
    gepa_subset_counts = frame["gepa_subset"].value_counts().to_dict()
    metadata = {
        "split_seed": SPLIT_SEED,
        "pair_order_seed": PAIR_ORDER_SEED,
        "split_hash": split_hash,
        "cohort_counts": {
            "n_posts": cohort_counts.n_posts,
            "n_keep": cohort_counts.n_keep,
            "n_remove": cohort_counts.n_remove,
            "n_unanimous": cohort_counts.n_unanimous,
        },
        "split_counts": {
            "test": split_counts.test,
            "dev": split_counts.dev,
            "gepa_pool": split_counts.gepa_pool,
            "gepa_val": split_counts.gepa_val,
            "gepa_train": split_counts.gepa_train,
        },
        "gepa_subset_counts": gepa_subset_counts,
        "built_at": get_current_timestamp(),
    }
    json_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return parquet_path, json_path


def upload_data(path: Path) -> str:
    """Call artifacts.upload_under_prefix; return s3 uri.

    Parameters
    ----------
    path
        Local parquet path.

    Returns
    -------
    str
        Uploaded object URI.
    """
    artifacts.upload_under_prefix(path)
    key = str(path.relative_to(REPO_ROOT))
    return f"s3://{artifacts.OUTPUT_S3_BUCKET}/{key}"


def log_splits_artifact(run: object, path: Path) -> None:
    """Log parquet as Wandb artifact name cohort_a_splits type dataset.

    Parameters
    ----------
    run
        Active Wandb run.
    path
        Local parquet path.
    """
    log_artifact(run, path, name="cohort_a_splits", artifact_type="dataset")


def main() -> CohortCounts:
    """Load, build cohort A, assign splits, write, upload, log artifact, print counts.

    Returns
    -------
    CohortCounts
        Cohort A summary counts.
    """
    _require_write_counts_flag()
    from shared.data.dataloader import load_dataset
    from shared.data.registry import STUDY_PHASE_2_PART_3_RESULTS_FULL

    raw = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)
    trials = filter_scored_trials(raw)
    trials = dedupe_participant_post(trials)
    agg = aggregate_post_labels(trials)
    cohort = build_cohort_a(agg)
    cohort = attach_pair_order(cohort)
    cohort_counts = _cohort_counts_from_frame(cohort)
    split_frame = assign_splits(cohort, SPLIT_SEED)
    split_frame = sample_gepa_subsets(split_frame, SPLIT_SEED)
    split_hash = compute_split_hash(split_frame)
    parquet_path, _json_path = write_outputs(split_frame, split_hash, EXPERIMENT_DIR)
    split_counts = _split_counts_from_frame(split_frame)
    _print_counts(cohort_counts, split_counts, split_hash)
    if not _counts_match_expected(cohort_counts, split_counts):
        print("counts differ from frozen acceptance targets; outputs written with actuals")
        return cohort_counts
    s3_uri = upload_data(parquet_path)
    print(f"s3_uri={s3_uri}")
    run = init_run(
        WandbRunSpec(
            group="jev_baseline",
            name="build_splits",
            job_type="score",
            config={"split_hash": split_hash, "split_seed": SPLIT_SEED},
        )
    )
    log_splits_artifact(run, parquet_path)
    run.finish()
    return cohort_counts


def _cohort_counts_from_frame(frame: pd.DataFrame) -> CohortCounts:
    return CohortCounts(
        n_posts=len(frame),
        n_keep=int((frame["label"] == 0).sum()),
        n_remove=int((frame["label"] == 1).sum()),
        n_unanimous=int(frame["is_unanimous"].sum()),
    )


def _split_counts_from_frame(frame: pd.DataFrame) -> SplitCounts:
    return SplitCounts(
        test=int((frame["split"] == "test").sum()),
        dev=int((frame["split"] == "dev").sum()),
        gepa_pool=int((frame["split"] == "gepa_pool").sum()),
        gepa_val=int((frame["gepa_subset"] == "val").sum()),
        gepa_train=int((frame["gepa_subset"] == "train").sum()),
    )


def _counts_match_expected(cohort_counts: CohortCounts, split_counts: SplitCounts) -> bool:
    return (
        cohort_counts.n_posts == EXPECTED_COHORT_POSTS
        and cohort_counts.n_keep == EXPECTED_COHORT_KEEP
        and cohort_counts.n_remove == EXPECTED_COHORT_REMOVE
        and cohort_counts.n_unanimous == EXPECTED_UNANIMOUS
        and split_counts.test == EXPECTED_TEST
        and split_counts.dev == EXPECTED_DEV
        and split_counts.gepa_pool == EXPECTED_GEPA_POOL
        and split_counts.gepa_val == EXPECTED_GEPA_VAL
        and split_counts.gepa_train == EXPECTED_GEPA_TRAIN
    )


def _print_counts(
    cohort_counts: CohortCounts,
    split_counts: SplitCounts,
    split_hash: str,
) -> None:
    print(f"cohort_a_posts={cohort_counts.n_posts}")
    print(f"cohort_a_keep={cohort_counts.n_keep}")
    print(f"cohort_a_remove={cohort_counts.n_remove}")
    print(f"unanimous_posts={cohort_counts.n_unanimous}")
    print(f"test={split_counts.test}")
    print(f"dev={split_counts.dev}")
    print(f"gepa_pool={split_counts.gepa_pool}")
    print(f"gepa_val={split_counts.gepa_val}")
    print(f"gepa_train={split_counts.gepa_train}")
    print(f"split_hash={split_hash}")


def _require_write_counts_flag() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-counts", action="store_true")
    args = parser.parse_args()
    if not args.write_counts:
        parser.error("pass --write-counts")


if __name__ == "__main__":
    main()
