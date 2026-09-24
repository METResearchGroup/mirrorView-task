"""Build the post-level cohort for Phase 2 Part 3.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort \\
      --participant-filter all --write
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_STIMULI,
    STUDY_PHASE_2_PART_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_3_STIMULI,
)

ParticipantFilter = Literal["all", "attention_pass"]


@dataclass(frozen=True)
class CohortBuildStats:
    """Summary counts printed after a cohort build."""

    n_posts: int
    n_labeled: int
    n_part2_overlap: int
    label_count_one: int
    label_count_two: int
    label_count_three_plus: int


@dataclass(frozen=True)
class CohortWriteResult:
    """Paths written for one cohort build across text arms."""

    run_timestamp: str
    stats: CohortBuildStats
    cohort_paths: tuple[Path, ...]


def slim_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep phase-one linked-fate keep or remove moderation trials."""
    _require_columns(frame, constants.REQUIRED_SLIM_COLUMNS)
    trials = frame.copy()
    trials["evaluation_mode"] = _normalize_text(trials, "evaluation_mode")
    trials["decision"] = _normalize_text(trials, "decision")
    trials["trial_type"] = _normalize_text(trials, "trial_type")
    trials["post_id"] = trials["post_id"].fillna("").astype(str).str.strip()
    trials["prolific_id"] = trials["prolific_id"].fillna("").astype(str).str.strip()
    return _filter_slim_rows(trials)


def filter_by_participant(
    trials: pd.DataFrame,
    participant_filter: ParticipantFilter,
) -> pd.DataFrame:
    """Apply the all or attention_pass participant filter."""
    if participant_filter == constants.PARTICIPANT_FILTER_ALL:
        return trials.copy()
    passing_ids = _attention_passing_prolific_ids(trials)
    return trials.loc[trials["prolific_id"].isin(passing_ids)].copy()


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
    if votes in constants.SPLIT_VOTE_PATTERNS:
        return constants.GROUP_SPLIT
    if remove_count == 0 and keep_count >= constants.MIN_RATERS:
        return constants.GROUP_UNANIMOUS_KEEP
    if keep_count == 0 and remove_count >= constants.MIN_RATERS:
        return constants.GROUP_UNANIMOUS_REMOVE
    return None


def modal_decision(keep_count: int, remove_count: int) -> str | None:
    """Return keep, remove, or None when there are zero raters."""
    total = keep_count + remove_count
    if total == 0:
        return None
    if keep_count == remove_count:
        raise ValueError("modal decision tie with n_raters > 0")
    if keep_count > remove_count:
        return constants.DECISION_KEEP
    return constants.DECISION_REMOVE


def three_group_label(keep_count: int, remove_count: int) -> str | None:
    """Return the three-group label when n_raters meets MIN_RATERS."""
    if keep_count + remove_count < constants.MIN_RATERS:
        return None
    return assign_group(keep_count, remove_count)


def map_toxicity_type(raw_value: str) -> str:
    """Map sample_*_toxicity strings to low, middle, or high."""
    text = str(raw_value).strip()
    if text.startswith(constants.TOXICITY_PREFIX):
        text = text[len(constants.TOXICITY_PREFIX) :]
    if text.endswith(constants.TOXICITY_SUFFIX):
        text = text[: -len(constants.TOXICITY_SUFFIX)]
    return text


def build_cohort_frame(participant_filter: ParticipantFilter) -> pd.DataFrame:
    """Build the full post-level cohort table."""
    stimuli = _load_stimuli_frame()
    part2_ids = _load_part2_post_ids()
    trials = _prepare_trials(participant_filter)
    vote_counts = _aggregate_vote_counts(trials)
    cohort = stimuli.merge(vote_counts, on="post_id", how="left")
    cohort = _fill_vote_defaults(cohort)
    cohort = _attach_label_columns(cohort)
    cohort["in_part2_catalog"] = cohort["post_id"].isin(part2_ids)
    cohort["split"] = None
    cohort["participant_filter"] = participant_filter
    return cohort[list(constants.COHORT_COLUMNS)]


def write_cohort_outputs(
    cohort: pd.DataFrame,
    stats: CohortBuildStats,
    participant_filter: ParticipantFilter,
    run_timestamp: str,
) -> CohortWriteResult:
    """Write cohort parquet and metadata for each text arm."""
    metadata = _build_metadata(stats, participant_filter, run_timestamp)
    written_paths: list[Path] = []
    for arm in constants.TEXT_ARMS:
        run_dir = paths.cohort_dir(arm) / run_timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        cohort_path = run_dir / constants.COHORT_FILENAME
        cohort.to_parquet(cohort_path, index=False)
        metadata_path = run_dir / constants.METADATA_FILENAME
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        written_paths.append(cohort_path)
        print(f"wrote {cohort_path.relative_to(paths.EXPERIMENT_ROOT)}")
    return CohortWriteResult(run_timestamp, stats, tuple(written_paths))


def compute_cohort_stats(cohort: pd.DataFrame) -> CohortBuildStats:
    """Summarize label counts and overlap for one cohort frame."""
    labeled = cohort[cohort["n_raters"] > 0]
    counts = labeled["n_raters"].value_counts()
    three_plus = int((labeled["n_raters"] >= 3).sum())
    return CohortBuildStats(
        n_posts=len(cohort),
        n_labeled=len(labeled),
        n_part2_overlap=int(cohort["in_part2_catalog"].sum()),
        label_count_one=int(counts.get(1, 0)),
        label_count_two=int(counts.get(2, 0)),
        label_count_three_plus=three_plus,
    )


