"""Build stable ``{integration}_{id}`` record ids for ingest writes.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.generate_record_id import generate_record_id"
"""

from __future__ import annotations

from typing import Any, Mapping

RECORD_ID_COLUMN = "record_id"

INTEGRATION_BLUESKY = "bluesky"
INTEGRATION_REDDIT = "reddit"
INTEGRATION_TWITTER = "twitter"


def generate_record_id(integration: str, primary_key: str) -> str:
    raise NotImplementedError


def attach_record_id(row: Mapping[str, Any], integration: str) -> dict[str, Any]:
    raise NotImplementedError
