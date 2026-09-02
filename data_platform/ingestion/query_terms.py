"""Quote keyword search terms shared by Bluesky and Twitter ingest.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.query_terms import quote_query_term"
"""

from __future__ import annotations

SEARCH_SYNTAX_CHARS = frozenset({'"', ":", "(", ")"})
QUOTE_WRAP = '"'
ESCAPED_QUOTE = '\\"'


def quote_query_term(keyword: str) -> str:
    """Return a search term, quoted when it needs search-syntax escaping.

    Parameters
    ----------
    keyword
        Raw keyword from ingest YAML.

    Returns
    -------
    str
        The original keyword, or a double-quoted escaped form when the
        keyword contains whitespace or search operators.
    """
    needs_quotes = any(ch.isspace() for ch in keyword) or any(
        ch in keyword for ch in SEARCH_SYNTAX_CHARS
    )
    if not needs_quotes:
        return keyword
    escaped = keyword.replace(QUOTE_WRAP, ESCAPED_QUOTE)
    return f"{QUOTE_WRAP}{escaped}{QUOTE_WRAP}"
