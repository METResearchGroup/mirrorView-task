"""Shared current-timestamp helper.

Use ``get_current_timestamp`` for current timestamps. Do not add more
timestamp generators.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from lib.timestamp_utils import get_current_timestamp; print(get_current_timestamp())"
"""

from datetime import datetime, timezone

CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


def get_current_timestamp() -> str:
    """Return the current UTC time in the contract format."""
    return datetime.now(timezone.utc).strftime(CREATED_AT_FORMAT)
