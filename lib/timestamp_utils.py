"""Shared timestamp generation, formatting, and parsing.

Import helpers from this module. Do not add timestamp format strings or
conversion functions in other files.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from lib.timestamp_utils import get_current_timestamp; print(get_current_timestamp())"
"""

from datetime import datetime, timezone

RUN_TIMESTAMP_FORMAT: str = "%Y_%m_%d-%H:%M:%S"
CREATED_AT_FORMAT: str = RUN_TIMESTAMP_FORMAT


def utc_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
) -> datetime:
    """Return an aware UTC datetime for the given civil time."""
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def unix_seconds(value: datetime) -> float:
    """Return the POSIX timestamp for an aware datetime."""
    return value.timestamp()


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def format_run_timestamp(value: datetime) -> str:
    """Format a datetime as a pipeline run-directory timestamp."""
    return value.astimezone(timezone.utc).strftime(RUN_TIMESTAMP_FORMAT)


def get_current_timestamp() -> str:
    """Return the current UTC time as a pipeline run-directory timestamp."""
    return format_run_timestamp(utc_now())


def format_iso_created_at(value: datetime) -> str:
    """Format a datetime as ISO-8601 UTC for raw-row created_at."""
    if value.tzinfo is None:
        aware = value.replace(tzinfo=timezone.utc)
    else:
        aware = value.astimezone(timezone.utc)
    return aware.isoformat()


def get_current_iso_created_at() -> str:
    """Return the current UTC time as ISO-8601 created_at."""
    return format_iso_created_at(utc_now())


def iso_created_at_from_unix(unix_seconds_value: float) -> str:
    """Format a POSIX timestamp as ISO-8601 UTC for raw-row created_at."""
    return format_iso_created_at(
        datetime.fromtimestamp(unix_seconds_value, tz=timezone.utc)
    )


def parse_iso_created_at(value: str) -> datetime:
    """Parse an ISO-8601 created_at string into an aware UTC datetime."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
