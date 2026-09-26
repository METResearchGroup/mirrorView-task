"""Stratified discovery versus test split for the cohort.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.split \\
      --seed 42 --write
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort import (
    build_cohort_frame,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    STRATIFY_COLUMNS,
)

DISCOVERY_IDS_FILENAME = "discovery_post_ids.csv"
TEST_IDS_FILENAME = "test_post_ids.csv"


@dataclass(frozen=True)
class SplitPreservationStats:
    """Counts for preserved versus newly assigned post IDs."""

    n_existing_preserved: int
    n_new_posts_assigned: int
    n_new_discovery: int
    n_new_test: int


@dataclass(frozen=True)
class SplitResult:
    """Discovery and test ID lists plus metadata path."""

    discovery_ids: list[str]
    test_ids: list[str]
    metadata_path: Path
    preservation: SplitPreservationStats


def _stratify_labels_for_split(frame: pd.DataFrame) -> pd.Series:
    """Bucket singleton strata so sklearn stratification can run."""
    labels = build_stratify_key(frame)
    counts = labels.value_counts()
    rare = counts[counts < 2].index
    adjusted = labels.where(~labels.isin(rare), constants.RARE_STRATIFY_BUCKET)
    bucket_count = int((adjusted == constants.RARE_STRATIFY_BUCKET).sum())
    if bucket_count == 1:
        return labels
    return adjusted


def build_stratify_key(frame: pd.DataFrame) -> pd.Series:
    """Build the concatenated stratification key for train_test_split."""
    modal = frame["modal_decision"].fillna(constants.UNLABELED_STRATUM).astype(str)
    parts = [modal]
    for column in STRATIFY_COLUMNS[1:]:
        parts.append(frame[column].astype(str))
    return parts[0].str.cat(parts[1:], sep="|")


def stratified_split(
    cohort: pd.DataFrame,
    seed: int,
) -> tuple[list[str], list[str]]:
    """Return discovery and test post ID lists for one cohort frame."""
    labels = _stratify_labels_for_split(cohort)
    discovery_frame, test_frame = train_test_split(
        cohort,
        test_size=constants.TEST_SIZE,
        random_state=seed,
        stratify=labels,
    )
    discovery_ids = discovery_frame["post_id"].astype(str).tolist()
    test_ids = test_frame["post_id"].astype(str).tolist()
    return discovery_ids, test_ids


def read_committed_post_ids(split_dir: Path) -> tuple[list[str], list[str]]:
    """Load discovery and test ID lists from committed CSV files."""
    discovery = _read_id_list(split_dir / DISCOVERY_IDS_FILENAME)
    test = _read_id_list(split_dir / TEST_IDS_FILENAME)
    return discovery, test


def split_with_preservation(
    cohort: pd.DataFrame,
    seed: int,
    split_dir: Path,
) -> tuple[list[str], list[str], SplitPreservationStats]:
    """Preserve prior split halves and stratify only new union posts."""
    existing_discovery, existing_test = read_committed_post_ids(split_dir)
    _validate_existing_splits(existing_discovery, existing_test, cohort)
    assigned = set(existing_discovery) | set(existing_test)
    cohort_ids = set(cohort["post_id"].astype(str))
    new_ids = sorted(cohort_ids - assigned)
    new_frame = cohort.loc[cohort["post_id"].astype(str).isin(new_ids)].copy()
    new_discovery: list[str] = []
    new_test: list[str] = []
    if not new_frame.empty:
        new_discovery, new_test = stratified_split(new_frame, seed)
    discovery_ids = existing_discovery + new_discovery
    test_ids = existing_test + new_test
    stats = SplitPreservationStats(
        n_existing_preserved=len(assigned & cohort_ids),
        n_new_posts_assigned=len(new_ids),
        n_new_discovery=len(new_discovery),
        n_new_test=len(new_test),
    )
    return discovery_ids, test_ids, stats


def write_split_outputs(
    cohort: pd.DataFrame,
    discovery_ids: list[str],
    test_ids: list[str],
    seed: int,
    preservation: SplitPreservationStats,
    split_dir: Path | None = None,
) -> SplitResult:
    """Write split CSVs, metadata, and update cohort parquet split column."""
    target_dir = split_dir if split_dir is not None else paths.post_split_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    discovery_path = target_dir / DISCOVERY_IDS_FILENAME
    test_path = target_dir / TEST_IDS_FILENAME
    metadata_path = target_dir / "split_metadata.json"
    _write_id_list(discovery_path, discovery_ids)
    _write_id_list(test_path, test_ids)
    metadata = _build_split_metadata(seed, discovery_ids, test_ids, preservation)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if split_dir is None:
        _update_cohort_split_columns(discovery_ids, test_ids)
    _print_wrote(discovery_path)
    _print_wrote(test_path)
    _print_wrote(metadata_path)
    return SplitResult(discovery_ids, test_ids, metadata_path, preservation)


def main() -> None:
    """Parse CLI args and write split artifacts when ``--write`` is set."""
    args = _parse_args()
    cohort = build_cohort_frame(constants.PARTICIPANT_FILTER_ALL)
    discovery_ids, test_ids, preservation = split_with_preservation(
        cohort, args.seed, paths.post_split_dir()
    )
    print(
        f"n_posts={len(cohort)} n_discovery={len(discovery_ids)} "
        f"n_test={len(test_ids)} n_existing_preserved="
        f"{preservation.n_existing_preserved} n_new_assigned="
        f"{preservation.n_new_posts_assigned}"
    )
    if not args.write:
        raise SystemExit("pass --write to persist split outputs")
    write_split_outputs(
        cohort,
        discovery_ids,
        test_ids,
        args.seed,
        preservation,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stratified cohort split.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _read_id_list(path: Path) -> list[str]:
    frame = pd.read_csv(path)
    return frame["post_id"].astype(str).tolist()


def _write_id_list(path: Path, post_ids: list[str]) -> None:
    frame = pd.DataFrame({"post_id": post_ids})
    frame.to_csv(path, index=False)


def _build_split_metadata(
    seed: int,
    discovery_ids: list[str],
    test_ids: list[str],
    preservation: SplitPreservationStats,
) -> dict[str, object]:
    return {
        "dataset": constants.DATASET_PHASE_2_PART_2_AND_3,
        "seed": seed,
        "n_discovery": len(discovery_ids),
        "n_test": len(test_ids),
        "n_new_posts_assigned": preservation.n_new_posts_assigned,
        "n_existing_preserved": preservation.n_existing_preserved,
        "stratify_columns": list(STRATIFY_COLUMNS),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


def _validate_existing_splits(
    discovery_ids: list[str],
    test_ids: list[str],
    cohort: pd.DataFrame,
) -> None:
    overlap = set(discovery_ids) & set(test_ids)
    if overlap:
        raise ValueError("discovery and test ID lists overlap")
    cohort_ids = set(cohort["post_id"].astype(str))
    missing = (set(discovery_ids) | set(test_ids)) - cohort_ids
    if missing:
        raise KeyError(f"prior split references posts missing from cohort: {len(missing)}")


def _update_cohort_split_columns(
    discovery_ids: list[str],
    test_ids: list[str],
) -> None:
    discovery_set = set(discovery_ids)
    test_set = set(test_ids)
    for arm in constants.TEXT_ARMS:
        run_dir = _latest_all_participant_cohort_run(arm)
        cohort_path = run_dir / constants.COHORT_FILENAME
        frame = pd.read_parquet(cohort_path)
        frame["split"] = frame["post_id"].map(
            lambda post_id: _split_label(post_id, discovery_set, test_set)
        )
        frame.to_parquet(cohort_path, index=False)


def _latest_all_participant_cohort_run(arm: str) -> Path:
    cohort_root = paths.cohort_dir(arm)
    if not cohort_root.is_dir():
        raise FileNotFoundError(f"Missing cohort directory: {cohort_root}")
    candidates = sorted(
        (
            path
            for path in cohort_root.iterdir()
            if path.is_dir()
            and _metadata_participant_filter(path) == constants.PARTICIPANT_FILTER_ALL
        ),
        key=lambda path: path.name,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No cohort run with participant_filter=all under {cohort_root}"
        )
    return candidates[-1]


def _metadata_participant_filter(run_dir: Path) -> str | None:
    metadata_path = run_dir / constants.METADATA_FILENAME
    if not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    value = metadata.get("participant_filter")
    return str(value) if value is not None else None


def _print_wrote(path: Path) -> None:
    try:
        relative = path.relative_to(paths.EXPERIMENT_ROOT)
        print(f"wrote {relative}")
    except ValueError:
        print(f"wrote {path}")


def _split_label(
    post_id: str,
    discovery_set: set[str],
    test_set: set[str],
) -> str:
    if post_id in discovery_set:
        return constants.DISCOVERY_SPLIT
    if post_id in test_set:
        return constants.TEST_SPLIT
    raise KeyError(f"post_id missing from split assignment: {post_id}")


if __name__ == "__main__":
    main()
