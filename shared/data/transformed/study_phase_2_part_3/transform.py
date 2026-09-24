"""Build and materialize Part 3 keep/remove labels.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_3/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_3_STIMULI,
)

STIMULI_JOIN_KEY = "post_primary_key"
RESULTS_JOIN_KEY = "post_id"
OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_labels.csv"

LINKED_FATE_MODE = "linked_fate"
KEEP_DECISION = "keep"
REMOVE_DECISION = "remove"
KEEP_REMOVE_LABEL_KEEP = 0
KEEP_REMOVE_LABEL_REMOVE = 1
MIN_RATERS_FOR_UNANIMOUS = 2
PLATFORM_SEPARATOR = "_"

OUTPUT_COLUMNS = [
    "post_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
    "keep_rate",
    "n_keep",
    "n_remove",
    "is_unanimous",
    "sampled_stance",
    "sample_toxicity_type",
    "platform",
]


def _load_slim_trial_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Select linked-fate keep/remove trials with a usable ``post_id``.

    Parameters
    ----------
    raw
        Part 3 results rows.

    Returns
    -------
    pandas.DataFrame
        Filtered trials with stripped ``post_id`` and lowercased ``decision``.

    Raises
    ------
    KeyError
        If ``evaluation_mode`` or ``post_id`` is missing.
    """
    raise NotImplementedError


def _aggregate_modal_labels_with_counts(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trials to one modal label and vote counts per post.

    Parameters
    ----------
    trials
        Slim linked-fate trial frame.

    Returns
    -------
    pandas.DataFrame
        One row per ``post_id`` with decision, label, and vote counts.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    raise NotImplementedError


def _build_unanimous_flags(trials: pd.DataFrame) -> pd.DataFrame:
    """Mark posts where every rater made the same decision.

    Parameters
    ----------
    trials
        Slim linked-fate trial frame.

    Returns
    -------
    pandas.DataFrame
        ``post_id``, ``is_unanimous``, and ``n_raters``. ``is_unanimous`` is
        null when ``n_raters`` is below ``MIN_RATERS_FOR_UNANIMOUS``.
    """
    raise NotImplementedError


def _join_stimuli_metadata(modal: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    """Attach stimulus text and metadata to modal labels.

    Parameters
    ----------
    modal
        One row per rated post, including unanimous flags.
    stimuli
        Part 3 stimulus catalog.

    Returns
    -------
    pandas.DataFrame
        Labels in ``OUTPUT_COLUMNS`` order.

    Raises
    ------
    ValueError
        If a modal ``post_id`` has no stimulus row.
    """
    raise NotImplementedError


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
    stimuli: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the Part 3 modal keep/remove frame.

    Parameters
    ----------
    raw
        Part 3 results. Loads ``STUDY_PHASE_2_PART_3_RESULTS_FULL`` when omitted.
    stimuli
        Part 3 stimuli. Loads ``STUDY_PHASE_2_PART_3_STIMULI`` when omitted.

    Returns
    -------
    pandas.DataFrame
        One row per rated post. See ``OUTPUT_COLUMNS``.

    Raises
    ------
    KeyError
        If required columns are missing.
    ValueError
        If text conflicts within a post, or a rated post lacks a stimulus.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)
    if stimuli is None:
        stimuli = load_dataset(STUDY_PHASE_2_PART_3_STIMULI, low_memory=False)
    trials = _load_slim_trial_frame(raw)
    modal = _aggregate_modal_labels_with_counts(trials)
    unanimous = _build_unanimous_flags(trials)
    labeled = modal.merge(unanimous[["post_id", "is_unanimous"]], on="post_id", how="left")
    return _join_stimuli_metadata(labeled, stimuli)


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write modal keep/remove labels to CSV and return the frame.

    Parameters
    ----------
    path
        Destination CSV. Defaults to ``keep_remove_labels.csv`` beside this module.

    Returns
    -------
    pandas.DataFrame
        The frame written to disk.
    """
    raise NotImplementedError


if __name__ == "__main__":
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(f"decision={labels['decision'].value_counts().to_dict()}")
    print(f"columns={list(labels.columns)}")
