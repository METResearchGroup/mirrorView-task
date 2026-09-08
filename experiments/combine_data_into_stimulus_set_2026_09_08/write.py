"""Write the combined parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

import pandas as pd


def write_combined_dataset(
    combined: pd.DataFrame,
    overall_crosstab: dict,
    integration_crosstab: dict,
) -> object:
    """Write local parquet, upload to S3, and write RESULTS.md."""
    raise NotImplementedError


def print_run_summary(result: object) -> None:
    """Print combined row count, URIs, SHA-256, and both crosstab tables."""
    raise NotImplementedError
