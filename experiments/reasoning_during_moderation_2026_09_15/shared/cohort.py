"""Build the September three-group moderation cohort.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import sha256_hex
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_COLUMNS,
    COHORT_FILENAME,
    COHORT_S3_KEY,
    DECISION_KEEP,
    DECISION_REMOVE,
    EMPTY_POST_SENTINEL,
    EVALUATION_MODE_LINKED_FATE,
    EXPERIMENT_DIR,
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    METADATA_FILENAME,
    METADATA_S3_KEY,
    MIN_CSV_FILES,
    MIN_RATERS,
    ORIGINAL_FIRST_DRAW,
    OUTPUT_S3_BUCKET,
    PAIR_ORDER_BIN_COUNT,
    PAIR_ORDER_HASH_BYTES,
    PAIR_ORDER_MIRROR_FIRST,
    PAIR_ORDER_ORIGINAL_FIRST,
    PAIR_ORDER_SEED,
    REQUIRED_SLIM_COLUMNS,
    SINCE_DATE,
    SLIM_TRIAL_COLUMNS,
    SLIM_TRIALS_FILENAME,
    SLIM_TRIALS_S3_KEY,
    SPLIT_VOTE_PATTERNS,
    TRIAL_TYPE_MODERATION,
)
from lib.timestamp_utils import get_current_timestamp
from scripts.export_study_results import (
    download_csvs,
    filter_manual_test_rows,
    list_csv_keys,
    load_downloaded_csvs,
    utc_midnight_ms,
)


def slim_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep linked-fate keep or remove moderation trials with a usable post id."""
    _require_columns(frame, REQUIRED_SLIM_COLUMNS)
    trials = frame.copy()
    trials["evaluation_mode"] = _normalize_text(trials, "evaluation_mode")
    trials["decision"] = _normalize_text(trials, "decision")
    trials["trial_type"] = _normalize_text(trials, "trial_type")
    trials["post_id"] = trials["post_id"].fillna("").astype(str).str.strip()
    trials["prolific_id"] = trials["prolific_id"].fillna("").astype(str).str.strip()
    return _filter_slim_rows(trials)


def assert_stable_pair_text(trials: pd.DataFrame) -> None:
    """Raise when a post has more than one original or mirror text."""
    for _post_id, group in trials.groupby("post_id"):
        originals = group["original_text"].astype(str).unique()
        mirrors = group["mirror_text"].astype(str).unique()
        _require_single_nonempty_text(originals)
        _require_single_nonempty_text(mirrors)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")


def _normalize_text(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].fillna("").astype(str).str.lower().str.strip()


def _filter_slim_rows(trials: pd.DataFrame) -> pd.DataFrame:
    usable_post = (trials["post_id"] != "") & (
        trials["post_id"].str.lower() != EMPTY_POST_SENTINEL
    )
    keep = (
        (trials["evaluation_mode"] == EVALUATION_MODE_LINKED_FATE)
        & (trials["decision"].isin({DECISION_KEEP, DECISION_REMOVE}))
        & (trials["trial_type"] == TRIAL_TYPE_MODERATION)
        & (trials["prolific_id"] != "")
        & usable_post
    )
    return trials.loc[keep].copy()


def _is_blank(value: object) -> bool:
    text = str(value).strip()
    return text == "" or text.lower() == EMPTY_POST_SENTINEL


def _require_single_nonempty_text(values: object) -> None:
    texts = list(values)
    if len(texts) != 1 or _is_blank(texts[0]):
        raise ValueError("post has conflicting or empty pair text")



def drop_conflicting_worker_posts(trials: pd.DataFrame) -> pd.DataFrame:
    """Drop worker-post pairs that contain both keep and remove."""
    worker_post = ["post_id", "prolific_id"]
    distinct_decisions = trials.groupby(worker_post)["decision"].transform("nunique")
    return trials.loc[distinct_decisions == 1].copy()


def dedupe_worker_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Keep the earliest row per worker and post."""
    ordered = trials.sort_values(
        ["post_id", "prolific_id", "time_elapsed", "trial_index"],
        kind="mergesort",
    )
    return ordered.drop_duplicates(["post_id", "prolific_id"], keep="first")


def assign_group(keep_count: int, remove_count: int) -> str | None:
    """Return split, unanimous_keep, unanimous_remove, or None."""
    votes = (keep_count, remove_count)
    if votes in SPLIT_VOTE_PATTERNS:
        return GROUP_SPLIT
    if remove_count == 0 and keep_count >= MIN_RATERS:
        return GROUP_UNANIMOUS_KEEP
    if keep_count == 0 and remove_count >= MIN_RATERS:
        return GROUP_UNANIMOUS_REMOVE
    return None


def pair_order_for_post(post_id: str, seed: int = PAIR_ORDER_SEED) -> tuple[str, str]:
    """Return a deterministic Post 1 and Post 2 role pair."""
    digest = hashlib.sha256(f"{seed}:{post_id}".encode()).digest()
    rng_seed = int.from_bytes(digest[:PAIR_ORDER_HASH_BYTES], "big")
    rng = np.random.Generator(np.random.PCG64(rng_seed))
    if int(rng.integers(0, PAIR_ORDER_BIN_COUNT)) == ORIGINAL_FIRST_DRAW:
        return PAIR_ORDER_ORIGINAL_FIRST
    return PAIR_ORDER_MIRROR_FIRST


def build_cohort(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate eligible posts into the three analysis groups."""
    assert_stable_pair_text(trials)
    counts = _count_votes(trials)
    eligible = counts[counts["n_raters"] >= MIN_RATERS].copy()
    eligible["group"] = [
        assign_group(int(row.keep_count), int(row.remove_count))
        for row in eligible.itertuples()
    ]
    grouped = eligible[eligible["group"].notna()].copy()
    with_text = grouped.join(_stable_texts(trials))
    return _attach_pair_order(with_text).reset_index()[list(COHORT_COLUMNS)]


