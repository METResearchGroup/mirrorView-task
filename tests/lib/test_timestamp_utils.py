"""Tests for lib.timestamp_utils.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/lib/test_timestamp_utils.py
"""

from __future__ import annotations

from datetime import timezone

from lib.timestamp_utils import (
    format_iso_created_at,
    format_run_timestamp,
    get_current_iso_created_at,
    get_current_timestamp,
    iso_created_at_from_unix,
    parse_iso_created_at,
    unix_seconds,
    utc_datetime,
    utc_now,
)


class TestUtcDatetime:
    """Tests for utc_datetime()."""

    def test_returns_aware_utc_datetime(self) -> None:
        """utc_datetime attaches timezone.utc."""
        result = utc_datetime(2026, 5, 30, 10, 0, 0)
        expected = utc_datetime(2026, 5, 30, 10, 0, 0)
        assert result == expected
        assert result.tzinfo is timezone.utc


class TestUnixSeconds:
    """Tests for unix_seconds()."""

    def test_round_trips_utc_datetime(self) -> None:
        """unix_seconds matches datetime.timestamp()."""
        moment = utc_datetime(2026, 5, 30, 0, 0, 0)
        result = unix_seconds(moment)
        expected = moment.timestamp()
        assert result == expected


class TestUtcNow:
    """Tests for utc_now()."""

    def test_returns_aware_utc_datetime(self) -> None:
        """utc_now is timezone-aware UTC."""
        result = utc_now()
        assert result.tzinfo is timezone.utc


class TestFormatRunTimestamp:
    """Tests for format_run_timestamp()."""

    def test_uses_pipeline_run_directory_format(self) -> None:
        """Run timestamps use YYYY_MM_DD-HH:MM:SS."""
        result = format_run_timestamp(utc_datetime(2026, 5, 30, 10, 0, 0))
        expected = "2026_05_30-10:00:00"
        assert result == expected


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp()."""

    def test_matches_run_timestamp_format(self) -> None:
        """Current timestamp uses the same run-directory format."""
        result = get_current_timestamp()
        parsed = format_run_timestamp(utc_datetime(2026, 1, 1, 0, 0, 0))
        assert len(result) == len(parsed)
        assert result[4] == "_"
        assert result[7] == "_"
        assert result[10] == "-"


class TestFormatIsoCreatedAt:
    """Tests for format_iso_created_at()."""

    def test_formats_aware_utc_datetime(self) -> None:
        """ISO created_at uses datetime.isoformat() in UTC."""
        result = format_iso_created_at(utc_datetime(2026, 5, 30, 0, 0, 0))
        expected = "2026-05-30T00:00:00+00:00"
        assert result == expected


class TestGetCurrentIsoCreatedAt:
    """Tests for get_current_iso_created_at()."""

    def test_returns_parseable_iso_utc(self) -> None:
        """Current ISO created_at parses back to UTC."""
        result = get_current_iso_created_at()
        parsed = parse_iso_created_at(result)
        assert parsed.tzinfo is timezone.utc


class TestIsoCreatedAtFromUnix:
    """Tests for iso_created_at_from_unix()."""

    def test_formats_posix_seconds(self) -> None:
        """Unix seconds become the same ISO string as format_iso_created_at."""
        moment = utc_datetime(2026, 5, 30, 0, 0, 0)
        result = iso_created_at_from_unix(unix_seconds(moment))
        expected = format_iso_created_at(moment)
        assert result == expected


class TestParseIsoCreatedAt:
    """Tests for parse_iso_created_at()."""

    def test_parses_offset_and_z_suffix(self) -> None:
        """Z and +00:00 parse to the same UTC datetime."""
        moment = utc_datetime(2026, 5, 30, 0, 0, 0)
        offset_form = format_iso_created_at(moment)
        result_offset = parse_iso_created_at(offset_form)
        result_z = parse_iso_created_at("2026-05-30T00:00:00Z")
        assert result_offset == moment
        assert result_z == moment
