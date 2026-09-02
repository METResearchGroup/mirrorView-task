"""Quote keyword search terms that Bluesky ingest and Twitter ingest share.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.query_terms import quote_query_term"
"""

from __future__ import annotations

SEARCH_SYNTAX_CHARS = frozenset({'"', ":", "(", ")"})
QUOTE_WRAP = '"'
ESCAPED_QUOTE = '\\"'


def quote_query_term(keyword: str) -> str:
    """Return the keyword as a search term, and wrap it in quotes when it needs escaping.

    Parameters
    ----------
    keyword
        Raw keyword from ingest YAML.

    Returns
    -------
    str
        The original keyword if it has no whitespace or search operators.
        Otherwise the keyword in double quotes, with inner quotes escaped.
    """
    needs_quotes = any(ch.isspace() for ch in keyword) or any(
        ch in keyword for ch in SEARCH_SYNTAX_CHARS
    )
    if not needs_quotes:
        return keyword
    escaped = keyword.replace(QUOTE_WRAP, ESCAPED_QUOTE)
    return f"{QUOTE_WRAP}{escaped}{QUOTE_WRAP}"
