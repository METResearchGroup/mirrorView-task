"""Build the local four-cell unanimous vs majority cohort.

Run from repo root::

    PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_STIMULI,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
COHORT_CSV = EXPERIMENT_ROOT / "outputs" / "cohort" / "four_cell_cohort.csv"

_MIN_RATERS = 3
_KEEP_REMOVE = frozenset({"keep", "remove"})
_CELL_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "cell",
    "n_raters",
    "keep_count",
    "remove_count",
    "is_unanimous",
    "sample_toxicity_type",
    "sampled_stance",
]
_REQUIRED_STIMULI_COLUMNS = (
    "post_primary_key",
    "sample_toxicity_type",
    "sampled_stance",
)


def _load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Select linked-fate keep or remove trials with a usable post id.

    Parameters
    ----------
    raw
        Phase 2 Part 2 results full frame.

    Returns
    -------
    pandas.DataFrame
        Slim trial rows with normalized mode and decision.

    Raises
    ------
    KeyError
        When required columns are missing.
    """
    required = {"evaluation_mode", "decision", "post_id", "original_text", "mirror_text"}
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"Results missing required columns: {sorted(missing)}")

    trials = raw.copy()
    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()
    trials = trials[trials["post_id"].notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()
    return trials


def _assert_stable_texts(trials: pd.DataFrame) -> None:
    """Raise if any post_id has conflicting original or mirror text.

    Parameters
    ----------
    trials
        Slim trial frame.

    Raises
    ------
    ValueError
        When a post has more than one distinct original or mirror text.
    """
    text_nunique = (
        trials.groupby("post_id", dropna=False)
        .agg(
            original_text_nunique=("original_text", lambda s: s.fillna("").nunique()),
            mirror_text_nunique=("mirror_text", lambda s: s.fillna("").nunique()),
        )
        .reset_index()
    )
    bad = text_nunique[
        (text_nunique["original_text_nunique"] != 1)
        | (text_nunique["mirror_text_nunique"] != 1)
    ]
    if len(bad):
        example_post = str(bad.iloc[0]["post_id"])
        raise ValueError(
            "Expected stable original/mirror text per post_id, but found conflicts. "
            f"Example problematic post_id={example_post}."
        )


def _aggregate_per_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate slim trials to per-post keep and remove counts.

    Parameters
    ----------
    trials
        Slim trial frame with stable texts.

    Returns
    -------
    pandas.DataFrame
        One row per post_id with rater counts and stable texts.
    """
    _assert_stable_texts(trials)
    grouped = (
        trials.groupby("post_id", dropna=False)
        .agg(
            n_raters=("decision", "size"),
            n_unique_decisions=("decision", "nunique"),
            keep_count=("decision", lambda s: int((s == "keep").sum())),
            remove_count=("decision", lambda s: int((s == "remove").sum())),
            original_text=("original_text", "first"),
            mirror_text=("mirror_text", "first"),
        )
        .reset_index()
    )
    grouped["is_unanimous"] = grouped["n_unique_decisions"] == 1
    return grouped


def _assign_cell(row: pd.Series) -> str:
    """Return the four-cell label for one aggregated post row.

    Parameters
    ----------
    row
        Aggregated post row with counts and ``is_unanimous``.

    Returns
    -------
    str
        One of the four frozen cell strings.

    Raises
    ------
    ValueError
        When the row does not match a cell rule (for example an exact tie).
    """
    is_unanimous = bool(row["is_unanimous"])
    n_raters = int(row["n_raters"])
    keep_count = int(row["keep_count"])
    remove_count = int(row["remove_count"])
    if is_unanimous and keep_count == n_raters:
        return "unanimous_keep"
    if is_unanimous and remove_count == n_raters:
        return "unanimous_remove"
    if (not is_unanimous) and keep_count > remove_count:
        return "majority_keep"
    if (not is_unanimous) and remove_count > keep_count:
        return "majority_remove"
    raise ValueError(
        f"Cannot assign cell for post_id={row['post_id']!r}: "
        f"keep={keep_count} remove={remove_count} n_raters={n_raters}"
    )


def _filter_universe(per_post: pd.DataFrame) -> pd.DataFrame:
    """Keep posts with at least three raters and drop exact ties.

    Parameters
    ----------
    per_post
        Aggregated per-post frame.

    Returns
    -------
    pandas.DataFrame
        Filtered frame with a ``cell`` column.
    """
    frame = per_post[per_post["n_raters"] >= _MIN_RATERS].copy()
    frame = frame[frame["keep_count"] != frame["remove_count"]].copy()
    frame["cell"] = frame.apply(_assign_cell, axis=1)
    return frame


def _join_stimuli(per_post: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    """Join toxicity and stance fields from stimuli onto the cohort.

    Parameters
    ----------
    per_post
        Filtered four-cell posts.
    stimuli
        Phase 2 Part 2 stimuli frame.

    Returns
    -------
    pandas.DataFrame
        Cohort rows with stimuli fields.

    Raises
    ------
    KeyError
        When required stimuli columns are missing.
    ValueError
        When a cohort post lacks exactly one stimuli match.
    """
    missing = [c for c in _REQUIRED_STIMULI_COLUMNS if c not in stimuli.columns]
    if missing:
        raise KeyError(f"Stimuli missing required columns: {missing}")

    stim = stimuli[list(_REQUIRED_STIMULI_COLUMNS)].copy()
    stim["post_primary_key"] = stim["post_primary_key"].astype(str).str.strip()
    stim_counts = stim["post_primary_key"].value_counts()
    duplicated = stim_counts[stim_counts > 1]
    if len(duplicated):
        raise ValueError(
            "Stimuli has duplicate post_primary_key values. "
            f"Example key={duplicated.index[0]!r}."
        )

    merged = per_post.merge(
        stim,
        left_on="post_id",
        right_on="post_primary_key",
        how="left",
        validate="one_to_one",
    )
    missing_mask = merged["post_primary_key"].isna()
    if bool(missing_mask.any()):
        examples = merged.loc[missing_mask, "post_id"].head(5).tolist()
        raise ValueError(
            "Cohort posts missing from stimuli. "
            f"n_missing={int(missing_mask.sum())} examples={examples}"
        )
    return merged


def _to_output_frame(merged: pd.DataFrame) -> pd.DataFrame:
    """Select and order the frozen cohort columns.

    Parameters
    ----------
    merged
        Joined cohort frame.

    Returns
    -------
    pandas.DataFrame
        Output frame with frozen column order.
    """
    out = merged.copy()
    out["message_id"] = out["post_id"].astype(str)
    out["n_raters"] = out["n_raters"].astype(int)
    out["keep_count"] = out["keep_count"].astype(int)
    out["remove_count"] = out["remove_count"].astype(int)
    out["is_unanimous"] = out["is_unanimous"].astype(bool)
    out["original_text"] = out["original_text"].astype(str)
    out["mirror_text"] = out["mirror_text"].astype(str)
    out["sample_toxicity_type"] = out["sample_toxicity_type"].astype(str)
    out["sampled_stance"] = out["sampled_stance"].astype(str)
    return out[_OUTPUT_COLUMNS].reset_index(drop=True)


def build_four_cell_cohort(
    raw: pd.DataFrame | None = None,
    stimuli: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the four-cell cohort without writing to disk.

    Parameters
    ----------
    raw
        Optional results-full frame. Loads from the registry when omitted.
    stimuli
        Optional stimuli frame. Loads from the registry when omitted.

    Returns
    -------
    pandas.DataFrame
        Four-cell cohort with frozen columns.
    """
    raw_frame = (
        raw
        if raw is not None
        else load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    )
    stimuli_frame = (
        stimuli
        if stimuli is not None
        else load_dataset(STUDY_PHASE_2_PART_2_STIMULI, low_memory=False)
    )
    trials = _load_slim_trial_frame(raw_frame)
    per_post = _aggregate_per_post(trials)
    universe = _filter_universe(per_post)
    merged = _join_stimuli(universe, stimuli_frame)
    return _to_output_frame(merged)


def write_four_cell_cohort(path: Path = COHORT_CSV) -> pd.DataFrame:
    """Build the cohort, write CSV, and return the frame.

    Parameters
    ----------
    path
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        Written cohort frame.
    """
    cohort = build_four_cell_cohort()
    path.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(path, index=False)
    return cohort


def _print_cell_counts(cohort: pd.DataFrame) -> None:
    """Print ordered cell counts and total size."""
    counts = cohort["cell"].value_counts()
    for cell in _CELL_ORDER:
        print(f"{cell}: {int(counts.get(cell, 0))}")
    print(f"total: {len(cohort)}")


def main() -> None:
    """CLI entry: write the local four-cell cohort and print counts."""
    cohort = write_four_cell_cohort(COHORT_CSV)
    print(f"Wrote {COHORT_CSV}")
    _print_cell_counts(cohort)


if __name__ == "__main__":
    main()
