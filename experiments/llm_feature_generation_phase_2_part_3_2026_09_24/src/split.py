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


@dataclass(frozen=True)
class SplitResult:
    """Discovery and test ID lists plus metadata path."""

    discovery_ids: list[str]
    test_ids: list[str]
    metadata_path: Path


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
    """Return discovery and test post ID lists."""
    labels = build_stratify_key(cohort)
    discovery_frame, test_frame = train_test_split(
        cohort,
        test_size=constants.TEST_SIZE,
        random_state=seed,
        stratify=labels,
    )
    discovery_ids = discovery_frame["post_id"].astype(str).tolist()
    test_ids = test_frame["post_id"].astype(str).tolist()
    return discovery_ids, test_ids


def write_split_outputs(
    cohort: pd.DataFrame,
    discovery_ids: list[str],
    test_ids: list[str],
    seed: int,
    participant_filter: str,
) -> SplitResult:
    """Write split CSVs, metadata, and update cohort parquet split column."""
    split_dir = paths.post_split_dir()
    split_dir.mkdir(parents=True, exist_ok=True)
    discovery_path = split_dir / "discovery_post_ids.csv"
    test_path = split_dir / "test_post_ids.csv"
    metadata_path = split_dir / "split_metadata.json"
    _write_id_list(discovery_path, discovery_ids)
    _write_id_list(test_path, test_ids)
    metadata = _build_split_metadata(
        seed, discovery_ids, test_ids, participant_filter
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    _update_cohort_split_columns(discovery_ids, test_ids)
    print(f"wrote {discovery_path.relative_to(paths.EXPERIMENT_ROOT)}")
    print(f"wrote {test_path.relative_to(paths.EXPERIMENT_ROOT)}")
    print(f"wrote {metadata_path.relative_to(paths.EXPERIMENT_ROOT)}")
    return SplitResult(discovery_ids, test_ids, metadata_path)


def main() -> None:
    """Parse CLI args and write split artifacts when ``--write`` is set."""
    args = _parse_args()
    cohort = build_cohort_frame(constants.PARTICIPANT_FILTER_ALL)
    discovery_ids, test_ids = stratified_split(cohort, args.seed)
    print(
        f"n_posts={len(cohort)} n_discovery={len(discovery_ids)} "
        f"n_test={len(test_ids)}"
    )
    if not args.write:
        raise SystemExit("pass --write to persist split outputs")
    write_split_outputs(
        cohort,
        discovery_ids,
        test_ids,
        args.seed,
        constants.PARTICIPANT_FILTER_ALL,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stratified cohort split.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _write_id_list(path: Path, post_ids: list[str]) -> None:
    frame = pd.DataFrame({"post_id": post_ids})
    frame.to_csv(path, index=False)


def _build_split_metadata(
    seed: int,
    discovery_ids: list[str],
    test_ids: list[str],
    participant_filter: str,
) -> dict[str, object]:
    return {
        "split_seed": seed,
        "n_discovery": len(discovery_ids),
        "n_test": len(test_ids),
        "stratify_columns": list(STRATIFY_COLUMNS),
        "participant_filter": participant_filter,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


def _update_cohort_split_columns(
    discovery_ids: list[str],
    test_ids: list[str],
) -> None:
    discovery_set = set(discovery_ids)
    test_set = set(test_ids)
    for arm in constants.TEXT_ARMS:
        cohort_dir = paths.cohort_dir(arm)
        if not cohort_dir.is_dir():
            continue
        run_dir = paths.latest_timestamp_subdir(cohort_dir)
        cohort_path = run_dir / constants.COHORT_FILENAME
        frame = pd.read_parquet(cohort_path)
        frame["split"] = frame["post_id"].map(
            lambda post_id: _split_label(post_id, discovery_set, test_set)
        )
        frame.to_parquet(cohort_path, index=False)


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
