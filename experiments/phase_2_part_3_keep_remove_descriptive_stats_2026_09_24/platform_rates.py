"""Build platform keep/remove crosstabs from per-post vote counts and stimuli.

Run from repo root::

    PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_platform_rates.py -q
"""

from __future__ import annotations

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_STIMULI

PLATFORM_BY_PREFIX: dict[str, str] = {
    "bluesky": "Bluesky",
    "reddit": "Reddit",
    "twitter": "Twitter",
}
PLATFORM_COLUMNS: tuple[str, ...] = ("Bluesky", "Reddit", "Twitter")
DECISION_ROWS: tuple[str, ...] = ("keep", "remove")

TOXICITY_BY_SAMPLE_TYPE: dict[str, str] = {
    "sample_low_toxicity": "low toxicity",
    "sample_middle_toxicity": "medium toxicity",
    "sample_high_toxicity": "high toxicity",
}
TOXICITY_ORDER: tuple[str, ...] = (
    "low toxicity",
    "medium toxicity",
    "high toxicity",
)
PLATFORM_TOXICITY_COLUMNS: tuple[str, ...] = tuple(
    f"{platform} {toxicity}"
    for platform in PLATFORM_COLUMNS
    for toxicity in TOXICITY_ORDER
)

PROPORTION_DECIMALS = 4

_LABELED_POST_COLUMNS = [
    "post_id",
    "decision",
    "platform",
    "toxicity",
    "platform_toxicity",
]


def modal_decision(keep_count: int, remove_count: int) -> str:
    """Return the modal keep or remove label for vote counts.

    Parameters
    ----------
    keep_count
        Number of keep votes.
    remove_count
        Number of remove votes.

    Returns
    -------
    str
        ``"keep"`` when ``keep_count > remove_count``; otherwise ``"remove"``.
    """
    if keep_count > remove_count:
        return "keep"
    return "remove"


def derive_platform(post_id: str) -> str:
    """Map a post id prefix to a display platform name.

    Parameters
    ----------
    post_id
        Post identifier whose prefix precedes the first underscore.

    Returns
    -------
    str
        Display platform label from ``PLATFORM_BY_PREFIX``.

    Raises
    ------
    ValueError
        When the prefix is not recognized.
    """
    prefix = str(post_id).split("_", 1)[0]
    try:
        return PLATFORM_BY_PREFIX[prefix]
    except KeyError as exc:
        raise ValueError(
            f"Unknown platform prefix {prefix!r} in post_id={post_id!r}"
        ) from exc


def derive_toxicity_label(sample_toxicity_type: str) -> str:
    """Map a stimuli sample type to a display toxicity label.

    Parameters
    ----------
    sample_toxicity_type
        Raw ``sample_toxicity_type`` value from stimuli.

    Returns
    -------
    str
        Display toxicity label from ``TOXICITY_BY_SAMPLE_TYPE``.

    Raises
    ------
    ValueError
        When the sample type is not recognized.
    """
    key = str(sample_toxicity_type).strip()
    try:
        return TOXICITY_BY_SAMPLE_TYPE[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown sample_toxicity_type {sample_toxicity_type!r}"
        ) from exc


def join_stimuli_for_platform(
    per_post: pd.DataFrame, stimuli: pd.DataFrame
) -> pd.DataFrame:
    """Inner-join per-post rows to stimuli on post id.

    Parameters
    ----------
    per_post
        Per-post vote frame with a ``post_id`` column.
    stimuli
        Stimuli frame with ``post_primary_key`` and ``sample_toxicity_type``.

    Returns
    -------
    pandas.DataFrame
        Joined rows with stimuli toxicity fields.

    Raises
    ------
    ValueError
        When stimuli keys are duplicated or any per-post id lacks a match.
    """
    raise NotImplementedError


def build_labeled_posts(
    per_post: pd.DataFrame, stimuli: pd.DataFrame
) -> pd.DataFrame:
    """Assign modal decisions plus platform and toxicity labels.

    Parameters
    ----------
    per_post
        Per-post vote frame with ``post_id``, ``keep_count``, and ``remove_count``.
    stimuli
        Stimuli frame for toxicity lookup.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``post_id``, ``decision``, ``platform``,
        ``toxicity``, and ``platform_toxicity`` columns.

    Raises
    ------
    ValueError
        When stimuli join validation fails.
    """
    raise NotImplementedError


def build_platform_crosstab(labeled_posts: pd.DataFrame) -> pd.DataFrame:
    """Build a keep/remove by platform count matrix.

    Parameters
    ----------
    labeled_posts
        Labeled posts with ``decision`` and ``platform`` columns.

    Returns
    -------
    pandas.DataFrame
        Integer counts indexed by ``DECISION_ROWS`` and ``PLATFORM_COLUMNS``.
    """
    raise NotImplementedError


def build_platform_toxicity_crosstab(labeled_posts: pd.DataFrame) -> pd.DataFrame:
    """Build a keep/remove by platform×toxicity count matrix.

    Parameters
    ----------
    labeled_posts
        Labeled posts with ``decision`` and ``platform_toxicity`` columns.

    Returns
    -------
    pandas.DataFrame
        Integer counts indexed by ``DECISION_ROWS`` and ``PLATFORM_TOXICITY_COLUMNS``.
    """
    raise NotImplementedError


def column_proportions(counts: pd.DataFrame) -> pd.DataFrame:
    """Compute column-wise keep/remove shares.

    Parameters
    ----------
    counts
        Integer crosstab with decision rows and platform columns.

    Returns
    -------
    pandas.DataFrame
        Float proportions; zero-sum columns become ``pd.NA``.
    """
    raise NotImplementedError


def load_stimuli() -> pd.DataFrame:
    """Load Phase 2 Part 3 stimuli from the dataset registry.

    Returns
    -------
    pandas.DataFrame
        Stimuli frame for toxicity lookup.
    """
    raise NotImplementedError
