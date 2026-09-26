"""Load Phase 2 Part 2+3 union stimuli and keep/remove labels for BERTopic.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import load_stimuli_posts"
"""

from __future__ import annotations

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
)

N_STIMULI_EXPECTED = 20_000

from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import dedupe_stimuli
from experiments.bertopic_original_mirror_part3_2026_09_24.src.paths import TextRole, require_text_role

POST_ID_COLUMN = "post_id"
STIMULUS_ID_COLUMN = "post_primary_key"
MIRRORED_TEXT_COLUMN = "mirrored_text"
ORIGINAL_TEXT_COLUMN = "original_text"
MIRROR_TEXT_COLUMN = "mirror_text"
PLATFORM_SEPARATOR = "_"

KEEP_REMOVE_COLUMNS = [
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

ROLE_TEXT_COLUMNS = {
    TextRole.ORIGINAL.value: ORIGINAL_TEXT_COLUMN,
    TextRole.MIRROR.value: MIRROR_TEXT_COLUMN,
}


def _platform_from_post_id(post_id: pd.Series) -> pd.Series:
    """Return the source platform prefix of each post id."""
    return post_id.astype(str).str.split(PLATFORM_SEPARATOR, n=1).str[0]


def load_stimuli_posts() -> pd.DataFrame:
    """Load Part 2+3 union stimuli with experiment column names.

    Returns
    -------
    pandas.DataFrame
        One row per stimulus post with ``post_id``, ``original_text``,
        ``mirror_text``, stance, toxicity, and ``platform``.
    """
    stimuli = load_dataset(STUDY_PHASE_2_PART_2_AND_3_STIMULI, low_memory=False)
    renamed = stimuli.rename(
        columns={STIMULUS_ID_COLUMN: POST_ID_COLUMN, MIRRORED_TEXT_COLUMN: MIRROR_TEXT_COLUMN}
    )
    renamed[POST_ID_COLUMN] = renamed[POST_ID_COLUMN].astype(str).str.strip()
    renamed["platform"] = _platform_from_post_id(renamed[POST_ID_COLUMN])
    return renamed.reset_index(drop=True)


def load_keep_remove_posts() -> pd.DataFrame:
    """Load Part 2+3 union modal keep/remove labels.

    Returns
    -------
    pandas.DataFrame
        Rated posts, including nullable ``is_unanimous``.

    Raises
    ------
    KeyError
        If a required label column is missing.
    """
    labels = load_dataset(STUDY_PHASE_2_PART_2_AND_3_KEEP_REMOVE_LABELS, low_memory=False)
    if "message_id" in labels.columns and POST_ID_COLUMN not in labels.columns:
        labels = labels.rename(columns={"message_id": POST_ID_COLUMN})
    labels[POST_ID_COLUMN] = labels[POST_ID_COLUMN].astype(str).str.strip()
    missing = set(KEEP_REMOVE_COLUMNS) - set(labels.columns)
    if missing:
        raise KeyError(f"Keep/remove labels missing columns: {sorted(missing)}")
    labels["is_unanimous"] = labels["is_unanimous"].astype("boolean")
    return labels.reset_index(drop=True)


def select_text_column(role: str) -> str:
    """Return the text column for a single-role fit.

    Parameters
    ----------
    role
        ``original`` or ``mirror``.

    Returns
    -------
    str
        Column name.

    Raises
    ------
    ValueError
        If ``role`` is ``joint`` or unknown.
    """
    validated = require_text_role(role)
    if validated == TextRole.JOINT.value:
        raise ValueError("joint has no single text column; use build_joint_frame")
    return ROLE_TEXT_COLUMNS[validated]


def texts_for_role(frame: pd.DataFrame, role: str) -> list[str]:
    """Return the text strings for ``role``.

    Parameters
    ----------
    frame
        Posts with original and mirror text.
    role
        ``original`` or ``mirror``.

    Returns
    -------
    list[str]
        One string per row.
    """
    column = select_text_column(role)
    return frame[column].astype(str).tolist()


def _role_rows(deduped: pd.DataFrame, role: str) -> pd.DataFrame:
    """Return one text row per post for ``role``."""
    return pd.DataFrame(
        {
            "post_id": deduped[POST_ID_COLUMN],
            "text": deduped[select_text_column(role)].astype(str),
            "text_role": role,
            "pair_post_id": deduped[POST_ID_COLUMN],
        }
    )


def build_joint_frame(deduped: pd.DataFrame) -> pd.DataFrame:
    """Stack original and mirror rows for a pooled fit.

    Parameters
    ----------
    deduped
        Deduped stimuli with original and mirror text.

    Returns
    -------
    pandas.DataFrame
        Two rows per post: ``post_id``, ``text``, ``text_role``, ``pair_post_id``.
    """
    original_rows = _role_rows(deduped, TextRole.ORIGINAL.value)
    mirror_rows = _role_rows(deduped, TextRole.MIRROR.value)
    return pd.concat([original_rows, mirror_rows], ignore_index=True)


def _with_text_column(deduped: pd.DataFrame, role: str) -> pd.DataFrame:
    """Return ``deduped`` plus a ``text`` column for ``role``."""
    labeled = deduped.copy()
    labeled["text"] = labeled[select_text_column(role)].astype(str)
    return labeled.reset_index(drop=True)


def load_fit_corpus(role: str) -> pd.DataFrame:
    """Load the deduped fit corpus for ``role``.

    Parameters
    ----------
    role
        ``original``, ``mirror``, or ``joint``.

    Returns
    -------
    pandas.DataFrame
        Deduped stimuli with ``text``, or the stacked joint frame.
    """
    validated = require_text_role(role)
    stimuli = load_stimuli_posts()
    deduped, _report = dedupe_stimuli(stimuli)
    if validated == TextRole.JOINT.value:
        return build_joint_frame(deduped)
    return _with_text_column(deduped, validated)
