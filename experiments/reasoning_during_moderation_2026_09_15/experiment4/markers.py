"""Confirmed uncertainty, revision, and tension markers for thinking traces.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkerScore:
    """Family flags for one thinking span."""

    uncertainty: bool
    revision: bool
    tension: bool


def score_trace(thinking_text: str) -> MarkerScore:
    """Return family flags from phrases and bag-of-words tokens on thinking text."""
    raise NotImplementedError
