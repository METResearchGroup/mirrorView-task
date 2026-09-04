"""Shared preprocess fixtures for truncation and related tests."""

from __future__ import annotations

LONG_ENGLISH_TEXT = (
    "This is a clear English comment about policy and governance without links or mentions. "
    * 8
)

EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT = (
    "This is a clear English comment about policy and governance without links or mentions. "
    "This is a clear English comment about policy and governance without links or mentions. "
    "This is a clear English comment about policy and governance without links or mentions."
)
