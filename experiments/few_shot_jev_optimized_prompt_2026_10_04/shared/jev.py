"""Compile the optimized keep or remove prompt into one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import build_optimized_remove_request"
"""

from __future__ import annotations


def build_optimized_remove_instructions(prompt):
    raise NotImplementedError


def build_optimized_remove_request(record):
    raise NotImplementedError


OPTIMIZED_REMOVE_INSTRUCTIONS = ""
