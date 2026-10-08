"""Study 2 prompt templates shared across experiments.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE, JEV_OPTIMIZED_STUDY_PROMPT_TEMPLATE"
"""

from shared.models.llm.prompt import (
    JEV_OPTIMIZED_STUDY_PROMPT_TEMPLATE,
    OPTIMIZED_STUDY_PROMPT_TEMPLATE,
    format_optimized_study_prompt,
)

__all__ = [
    "JEV_OPTIMIZED_STUDY_PROMPT_TEMPLATE",
    "OPTIMIZED_STUDY_PROMPT_TEMPLATE",
    "format_optimized_study_prompt",
]
