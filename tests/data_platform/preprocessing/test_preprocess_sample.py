from __future__ import annotations

from data_platform.preprocessing.sample_records import (
    SOURCE_RAW_RUN_COLUMN,
    sample_records_per_source_run,
)


def test_scaffold_imports_sample_records() -> None:
    assert SOURCE_RAW_RUN_COLUMN == "source_raw_run"
    assert callable(sample_records_per_source_run)