def _count_votes(trials: pd.DataFrame) -> pd.DataFrame:
    tagged = trials.assign(
        _keep=trials["decision"].eq(DECISION_KEEP),
        _remove=trials["decision"].eq(DECISION_REMOVE),
    )
    counts = tagged.groupby("post_id").agg(
        n_raters=("decision", "size"),
        keep_count=("_keep", "sum"),
        remove_count=("_remove", "sum"),
    )
    counts["keep_count"] = counts["keep_count"].astype(int)
    counts["remove_count"] = counts["remove_count"].astype(int)
    if not (counts["n_raters"] == counts["keep_count"] + counts["remove_count"]).all():
        raise ValueError("n_raters must equal keep_count plus remove_count")
    return counts


def _stable_texts(trials: pd.DataFrame) -> pd.DataFrame:
    return (
        trials.drop_duplicates("post_id")
        .set_index("post_id")[["original_text", "mirror_text"]]
    )


def _attach_pair_order(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.copy()
    orders = [
        pair_order_for_post(str(post_id), PAIR_ORDER_SEED) for post_id in ordered.index
    ]
    ordered["post_1_role"] = [order[0] for order in orders]
    ordered["post_2_role"] = [order[1] for order in orders]
    return ordered


def write_cohort(
    cohort: pd.DataFrame,
    slim: pd.DataFrame,
    metadata: dict[str, object],
    experiment_dir: Path,
) -> tuple[Path, Path, Path]:
    """Write cohort parquet, slim trials, and export metadata locally."""
    output_dir = experiment_dir / "outputs" / "cohort"
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_path = output_dir / COHORT_FILENAME
    slim_path = output_dir / SLIM_TRIALS_FILENAME
    metadata_path = output_dir / METADATA_FILENAME
    cohort.to_parquet(cohort_path, index=False)
    slim.to_parquet(slim_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    return cohort_path, slim_path, metadata_path


def upload_cohort(body: bytes, key: str, store: CampaignObjectStore) -> None:
    """Upload bytes with put_new and refuse an existing key."""
    store.put_new(key, body)


def main() -> None:
    _require_write_counts_flag()
    csv_files, export = _download_export()
    _require_csv_file_count(csv_files)
    trials = slim_trials(export)
    trials = drop_conflicting_worker_posts(trials)
    trials = dedupe_worker_post(trials)
    assert_stable_pair_text(trials)
    cohort = build_cohort(trials)
    counts = _counts_from_cohort(cohort, csv_files)
    _require_nonempty_groups(counts)
    slim = _slim_for_cohort(trials, cohort)
    metadata = _export_metadata(counts)
    paths = write_cohort(cohort, slim, metadata, EXPERIMENT_DIR)
    _upload_outputs(paths)
    _print_counts(counts)


def _require_write_counts_flag() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-counts", action="store_true")
    args = parser.parse_args()
    if not args.write_counts:
        parser.error("pass --write-counts")


def _download_export() -> tuple[int, pd.DataFrame]:
    client = boto3.client("s3")
    keys = list_csv_keys(client, min_file_epoch_ms=utc_midnight_ms(SINCE_DATE))
    paths = download_csvs(client, keys)
    combined = load_downloaded_csvs(paths)
    return len(keys), filter_manual_test_rows(combined)


def _require_csv_file_count(csv_files: int) -> None:
    if csv_files < MIN_CSV_FILES:
        raise ValueError(f"csv_files={csv_files} is less than {MIN_CSV_FILES}")


def _counts_from_cohort(cohort: pd.DataFrame, csv_files: int) -> dict[str, int]:
    group_counts = cohort["group"].value_counts()
    split = int(group_counts.get(GROUP_SPLIT, 0))
    keep = int(group_counts.get(GROUP_UNANIMOUS_KEEP, 0))
    remove = int(group_counts.get(GROUP_UNANIMOUS_REMOVE, 0))
    return {
        "csv_files": csv_files,
        "split": split,
        "unanimous_keep": keep,
        "unanimous_remove": remove,
        "eligible_posts": split + keep + remove,
    }


def _require_nonempty_groups(counts: dict[str, int]) -> None:
    empty = [
        name
        for name in (GROUP_SPLIT, GROUP_UNANIMOUS_KEEP, GROUP_UNANIMOUS_REMOVE)
        if counts[name] == 0
    ]
    if empty:
        raise ValueError(f"empty analysis groups: {empty}")


def _slim_for_cohort(trials: pd.DataFrame, cohort: pd.DataFrame) -> pd.DataFrame:
    merged = trials.merge(cohort[["post_id", "group"]], on="post_id", how="inner")
    return merged[list(SLIM_TRIAL_COLUMNS)]


def _export_metadata(counts: dict[str, int]) -> dict[str, object]:
    return {
        "since_date": SINCE_DATE.isoformat(),
        "built_at": get_current_timestamp(),
        **counts,
    }


def _upload_outputs(paths: tuple[Path, Path, Path]) -> None:
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    cohort_path, slim_path, metadata_path = paths
    cohort_body = cohort_path.read_bytes()
    upload_cohort(cohort_body, COHORT_S3_KEY, store)
    upload_cohort(slim_path.read_bytes(), SLIM_TRIALS_S3_KEY, store)
    upload_cohort(metadata_path.read_bytes(), METADATA_S3_KEY, store)
    print(f"sha256={sha256_hex(cohort_body)}")


def _print_counts(counts: dict[str, int]) -> None:
    for name, value in counts.items():
        print(f"{name}={value}")


if __name__ == "__main__":
    main()
