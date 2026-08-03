"""Materialize modal keep/remove labels for Study Phase 2 Part 2.

Reads the registered raw Part 2 results CSV, filters to linked-fate keep/remove
trials with non-null ``post_id``, aggregates to one modal decision per post
(ties → remove), and writes ``keep_remove_labels.csv`` beside this script.

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
    """Layer A: linked-fate keep/remove trials with non-null post_id."""
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
    """Layer B: one row per post with modal decision (tie → remove)."""
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
    """Build the modal keep/remove training frame from Part 2 results."""
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    trials = _load_slim_trial_frame(raw)
    return _aggregate_modal_labels(trials)


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Materialize ``keep_remove_labels.csv`` and return the dataframe."""
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
