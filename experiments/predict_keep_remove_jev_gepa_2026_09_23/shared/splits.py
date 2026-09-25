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
    CohortSource,
    PAIR_ORDER_SEED,
    aggregate_post_labels,
    apply_union_strata_exclusion,
    attach_pair_order,
    attach_part3_overlap_flags,
    build_cohort_a,
    build_scored_trials,
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
COHORT_UNION_PARQUET = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_union_splits.parquet"
)
SPLIT_HASH_JSON = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/split_hash.json"
)
COHORT_UNION_SPLIT_HASH_JSON = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_union_split_hash.json"
)
S3_DATA_KEY = "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet"
S3_UNION_DATA_KEY = (
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_union_splits.parquet"
)
PART3_FROZEN_SPLIT_HASH = (
    "f13300f6ca6e71147b97fbc67a0e3d4e90c5cd4a554f1fc4694a10eb178a541b"
)
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
    "n_raters_part2",
    "n_raters_part3",
    "remove_share",
    "is_unanimous",
    "sampled_stance",
    "sample_toxicity_type",
    "post_1_role",
    "post_2_role",
    "in_part3_cohort_a",
    "label_changed_vs_part3",
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
EXPECTED_UNION_COHORT_POSTS = 19219
EXPECTED_UNION_COHORT_KEEP = 15210
EXPECTED_UNION_COHORT_REMOVE = 4009
EXPECTED_UNION_EXCLUDED_STRATA = 0
EXPECTED_UNION_TEST = 3841
EXPECTED_UNION_DEV = 1927
EXPECTED_UNION_GEPA_POOL = 13451
EXPECTED_UNION_GEPA_VAL = 300
EXPECTED_UNION_GEPA_TRAIN = 2000


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


@dataclass(frozen=True)
class UnionBuildReport:
    """Union cohort overlap and GEPA refresh summary."""

    n_excluded_strata: int
    excluded_keep: int
    excluded_remove: int
    n_stance_disagreements: int
    n_toxicity_disagreements: int
    n_overlap_part3: int
    n_label_changed: int
    n_dropped_from_part3: int
    n_new_posts: int
    n_shared_test_posts: int
    val_members_changed: int
    train_members_changed: int


@dataclass(frozen=True)
class GepaChangeReport:
    """How many GEPA val or train members differ from the frozen Part 3 pick."""

    val_members_changed: int
    train_members_changed: int


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


def assign_nested_splits(
    cohort: pd.DataFrame,
    frozen: pd.DataFrame,
    seed: int = SPLIT_SEED,
) -> pd.DataFrame:
    """Preserve frozen split assignments for overlap; stratify only new posts."""
    tagged = cohort.copy()
    tagged["post_id"] = tagged["post_id"].astype(str)
    frozen_lookup = frozen.copy()
    frozen_lookup["post_id"] = frozen_lookup["post_id"].astype(str)
    frozen_index = frozen_lookup.set_index("post_id")
    overlap_mask = tagged["post_id"].isin(frozen_index.index)
    preserved = tagged.loc[overlap_mask].copy()
    preserved["split"] = preserved["post_id"].map(frozen_index["split"])
    preserved["gepa_subset"] = preserved["post_id"].map(frozen_index["gepa_subset"])
    new_posts = tagged.loc[~overlap_mask].drop(columns=["split", "gepa_subset"], errors="ignore")
    if len(new_posts):
        if len(new_posts) < 2:
            new_posts = new_posts.assign(split="gepa_pool", gepa_subset="none")
        else:
            new_posts = assign_splits(new_posts, seed=seed)
            new_posts["gepa_subset"] = "none"
    else:
        new_posts = tagged.iloc[0:0].copy()
        new_posts["split"] = pd.Series(dtype="object")
        new_posts["gepa_subset"] = "none"
    combined = pd.concat([preserved, new_posts], ignore_index=True)
    combined["gepa_subset"] = combined["gepa_subset"].fillna("none")
    return combined


