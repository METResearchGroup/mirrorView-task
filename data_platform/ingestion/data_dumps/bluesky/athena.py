"""Athena client for Bluesky Jetstream dump queries.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations

import re
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

DEFAULT_REGION = "us-east-2"
ALLOWED_FIRST_TOKENS = frozenset({"SELECT", "WITH"})
QUERY_STATUS_SUCCEEDED = "SUCCEEDED"
QUERY_STATUS_FAILED = "FAILED"
QUERY_STATUS_CANCELLED = "CANCELLED"
TERMINAL_FAILURE_STATES = frozenset({QUERY_STATUS_FAILED, QUERY_STATUS_CANCELLED})
POLL_INTERVAL_SECONDS = 1
QUERY_TIMEOUT_SECONDS = 3600
UNKNOWN_STATE_CHANGE_REASON = "unknown"


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
        TimeoutError
            When the query exceeds ``QUERY_TIMEOUT_SECONDS``.
        """
        return _submit_and_wait_for_query(
            self.client,
            query,
            database,
            workgroup,
        )

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
        response = self.client.get_query_execution(QueryExecutionId=execution_id)
        return response["QueryExecution"]["ResultConfiguration"]["OutputLocation"]


def _submit_and_wait_for_query(
    client: Any,
    query: str,
    database: str,
    workgroup: str,
) -> str:
    _validate_read_only_query(query)
    execution_id = _start_query_execution(client, query, database, workgroup)
    return _wait_for_query_completion(client, execution_id)


def _start_query_execution(
    client: Any,
    query: str,
    database: str,
    workgroup: str,
) -> str:
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup,
    )
    return response["QueryExecutionId"]


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


def _wait_for_query_completion(client: Any, execution_id: str) -> str:
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    while True:
        state = client.get_query_execution(QueryExecutionId=execution_id)
        status = state["QueryExecution"]["Status"]["State"]
        if status == QUERY_STATUS_SUCCEEDED:
            return execution_id
        if status in TERMINAL_FAILURE_STATES:
            raise RuntimeError(_format_terminal_failure(state, status))
        _raise_if_query_timed_out(client, execution_id, deadline)
        time.sleep(POLL_INTERVAL_SECONDS)


def _format_terminal_failure(state: dict[str, Any], status: str) -> str:
    reason = state["QueryExecution"]["Status"].get(
        "StateChangeReason",
        UNKNOWN_STATE_CHANGE_REASON,
    )
    return f"Athena query {status}: {reason}"


def _raise_if_query_timed_out(
    client: Any,
    execution_id: str,
    deadline: float,
) -> None:
    if time.monotonic() < deadline:
        return
    _cancel_query_execution(client, execution_id)
    raise TimeoutError(
        f"Athena query {execution_id} exceeded {QUERY_TIMEOUT_SECONDS} seconds"
    )


def _cancel_query_execution(client: Any, execution_id: str) -> None:
    try:
        client.stop_query_execution(QueryExecutionId=execution_id)
    except (BotoCoreError, ClientError):
        return
