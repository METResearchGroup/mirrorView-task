"""Render the linked-fate study prompt for one original/mirror pair.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations


def render_prompt(
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool,
) -> str:
    raise NotImplementedError
