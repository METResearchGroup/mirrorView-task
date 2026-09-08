"""Combine four pinned curated parquet files into one stimulus dataset.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the four pinned curated objects exist at the hashes in sources.py
when PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
then combined_rows=55573
and local dataset.parquet exists
and S3 object experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet exists
and its SHA-256 matches the local file
and RESULTS.md contains the overall stance by toxicity table
and RESULTS.md contains the three-platform stance by toxicity table
and stdout prints both tables

given the S3 dataset.parquet key already exists
when the command is run again
then the process raises FileExistsError and does not change the four source objects

Run from the repo root:

    PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
"""

from __future__ import annotations

import sys

from experiments.combine_data_into_stimulus_set_2026_09_08.crosstab import (
    stance_by_toxicity,
    stance_by_toxicity_by_integration,
)
from experiments.combine_data_into_stimulus_set_2026_09_08.load import load_curated_source
from experiments.combine_data_into_stimulus_set_2026_09_08.normalize import (
    normalize_curated_frame,
)
from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_ROW_COUNT,
    SORT_COLUMNS,
    pinned_sources,
)
from experiments.combine_data_into_stimulus_set_2026_09_08.write import (
    print_run_summary,
    write_combined_dataset,
)
import pandas as pd


def concatenate_curated_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate normalized source tables and sort them.

    Parameters
    ----------
    frames
        Normalized tables in pinned-source order.

    Returns
    -------
    pd.DataFrame
        Combined table sorted by integration, dataset id, and source record id.

    Raises
    ------
    ValueError
        When the combined row count is not 55573.
    """
    combined = pd.concat(frames, ignore_index=True)
    sorted_combined = combined.sort_values(
        list(SORT_COLUMNS),
        kind="mergesort",
    ).reset_index(drop=True)
    if len(sorted_combined) != COMBINED_ROW_COUNT:
        raise ValueError(f"combined_rows={len(sorted_combined)}")
    return sorted_combined


def main() -> int:
    """Load, combine, write, and print the stimulus dataset."""
    sources = pinned_sources()
    frames = [
        normalize_curated_frame(load_curated_source(source), source) for source in sources
    ]
    combined = concatenate_curated_frames(frames)
    overall = stance_by_toxicity(combined)
    by_integration = stance_by_toxicity_by_integration(combined)
    result = write_combined_dataset(combined, overall, by_integration)
    print_run_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
