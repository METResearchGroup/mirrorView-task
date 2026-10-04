"""Compile the optimized keep or remove prompt into one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import build_optimized_remove_request"
"""

from __future__ import annotations

from langchain_typesafe import ClassifierRequest

from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import (
    REMOVE_QUESTION,
    build_remove_request,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord
from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE

_DYNAMIC_BLOCK = "Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n"
_TERMINAL_LINE = "keep or remove"
_REQUIRED_DYNAMIC_BLOCK_COUNT = 1


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
    _reject_dynamic_block_count(prompt)
    _reject_nonterminal_line(prompt)
    without_block = prompt.replace(_DYNAMIC_BLOCK, "", _REQUIRED_DYNAMIC_BLOCK_COUNT)
    return without_block[: -len(_TERMINAL_LINE)] + REMOVE_QUESTION


def _reject_dynamic_block_count(prompt: str) -> None:
    if prompt.count(_DYNAMIC_BLOCK) != _REQUIRED_DYNAMIC_BLOCK_COUNT:
        raise ValueError("optimized prompt must contain one dynamic pair block")


def _reject_nonterminal_line(prompt: str) -> None:
    if not prompt.endswith(_TERMINAL_LINE):
        raise ValueError("optimized prompt must end with keep or remove")


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
    return build_remove_request(record, instructions=OPTIMIZED_REMOVE_INSTRUCTIONS)


OPTIMIZED_REMOVE_INSTRUCTIONS = build_optimized_remove_instructions(
    OPTIMIZED_STUDY_PROMPT_TEMPLATE
)
