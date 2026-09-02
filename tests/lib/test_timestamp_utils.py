"""Tests for lib.timestamp_utils.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/lib/test_timestamp_utils.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from lib.timestamp_utils import CREATED_AT_FORMAT, get_current_timestamp


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp()."""

    def test_uses_utc_contract_format(self) -> None:
        """Current timestamp matches CREATED_AT_FORMAT in UTC."""
        result = get_current_timestamp()
        parsed = datetime.strptime(result, CREATED_AT_FORMAT).replace(tzinfo=timezone.utc)
        assert parsed.tzinfo is timezone.utc
        assert result == parsed.strftime(CREATED_AT_FORMAT)
