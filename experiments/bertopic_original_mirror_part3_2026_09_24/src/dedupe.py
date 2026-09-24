"""Dedupe Phase 2 Part 2+3 union stimuli before topic fitting.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import dedupe_stimuli"
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DUPLICATE_ORIGINAL_RULE = "drop_duplicates on original_text keep first by post_id ascending"
IDENTICAL_PAIR_RULE = "drop rows where original_text == mirror_text"


def _sorted_by_post_id(stimuli: pd.DataFrame) -> pd.DataFrame:
    """Return stimuli sorted by ``post_id`` ascending."""
    return stimuli.sort_values("post_id", kind="mergesort").reset_index(drop=True)


def _drop_duplicate_originals(sorted_stimuli: pd.DataFrame) -> pd.DataFrame:
    """Keep the first row for each ``original_text``."""
    return sorted_stimuli.drop_duplicates(subset=["original_text"], keep="first")


def _drop_identical_pairs(stimuli: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose mirror text equals the original text."""
    identical = stimuli["original_text"] == stimuli["mirror_text"]
    return stimuli.loc[~identical].reset_index(drop=True)


def build_dedupe_report(
    before: pd.DataFrame,
    after: pd.DataFrame,
    removed_dup_orig: int,
    removed_identical: int,
) -> dict:
    """Build the dedupe count report.

    Parameters
    ----------
    before
        Stimulus frame before dedupe.
    after
        Stimulus frame after both drops.
    removed_dup_orig
        Rows removed as duplicate originals.
    removed_identical
        Rows removed because mirror text matched original text.

    Returns
    -------
    dict
        Counts and the two dedupe rules.
    """
    return {
        "n_stimuli_raw": int(len(before)),
        "n_removed_duplicate_original": int(removed_dup_orig),
        "n_removed_identical_pair": int(removed_identical),
        "n_after_dedupe": int(len(after)),
        "dedupe_rule_duplicate_original": DUPLICATE_ORIGINAL_RULE,
        "dedupe_rule_identical_pair": IDENTICAL_PAIR_RULE,
    }


def dedupe_stimuli(stimuli: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop duplicate originals, then identical original-mirror pairs.

    Parameters
    ----------
    stimuli
        Frame with ``post_id``, ``original_text``, and ``mirror_text``.

    Returns
    -------
    tuple[pandas.DataFrame, dict]
        Deduped frame and the report from ``build_dedupe_report``.
    """
    sorted_stimuli = _sorted_by_post_id(stimuli)
    without_duplicate_originals = _drop_duplicate_originals(sorted_stimuli)
    deduped = _drop_identical_pairs(without_duplicate_originals)
    removed_duplicates = len(sorted_stimuli) - len(without_duplicate_originals)
    removed_identical = len(without_duplicate_originals) - len(deduped)
    report = build_dedupe_report(stimuli, deduped, removed_duplicates, removed_identical)
    return deduped, report


def write_dedupe_report(path: Path, report: dict) -> None:
    """Write ``report`` as JSON.

    Parameters
    ----------
    path
        Destination path.
    report
        Report dict from ``build_dedupe_report``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
