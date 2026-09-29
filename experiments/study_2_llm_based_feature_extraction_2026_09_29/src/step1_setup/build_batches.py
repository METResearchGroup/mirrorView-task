"""Build mining batches of kept and removed pairs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    BATCH_ID_PREFIX,
    BATCH_ID_WIDTH,
    KEEP_PAIRS_PER_BATCH,
    MODAL_LABEL_KEEP,
    MODAL_LABEL_REMOVE,
    REMOVE_PAIRS_PER_BATCH,
)


def shuffled_post_ids(
    cohort: pd.DataFrame, modal_label: str, rng: np.random.Generator
) -> list[str]:
    """Return shuffled post ids for one modal label.

    Parameters
    ----------
    cohort
        Cohort with ``post_id`` and ``modal_label``.
    modal_label
        ``keep`` or ``remove`` label to filter on.
    rng
        NumPy random generator used for the permutation.

    Returns
    -------
    list[str]
        Post ids in shuffled order.
    """
    raise NotImplementedError


def format_batch_id(index: int) -> str:
    """Format a zero-padded batch identifier.

    Parameters
    ----------
    index
        Batch index starting at zero.

    Returns
    -------
    str
        Batch id such as ``batch_007``.
    """
    return f"{BATCH_ID_PREFIX}{index:0{BATCH_ID_WIDTH}d}"


def build_batches(cohort: pd.DataFrame, seed: int) -> list[dict]:
    """Build mining batches of kept and removed post ids.

    Parameters
    ----------
    cohort
        Cohort with modal labels.
    seed
        Random seed for shuffling keep then remove ids.

    Returns
    -------
    list[dict]
        Each dict has ``batch_id``, ``keep_post_ids``, and ``remove_post_ids``.
    """
    raise NotImplementedError
