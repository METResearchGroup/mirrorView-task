"""Athena client for Bluesky Jetstream dump queries.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations

import boto3


DEFAULT_REGION = "us-east-2"


class Athena:
    """Submit read-only Athena queries and resolve result locations."""

    def __init__(self, region: str = DEFAULT_REGION) -> None:
        self.client = boto3.client("athena", region_name=region)

    def run_query(self, query: str, *, database: str, workgroup: str) -> str:
        """Submit a query and poll until it completes.

        Parameters
        ----------
        query
            Read-only SQL statement to execute.
        database
            Glue database for the query execution context.
        workgroup
            Athena workgroup name.

        Returns
        -------
        str
            Query execution identifier.

        Raises
        ------
        ValueError
            When the statement is not a read-only SELECT or WITH query.
        RuntimeError
            When Athena reports FAILED or CANCELLED.
        """
        raise NotImplementedError

    def get_output_location(self, execution_id: str) -> str:
        """Return the S3 URI of the result CSV for a completed query execution.

        Parameters
        ----------
        execution_id
            Athena query execution identifier.

        Returns
        -------
        str
            S3 URI of the query result object.
        """
        raise NotImplementedError