def main() -> None:
    """Parse CLI args and build cohort outputs when ``--write`` is set."""
    args = _parse_args()
    cohort = build_cohort_frame(args.participant_filter)
    stats = compute_cohort_stats(cohort)
    _print_stats(args.participant_filter, stats)
    if not args.write:
        raise SystemExit("pass --write to persist cohort outputs")
    run_timestamp = paths.make_run_timestamp()
    write_cohort_outputs(cohort, stats, args.participant_filter, run_timestamp)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the post-level cohort.")
    parser.add_argument(
        "--participant-filter",
        choices=(
            constants.PARTICIPANT_FILTER_ALL,
            constants.PARTICIPANT_FILTER_ATTENTION_PASS,
        ),
        required=True,
    )
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def _print_stats(participant_filter: str, stats: CohortBuildStats) -> None:
    print(
        f"participant_filter={participant_filter} "
        f"n_posts={stats.n_posts} n_labeled={stats.n_labeled} "
        f"n_part2_overlap={stats.n_part2_overlap}"
    )
    print(
        "label_counts: "
        f"n1={stats.label_count_one} n2={stats.label_count_two} "
        f"n3plus={stats.label_count_three_plus}"
    )


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")


def _normalize_text(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].fillna("").astype(str).str.lower().str.strip()


def _filter_slim_rows(trials: pd.DataFrame) -> pd.DataFrame:
    usable_post = (trials["post_id"] != "") & (
        trials["post_id"].str.lower() != constants.EMPTY_POST_SENTINEL
    )
    keep = (
        (trials["phase"] == constants.PHASE_ONE)
        & (trials["evaluation_mode"] == constants.EVALUATION_MODE_LINKED_FATE)
        & (trials["decision"].isin({constants.DECISION_KEEP, constants.DECISION_REMOVE}))
        & (trials["trial_type"] == constants.TRIAL_TYPE_MODERATION)
        & (trials["prolific_id"] != "")
        & usable_post
    )
    return trials.loc[keep].copy()


def _attention_passing_prolific_ids(trials: pd.DataFrame) -> set[str]:
    attention = trials[["prolific_id", "attention_check_passed"]].dropna(
        subset=["attention_check_passed"]
    )
    first_pass = attention.groupby("prolific_id")["attention_check_passed"].first()
    passing = first_pass[first_pass == 1]
    return set(passing.index.astype(str))


def _load_stimuli_frame() -> pd.DataFrame:
    frame = load_dataset(STUDY_PHASE_2_PART_3_STIMULI)
    stimuli = frame.rename(columns={"post_primary_key": "post_id"}).copy()
    stimuli["sample_toxicity_type"] = stimuli["sample_toxicity_type"].map(
        map_toxicity_type
    )
    return stimuli[["post_id", "original_text", "mirrored_text", "sampled_stance", "sample_toxicity_type"]].rename(
        columns={"mirrored_text": "mirror_text"}
    )


def _load_part2_post_ids() -> set[str]:
    part2 = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)
    return set(part2["post_primary_key"].astype(str))


def _prepare_trials(participant_filter: ParticipantFilter) -> pd.DataFrame:
    results = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)
    trials = slim_trials(results)
    return filter_by_participant(trials, participant_filter)


def _aggregate_vote_counts(trials: pd.DataFrame) -> pd.DataFrame:
    tagged = trials.assign(
        _keep=trials["decision"].eq(constants.DECISION_KEEP),
        _remove=trials["decision"].eq(constants.DECISION_REMOVE),
    )
    counts = tagged.groupby("post_id").agg(
        keep_count=("_keep", "sum"),
        remove_count=("_remove", "sum"),
    )
    counts["keep_count"] = counts["keep_count"].astype(int)
    counts["remove_count"] = counts["remove_count"].astype(int)
    counts["n_raters"] = counts["keep_count"] + counts["remove_count"]
    return counts.reset_index()


def _fill_vote_defaults(cohort: pd.DataFrame) -> pd.DataFrame:
    filled = cohort.copy()
    for column in ("keep_count", "remove_count", "n_raters"):
        filled[column] = filled[column].fillna(0).astype(int)
    return filled


def _attach_label_columns(cohort: pd.DataFrame) -> pd.DataFrame:
    labeled = cohort.copy()
    labeled["modal_decision"] = [
        _resolve_modal_decision(int(row.keep_count), int(row.remove_count))
        for row in labeled.itertuples(index=False)
    ]
    labeled["three_group_label"] = [
        three_group_label(int(row.keep_count), int(row.remove_count))
        for row in labeled.itertuples(index=False)
    ]
    return labeled


def _resolve_modal_decision(keep_count: int, remove_count: int) -> str | None:
    total = keep_count + remove_count
    if total == 0 or keep_count == remove_count:
        return None
    return modal_decision(keep_count, remove_count)


def _build_metadata(
    stats: CohortBuildStats,
    participant_filter: ParticipantFilter,
    run_timestamp: str,
) -> dict[str, object]:
    return {
        "participant_filter": participant_filter,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "n_posts": stats.n_posts,
        "n_labeled": stats.n_labeled,
        "label_count_histogram": {
            "1": stats.label_count_one,
            "2": stats.label_count_two,
            "3_plus": stats.label_count_three_plus,
        },
        "n_part2_overlap": stats.n_part2_overlap,
        "run_timestamp": run_timestamp,
    }


if __name__ == "__main__":
    main()
