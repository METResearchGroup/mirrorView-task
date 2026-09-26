"""Build and materialize combined Part 2 + Part 3 keep/remove labels.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_2_and_3/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.registry import (
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_AND_3_STIMULI,
)
from shared.data.transformed.study_phase_2_part_3.transform import (
    OUTPUT_COLUMNS,
    build_keep_remove_labels as _build_keep_remove_labels,
)

OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_labels.csv"


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
    stimuli: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build modal keep/remove labels for the combined Part 2 and 3 cohort."""
    return _build_keep_remove_labels(
        raw,
        stimuli,
        results_dataset=STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
        stimuli_dataset=STUDY_PHASE_2_PART_2_AND_3_STIMULI,
    )


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write combined keep/remove labels to CSV and return the frame."""
    labels = build_keep_remove_labels()
    path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(path, index=False)
    return labels


if __name__ == "__main__":
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(f"decision={labels['decision'].value_counts().to_dict()}")
    print(f"columns={list(labels.columns)}")


__all__ = ["OUTPUT_COLUMNS", "build_keep_remove_labels", "write_keep_remove_labels"]
