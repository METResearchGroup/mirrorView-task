"""Bluesky Jetstream dump SQL for Athena.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

GLUE_DATABASE = "bluesky_raw"
ATHENA_WORKGROUP = "bluesky_raw_maintenance"
DAY_START = "2026-09-01 00:00:00 UTC"
DAY_END = "2026-09-02 00:00:00 UTC"


def posts_for_utc_day_sql() -> str:
    """Return the posts SELECT for the configured UTC day window.

    Returns
    -------
    str
        Athena SQL selecting ``uri``, ``did``, ``created_at``, and ``text`` for
        posts created on the configured UTC day.
    """
    return f"""SELECT
  uri,
  did,
  created_at,
  text
FROM posts
WHERE created_at >= TIMESTAMP '{DAY_START}'
  AND created_at <  TIMESTAMP '{DAY_END}'"""

