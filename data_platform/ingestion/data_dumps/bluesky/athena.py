"""Athena client for Bluesky Jetstream dump queries.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations

import re

import boto3

DEFAULT_REGION = "us-east-2"
ALLOWED_FIRST_TOKENS = frozenset({"SELECT", "WITH"})


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
        _validate_read_only_query(query)
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


def _strip_leading_sql_comments(query: str) -> str:
    remaining = query.lstrip()
    while remaining.startswith("--"):
        newline_index = remaining.find("\n")
        if newline_index == -1:
            return ""
        remaining = remaining[newline_index + 1 :].lstrip()
    return remaining


def _first_sql_token(query: str) -> str:
    remaining = _strip_leading_sql_comments(query)
    match = re.match(r"(\w+)", remaining, flags=re.IGNORECASE)
    if match is None:
        return ""
    return match.group(1).upper()


def _validate_read_only_query(query: str) -> None:
    first_token = _first_sql_token(query)
    if first_token in ALLOWED_FIRST_TOKENS:
        return
    if not first_token:
        raise ValueError("Query must start with SELECT or WITH")
    raise ValueError(f"Only read-only SELECT queries are allowed, got {first_token}")
