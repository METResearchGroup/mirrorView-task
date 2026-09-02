"""Quote keyword search terms that Bluesky ingest and Twitter ingest share.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.query_terms import quote_query_term"
"""

from __future__ import annotations


def quote_query_term(keyword: str) -> str:
    """Return the keyword, quoted when it has whitespace or search operators."""
    if any(ch.isspace() for ch in keyword) or any(ch in keyword for ch in ('"', ":", "(", ")")):
        escaped = keyword.replace('"', '\\"')
        return f'"{escaped}"'
    return keyword
