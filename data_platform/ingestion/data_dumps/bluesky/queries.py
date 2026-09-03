"""Bluesky Jetstream dump SQL for Athena.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""


def posts_for_utc_day_sql() -> str:
    """Return the posts SELECT for the configured UTC day window."""
    raise NotImplementedError
