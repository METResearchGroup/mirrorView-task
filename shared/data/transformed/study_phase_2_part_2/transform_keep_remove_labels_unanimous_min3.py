"""Build and materialize Part 2 unanimous min-3 keep/remove labels.

Public entrypoints:

- ``build_keep_remove_labels_unanimous_min3`` /
  ``write_keep_remove_labels_unanimous_min3`` →
  ``keep_remove_labels_unanimous_min3.csv``

Inclusion rule: linked-fate keep/remove trials with usable ``post_id``,
grouped by post; keep posts with ``n_raters >= 3`` where all raters share
the same decision (unanimous).

Run from repo root::

    PYTHONPATH=. uv run python \\
      shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = OUTPUT_DIR / "keep_remove_labels_unanimous_min3.csv"

_MIN_RATERS = 3
_KEEP_REMOVE = frozenset({"keep", "remove"})
_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
]


def _load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Select linked-fate keep/remove trials with a usable ``post_id``.

    Normalizes ``decision`` and ``evaluation_mode`` for comparison. Rows with
    null, empty, or literal ``"nan"`` post IDs are dropped.

    Raises
    ------
    KeyError
        If ``evaluation_mode``, ``post_id``, or ``decision`` is missing.
    """
    trials = raw.copy()
    if "decision" not in trials.columns:
        raise KeyError("Expected `decision` column in Part 2 results.")
    if "evaluation_mode" not in trials.columns:
        raise KeyError("Expected `evaluation_mode` column in Part 2 results.")
    if "post_id" not in trials.columns:
        raise KeyError("Expected `post_id` column in Part 2 results.")

    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()

    post_id = trials["post_id"]
    trials = trials[post_id.notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()

    return trials


def _assert_stable_texts(trials: pd.DataFrame) -> None:
    """Raise if any ``post_id`` has conflicting original or mirror text."""
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


def _aggregate_unanimous_min3(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate slim trials to unanimous posts with at least three raters.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    required = {"post_id", "original_text", "mirror_text", "decision"}
    missing = required - set(trials.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")

    _assert_stable_texts(trials)

    grouped = (
        trials.groupby("post_id", dropna=False)
        .agg(
            n_raters=("decision", "size"),
            n_unique_decisions=("decision", "nunique"),
            keep_count=("decision", lambda s: int((s == "keep").sum())),
            remove_count=("decision", lambda s: int((s == "remove").sum())),
        )
        .reset_index()
    )
    kept = grouped[
        (grouped["n_raters"] >= _MIN_RATERS) & (grouped["n_unique_decisions"] == 1)
    ].copy()

    kept["decision"] = kept.apply(
        lambda row: "keep" if int(row["keep_count"]) == int(row["n_raters"]) else "remove",
        axis=1,
    )
    kept["keep_remove_label"] = (kept["decision"] == "remove").astype(int)

    texts = trials.drop_duplicates(subset=["post_id"])[
        ["post_id", "original_text", "mirror_text"]
    ]
    out = kept.merge(texts, on="post_id", how="left")
    out = out.rename(columns={"post_id": "message_id"})
    return out[_OUTPUT_COLUMNS].reset_index(drop=True)


def build_keep_remove_labels_unanimous_min3(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build unanimous min-3 keep/remove labels from Part 2 results.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Part 2 results. When omitted, loads
        ``STUDY_PHASE_2_PART_2_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``message_id``, ``original_text``,
        ``mirror_text``, ``decision``, ``keep_remove_label``, and ``n_raters``.

    Raises
    ------
    KeyError
        If required columns are missing from the source frame.
    ValueError
        If a post has conflicting original or mirror text across trials.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    trials = _load_slim_trial_frame(raw)
    return _aggregate_unanimous_min3(trials)


def write_keep_remove_labels_unanimous_min3(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write unanimous min-3 keep/remove labels to CSV and return the frame.

    Creates parent directories as needed. By default writes
    ``keep_remove_labels_unanimous_min3.csv`` next to this script.

    Parameters
    ----------
    path : pathlib.Path, optional
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        The same frame written to disk.
    """
    df = build_keep_remove_labels_unanimous_min3()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    labels = write_keep_remove_labels_unanimous_min3()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")
