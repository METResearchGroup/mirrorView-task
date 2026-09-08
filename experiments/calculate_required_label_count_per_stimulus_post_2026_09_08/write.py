"""Write remaining label counts locally, upload to S3, and write RESULTS.md.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import pandas as pd


def write_required_label_counts(counts: pd.DataFrame) -> object:
    """Write the local CSV, upload it, and write RESULTS.md."""
    raise NotImplementedError


def print_run_summary(result: object) -> None:
    """Print remaining label totals and the S3 URI."""
    raise NotImplementedError
