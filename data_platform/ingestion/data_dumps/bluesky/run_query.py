"""Download Bluesky Jetstream posts for one UTC day via Athena.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations


def main() -> int:
    """Run the posts SELECT and download the Athena result CSV."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
