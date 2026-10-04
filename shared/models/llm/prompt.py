"""Issue 351 optimized Study 2 keep or remove prompt.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.llm.prompt import format_optimized_study_prompt"
"""

from __future__ import annotations


def format_optimized_study_prompt(post_1_text: str, post_2_text: str) -> str:
    """Render the optimized prompt with the two post texts inserted."""
    raise NotImplementedError
