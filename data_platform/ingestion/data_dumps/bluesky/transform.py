"""Map Bluesky warehouse dump rows onto the Bluesky ingest record shape.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.transform import dump_post_to_sync_row"
"""

from __future__ import annotations

from collections.abc import Mapping


def dump_post_to_sync_row(
    row: Mapping[str, object],
    sync_timestamp: str,
) -> dict[str, object]:
    raise NotImplementedError
