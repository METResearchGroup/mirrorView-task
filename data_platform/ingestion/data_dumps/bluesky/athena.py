"""Athena client for Bluesky Jetstream dump queries.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations


class Athena:
    """Submit read-only Athena queries and resolve result locations."""

    def __init__(self, region: str = "us-east-2") -> None:
        raise NotImplementedError

    def run_query(self, query: str, *, database: str, workgroup: str) -> str:
        """Submit a query and poll until it completes."""
        raise NotImplementedError

    def get_output_location(self, execution_id: str) -> str:
        """Return the S3 URI of the result CSV for a completed query execution."""
        raise NotImplementedError
