from __future__ import annotations

import pytest

from data_platform.ingestion.query_terms import quote_query_term

PLAIN_KEYWORD = "climate"
PHRASE_KEYWORD = "climate change"
OPERATOR_KEYWORD = "lang:en"
QUOTED_KEYWORD = 'say "hello"'


class TestQuoteQueryTerm:
    """Tests for quote_query_term()."""

    @pytest.mark.parametrize(
        ("keyword", "expected"),
        [
            (PLAIN_KEYWORD, PLAIN_KEYWORD),
            (PHRASE_KEYWORD, '"climate change"'),
            (OPERATOR_KEYWORD, '"lang:en"'),
            (QUOTED_KEYWORD, '"say \\"hello\\""'),
        ],
    )
    def test_quotes_terms_that_need_search_syntax(self, keyword: str, expected: str) -> None:
        result = quote_query_term(keyword)

        assert result == expected
