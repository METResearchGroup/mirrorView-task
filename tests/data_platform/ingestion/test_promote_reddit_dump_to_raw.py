from __future__ import annotations

from data_platform.ingestion.data_dumps.reddit.promote_to_raw import (
    DUMP_DATASET_CONFIG,
    promote_dump_sources_to_raw,
)


def test_scaffold_imports_promote_caller() -> None:
    assert DUMP_DATASET_CONFIG.name == "pushshift_dump.yaml"
    assert callable(promote_dump_sources_to_raw)
