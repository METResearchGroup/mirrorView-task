"""Quote keyword search terms for Bluesky and Twitter ingest queries.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.query_terms import quote_query_term"
"""

from __future__ import annotations


def quote_query_term(keyword: str) -> str:
    """Wrap a keyword in quotes when it contains whitespace or search-syntax characters."""
    raise NotImplementedError
