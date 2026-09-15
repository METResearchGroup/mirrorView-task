"""Build the September three-group moderation cohort.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
    EMPTY_POST_SENTINEL,
    EVALUATION_MODE_LINKED_FATE,
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    MIN_RATERS,
    PAIR_ORDER_MIRROR_FIRST,
    PAIR_ORDER_ORIGINAL_FIRST,
    PAIR_ORDER_SEED,
    REQUIRED_SLIM_COLUMNS,
    SPLIT_VOTE_PATTERNS,
    TRIAL_TYPE_MODERATION,
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
    raise NotImplementedError


def build_cohort(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate eligible posts into the three analysis groups."""
    raise NotImplementedError


def write_cohort(
    cohort: pd.DataFrame,
    slim: pd.DataFrame,
    metadata: dict[str, object],
    experiment_dir: Path,
) -> tuple[Path, Path, Path]:
    """Write cohort parquet, slim trials, and export metadata locally."""
    raise NotImplementedError


def upload_cohort(body: bytes, key: str, store: CampaignObjectStore) -> None:
    """Upload bytes with put_new and refuse an existing key."""
    raise NotImplementedError


def main() -> None:
    export = _download_export()
    trials = slim_trials(export)
    trials = drop_conflicting_worker_posts(trials)
    trials = dedupe_worker_post(trials)
    assert_stable_pair_text(trials)
    cohort = build_cohort(trials)
    _write_and_upload(cohort, trials)


def _download_export() -> pd.DataFrame:
    raise NotImplementedError


def _write_and_upload(cohort: pd.DataFrame, trials: pd.DataFrame) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