def _retained_gepa_ids(
    frame: pd.DataFrame,
    frozen: pd.DataFrame,
    subset: str,
) -> set[str]:
    pool_ids = set(frame.loc[frame["split"].eq("gepa_pool"), "post_id"].astype(str))
    labels = frame.set_index(frame["post_id"].astype(str))["label"]
    retained: set[str] = set()
    frozen_rows = frozen.loc[frozen["gepa_subset"].eq(subset)]
    for post_id in frozen_rows["post_id"].astype(str):
        if post_id not in pool_ids:
            continue
        frozen_label = int(frozen_rows.loc[frozen_rows["post_id"].astype(str) == post_id, "label"].iloc[0])
        if int(labels.loc[post_id]) != frozen_label:
            continue
        retained.add(post_id)
    return retained


def retain_and_top_up_gepa_subsets(
    frame: pd.DataFrame,
    frozen: pd.DataFrame,
    seed: int = SPLIT_SEED,
) -> tuple[pd.DataFrame, GepaChangeReport]:
    """Keep valid frozen GEPA picks and top up val and train to balanced caps."""
    val_ids = _retained_gepa_ids(frame, frozen, "val")
    train_ids = _retained_gepa_ids(frame, frozen, "train")
    frozen_val = set(frozen.loc[frozen["gepa_subset"].eq("val"), "post_id"].astype(str))
    frozen_train = set(frozen.loc[frozen["gepa_subset"].eq("train"), "post_id"].astype(str))
    result = _apply_gepa_ids(frame, seed, val_ids, train_ids)
    final_val = set(result.loc[result["gepa_subset"].eq("val"), "post_id"].astype(str))
    final_train = set(result.loc[result["gepa_subset"].eq("train"), "post_id"].astype(str))
    report = GepaChangeReport(
        val_members_changed=len(frozen_val.symmetric_difference(final_val)),
        train_members_changed=len(frozen_train.symmetric_difference(final_train)),
    )
    return result, report


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
    return _apply_gepa_ids(pool, seed, set(), set())


