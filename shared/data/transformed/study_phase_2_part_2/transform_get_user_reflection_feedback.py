"""Build and materialize Part 2 per-user Phase 1 reflection feedback.

Public entrypoints:

- ``build_user_reflection_feedback`` / ``write_user_reflection_feedback`` →
  ``user_reflection_feedback.csv``

Run from repo root::

    PYTHONPATH=. uv run python \\
      shared/data/transformed/study_phase_2_part_2/transform_get_user_reflection_feedback.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

OUTPUT_DIR = Path(__file__).resolve().parent
USER_REFLECTION_FEEDBACK_CSV = OUTPUT_DIR / "user_reflection_feedback.csv"

_USER_REFLECTION_COLUMNS = [
    "participant_id",
    "prolific_id",
    "phase1_pair_reflection_text",
    "phase1_pair_influence_rating",
]


def _is_usable_text(series: pd.Series) -> pd.Series:
    """True where stringified values are non-empty and not literal ``nan``."""
    cleaned = series.astype(str).str.strip()
    return series.notna() & (cleaned != "") & (cleaned.str.lower() != "nan")


def _load_reflection_survey_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """Select Phase 1 reflection survey rows with usable user feedback.

    Keeps ``trial_type == "survey-html-form"`` rows that have a non-empty
    ``phase1_pair_reflection_text`` and a usable ``participant_id``. Coerces
    ``phase1_pair_influence_rating`` to numeric.

    Raises
    ------
    KeyError
        If required columns are missing from ``raw``.
    """
    required = {
        "participant_id",
        "prolific_id",
        "trial_type",
        "phase1_pair_reflection_text",
        "phase1_pair_influence_rating",
    }
    missing = required - set(raw.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")

    rows = raw.copy()
    trial_type = rows["trial_type"].astype(str).str.strip().str.lower()
    rows = rows[trial_type == "survey-html-form"].copy()

    rows = rows[_is_usable_text(rows["phase1_pair_reflection_text"])].copy()

    pid = rows["participant_id"]
    rows = rows[pid.notna()].copy()
    rows["participant_id"] = rows["participant_id"].astype(str).str.strip()
    rows = rows[rows["participant_id"] != ""].copy()
    rows = rows[rows["participant_id"].str.lower() != "nan"].copy()

    rows["phase1_pair_reflection_text"] = (
        rows["phase1_pair_reflection_text"].astype(str).str.strip()
    )
    rows["phase1_pair_influence_rating"] = pd.to_numeric(
        rows["phase1_pair_influence_rating"], errors="coerce"
    )
    # Stringify prolific ids only where present (avoid literal "nan").
    prolific = rows["prolific_id"]
    rows["prolific_id"] = prolific.where(
        prolific.isna(), prolific.astype(str).str.strip()
    )

    return rows


def _one_row_per_participant(rows: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one reflection row per ``participant_id``.

    Source data is expected to already be unique (one survey-html-form
    reflection per participant). If duplicates appear, keep the **first**
    non-empty reflection in source-row order.
    """
    return rows.drop_duplicates(subset=["participant_id"], keep="first")


def build_user_reflection_feedback(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the per-user Phase 1 reflection feedback frame.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Part 2 results. When omitted, loads
        ``STUDY_PHASE_2_PART_2_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per ``participant_id`` with ``prolific_id``,
        ``phase1_pair_reflection_text``, and numeric
        ``phase1_pair_influence_rating``.

    Raises
    ------
    KeyError
        If required columns are missing from the source frame.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    rows = _load_reflection_survey_rows(raw)
    out = _one_row_per_participant(rows)
    return out[_USER_REFLECTION_COLUMNS].reset_index(drop=True)


def write_user_reflection_feedback(
    path: Path = USER_REFLECTION_FEEDBACK_CSV,
) -> pd.DataFrame:
    """Write per-user reflection feedback to CSV and return the frame.

    Creates parent directories as needed. By default writes
    ``user_reflection_feedback.csv`` next to this script (the path registered
    as ``STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK``).

    Parameters
    ----------
    path : pathlib.Path, optional
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        The same frame written to disk.
    """
    df = build_user_reflection_feedback()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    reflections = write_user_reflection_feedback()
    print(f"Wrote {USER_REFLECTION_FEEDBACK_CSV}")
    print(f"rows={len(reflections)}")
    print(f"columns={list(reflections.columns)}")
