"""Build and materialize modal keep/remove labels from Part 2 raw results.

Public entrypoints: ``build_keep_remove_labels`` (in-memory frame) and
``write_keep_remove_labels`` (persist ``keep_remove_labels.csv`` beside this
script).

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = OUTPUT_DIR / "keep_remove_labels.csv"

_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
]


def _load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Select linked-fate keep/remove trials with a usable ``post_id``.

    Normalizes ``decision`` and ``evaluation_mode`` for comparison. Rows with
    null, empty, or literal ``"nan"`` post IDs are dropped.

    Raises
    ------
    KeyError
        If ``evaluation_mode`` or ``post_id`` is missing from ``raw``.
    """
    trials = raw.copy()
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()

    if "evaluation_mode" not in trials.columns:
        raise KeyError("Expected `evaluation_mode` column in Part 2 results.")
    trials["evaluation_mode"] = trials["evaluation_mode"].astype(str).str.lower().str.strip()
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()

    trials = trials[trials["decision"].isin(["keep", "remove"])].copy()

    if "post_id" not in trials.columns:
        raise KeyError("Expected `post_id` column in Part 2 results.")

    # Drop null/empty post_id before stringifying (avoids "nan" string keys).
    post_id = trials["post_id"]
    trials = trials[post_id.notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()

    return trials


def _aggregate_modal_labels(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trials to one modal keep/remove label per post.

    Tie votes become ``remove``. ``message_id`` aliases ``post_id``;
    ``keep_remove_label`` is 1 for remove and 0 for keep.

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

    counts = (
        trials.groupby(["post_id", "decision"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "keep" not in counts.columns:
        counts["keep"] = 0
    if "remove" not in counts.columns:
        counts["remove"] = 0

    counts["decision"] = counts.apply(
        lambda r: "keep" if int(r["keep"]) > int(r["remove"]) else "remove",
        axis=1,
    )
    counts["keep_remove_label"] = (counts["decision"] == "remove").astype(int)

    texts = trials.drop_duplicates(subset=["post_id"])[
        ["post_id", "original_text", "mirror_text"]
    ]
    out = counts.merge(texts, on="post_id", how="left")
    out = out.rename(columns={"post_id": "message_id"})
    return out[_OUTPUT_COLUMNS].reset_index(drop=True)


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the modal keep/remove training frame from Part 2 results.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Part 2 results. When omitted, loads
        ``STUDY_PHASE_2_PART_2_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``message_id``, ``original_text``,
        ``mirror_text``, ``decision``, and ``keep_remove_label``.

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
    return _aggregate_modal_labels(trials)


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write modal keep/remove labels to CSV and return the frame.

    Creates parent directories as needed. By default writes
    ``keep_remove_labels.csv`` next to this script (the path registered as
    ``STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS``).

    Parameters
    ----------
    path : pathlib.Path, optional
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        The same frame written to disk.
    """
    df = build_keep_remove_labels()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    frame = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(frame)}")
    print(frame["decision"].value_counts().to_dict())
    print(f"columns={list(frame.columns)}")