def _apply_gepa_ids(
    pool: pd.DataFrame,
    seed: int,
    val_ids: set[str],
    train_ids: set[str],
) -> pd.DataFrame:
    sampled = pool.copy()
    sampled["gepa_subset"] = "none"
    pool_frame = sampled.loc[sampled["split"].eq("gepa_pool")].copy()
    labels_by_id = pool_frame.set_index(pool_frame["post_id"].astype(str))["label"]
    val_ids = {post_id for post_id in val_ids if post_id in labels_by_id.index}
    train_ids = {post_id for post_id in train_ids if post_id in labels_by_id.index}
    for label, per_class_cap in ((0, GEPA_VAL_PER_CLASS), (1, GEPA_VAL_PER_CLASS)):
        current = sum(1 for post_id in val_ids if int(labels_by_id.get(post_id, -1)) == label)
        need = per_class_cap - current
        if need <= 0:
            continue
        class_rows = pool_frame.loc[
            pool_frame["label"].eq(label)
            & ~pool_frame["post_id"].astype(str).isin(val_ids | train_ids)
        ]
        take = min(need, len(class_rows))
        if take == 0:
            continue
        chosen = class_rows.sample(n=take, random_state=seed + label)
        val_ids.update(chosen["post_id"].astype(str))
    for label, per_class_cap in ((0, GEPA_TRAIN_PER_CLASS_CAP), (1, GEPA_TRAIN_PER_CLASS_CAP)):
        current = sum(1 for post_id in train_ids if int(labels_by_id.get(post_id, -1)) == label)
        need = per_class_cap - current
        if need <= 0:
            continue
        class_rows = pool_frame.loc[
            pool_frame["label"].eq(label)
            & ~pool_frame["post_id"].astype(str).isin(val_ids | train_ids)
        ]
        take = min(need, len(class_rows))
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
    parquet_filename: str,
    json_filename: str,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    """Write parquet and JSON metadata with counts and built_at timestamp.

    Parameters
    ----------
    frame
        Final cohort frame.
    split_hash
        Deterministic split hash.
    experiment_dir
        Experiment root directory.
    parquet_filename
        Parquet file name under ``data/``.
    json_filename
        JSON metadata file name under ``data/``.
    extra_metadata
        Optional extra keys merged into the JSON payload.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        Parquet and JSON output paths.
    """
    output_dir = experiment_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / parquet_filename
    json_path = output_dir / json_filename
    ordered = frame[list(OUTPUT_COLUMNS)].copy()
    ordered.to_parquet(parquet_path, index=False)
    cohort_counts = _cohort_counts_from_frame(frame)
    split_counts = _split_counts_from_frame(frame)
    gepa_subset_counts = frame["gepa_subset"].value_counts().to_dict()
    metadata: dict[str, object] = {
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
    if extra_metadata:
        metadata.update(extra_metadata)
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


def log_union_splits_artifact(run: object, path: Path) -> None:
    """Log parquet as Wandb artifact name cohort_union_splits type dataset."""
    log_artifact(run, path, name="cohort_union_splits", artifact_type="dataset")


def load_frozen_part3_splits(experiment_dir: Path) -> pd.DataFrame:
    """Load the frozen Part 3 cohort split parquet."""
    path = experiment_dir / "data" / COHORT_PARQUET.name
    if not path.is_file():
        raise FileNotFoundError(f"missing frozen cohort splits at {path}")
    return pd.read_parquet(path)


def build_part3_split_frame() -> pd.DataFrame:
    """Build cohort A from Part 3-only results with fresh split columns."""
    trials = build_scored_trials(CohortSource.PART3)
    agg = aggregate_post_labels(trials)
    cohort = build_cohort_a(agg)
    cohort = attach_pair_order(cohort)
    cohort["in_part3_cohort_a"] = True
    cohort["label_changed_vs_part3"] = False
    split_frame = assign_splits(cohort, SPLIT_SEED)
    return sample_gepa_subsets(split_frame, SPLIT_SEED)


def build_union_split_frame(frozen: pd.DataFrame) -> tuple[pd.DataFrame, UnionBuildReport]:
    """Build union cohort with nested splits and topped-up GEPA subsets."""
    trials = build_scored_trials(CohortSource.UNION)
    agg = aggregate_post_labels(trials)
    cohort = build_cohort_a(agg)
    cohort, exclusion = apply_union_strata_exclusion(cohort, trials)
    cohort = attach_pair_order(cohort)
    cohort = attach_part3_overlap_flags(cohort, frozen)
    split_frame = assign_nested_splits(cohort, frozen, SPLIT_SEED)
    split_frame, gepa_report = retain_and_top_up_gepa_subsets(
        split_frame,
        frozen,
        SPLIT_SEED,
    )
    frozen_ids = set(frozen["post_id"].astype(str))
    union_ids = set(split_frame["post_id"].astype(str))
    frozen_test = set(frozen.loc[frozen["split"].eq("test"), "post_id"].astype(str))
    union_test = set(split_frame.loc[split_frame["split"].eq("test"), "post_id"].astype(str))
    report = UnionBuildReport(
        n_excluded_strata=exclusion.n_excluded,
        excluded_keep=exclusion.excluded_keep,
        excluded_remove=exclusion.excluded_remove,
        n_stance_disagreements=exclusion.n_stance_disagreements,
        n_toxicity_disagreements=exclusion.n_toxicity_disagreements,
        n_overlap_part3=len(frozen_ids & union_ids),
        n_label_changed=int(split_frame["label_changed_vs_part3"].sum()),
        n_dropped_from_part3=len(frozen_ids - union_ids),
        n_new_posts=len(union_ids - frozen_ids),
        n_shared_test_posts=len(frozen_test & union_test),
        val_members_changed=gepa_report.val_members_changed,
        train_members_changed=gepa_report.train_members_changed,
    )
    return split_frame, report


def main() -> CohortCounts:
    """Load, build cohort, assign splits, write, upload, log artifact, print counts.

    Returns
    -------
    CohortCounts
        Cohort summary counts.
    """
    args = _parse_cli_args()
    if args.cohort_source == CohortSource.PART3.value:
        return _run_part3_build()
    return _run_union_build()


def _run_part3_build() -> CohortCounts:
    split_frame = build_part3_split_frame()
    split_hash = compute_split_hash(split_frame)
    parquet_path, _json_path = write_outputs(
        split_frame,
        split_hash,
        EXPERIMENT_DIR,
        COHORT_PARQUET.name,
        SPLIT_HASH_JSON.name,
    )
    cohort_counts = _cohort_counts_from_frame(split_frame)
    split_counts = _split_counts_from_frame(split_frame)
    _print_counts(cohort_counts, split_counts, split_hash)
    if split_hash != PART3_FROZEN_SPLIT_HASH:
        print("split hash differs from frozen Part 3 acceptance target")
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


def _run_union_build() -> CohortCounts:
    frozen = load_frozen_part3_splits(EXPERIMENT_DIR)
    split_frame, union_report = build_union_split_frame(frozen)
    split_hash = compute_split_hash(split_frame)
    parquet_path, json_path = write_outputs(
        split_frame,
        split_hash,
        EXPERIMENT_DIR,
        COHORT_UNION_PARQUET.name,
        COHORT_UNION_SPLIT_HASH_JSON.name,
        extra_metadata={
            "cohort_source": CohortSource.UNION.value,
            "study_part_derivation": (
                "Part 3 rows have non-empty attention_check_passed; Part 2 rows leave it empty."
            ),
            "union_report": union_report.__dict__,
        },
    )
    cohort_counts = _cohort_counts_from_frame(split_frame)
    split_counts = _split_counts_from_frame(split_frame)
    _print_union_counts(cohort_counts, split_counts, split_hash, union_report)
    if not _union_counts_match_expected(cohort_counts, split_counts, union_report):
        print("union counts differ from frozen acceptance targets; outputs written with actuals")
        return cohort_counts
    s3_uri = upload_data(parquet_path)
    upload_data(json_path)
    print(f"s3_uri={s3_uri}")
    run = init_run(
        WandbRunSpec(
            group="data",
            name="build_splits",
            job_type="build_splits",
            config={"split_hash": split_hash, "split_seed": SPLIT_SEED},
        )
    )
    log_union_splits_artifact(run, parquet_path)
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


def _union_counts_match_expected(
    cohort_counts: CohortCounts,
    split_counts: SplitCounts,
    union_report: UnionBuildReport,
) -> bool:
    if EXPECTED_UNION_COHORT_POSTS == 0:
        return False
    return (
        cohort_counts.n_posts == EXPECTED_UNION_COHORT_POSTS
        and cohort_counts.n_keep == EXPECTED_UNION_COHORT_KEEP
        and cohort_counts.n_remove == EXPECTED_UNION_COHORT_REMOVE
        and union_report.n_excluded_strata == EXPECTED_UNION_EXCLUDED_STRATA
        and split_counts.test == EXPECTED_UNION_TEST
        and split_counts.dev == EXPECTED_UNION_DEV
        and split_counts.gepa_pool == EXPECTED_UNION_GEPA_POOL
        and split_counts.gepa_val == EXPECTED_UNION_GEPA_VAL
        and split_counts.gepa_train == EXPECTED_UNION_GEPA_TRAIN
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


def _print_union_counts(
    cohort_counts: CohortCounts,
    split_counts: SplitCounts,
    split_hash: str,
    union_report: UnionBuildReport,
) -> None:
    _print_counts(cohort_counts, split_counts, split_hash)
    print(f"excluded_strata={union_report.n_excluded_strata}")
    print(f"excluded_keep={union_report.excluded_keep}")
    print(f"excluded_remove={union_report.excluded_remove}")
    print(f"stance_disagreements={union_report.n_stance_disagreements}")
    print(f"toxicity_disagreements={union_report.n_toxicity_disagreements}")
    print(f"overlap_part3={union_report.n_overlap_part3}")
    print(f"label_changed={union_report.n_label_changed}")
    print(f"dropped_from_part3={union_report.n_dropped_from_part3}")
    print(f"new_posts={union_report.n_new_posts}")
    print(f"shared_test_posts={union_report.n_shared_test_posts}")
    print(f"val_members_changed={union_report.val_members_changed}")
    print(f"train_members_changed={union_report.train_members_changed}")


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-counts", action="store_true")
    parser.add_argument(
        "--cohort-source",
        choices=[CohortSource.PART3.value, CohortSource.UNION.value],
        default=CohortSource.PART3.value,
    )
    args = parser.parse_args()
    if not args.write_counts:
        parser.error("pass --write-counts")
    return args


if __name__ == "__main__":
    main()
