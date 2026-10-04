"""Study 2 prompt templates shared across experiments.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE"
"""

from shared.models.llm.prompt import OPTIMIZED_STUDY_PROMPT_TEMPLATE

__all__ = ["OPTIMIZED_STUDY_PROMPT_TEMPLATE"]
