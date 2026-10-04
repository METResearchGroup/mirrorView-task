"""Compile the optimized keep or remove prompt into one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import build_optimized_remove_request"
"""

from __future__ import annotations

from langchain_typesafe import ClassifierRequest

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord


def build_optimized_remove_instructions(prompt: str) -> str:
    """Return optimized instructions with the dynamic pair block removed.

    Parameters
    ----------
    prompt
        Balanced GEPA template that ends with ``keep or remove``.

    Returns
    -------
    str
        Demonstrations preserved, ending with the state-pointer remove question.

    Raises
    ------
    ValueError
        When the dynamic block count is not one, or the prompt does not end
        with ``keep or remove``.
    """
    raise NotImplementedError


def build_optimized_remove_request(record: Study2InputRecord) -> ClassifierRequest:
    """Build one optimized-prompt classifier request for the current pair.

    Parameters
    ----------
    record
        Prepared Study 2 pair. Its texts go in classifier state only.

    Returns
    -------
    ClassifierRequest
        State for the two posts and one remove question using the compiled prompt.
    """
    raise NotImplementedError


OPTIMIZED_REMOVE_INSTRUCTIONS = ""
