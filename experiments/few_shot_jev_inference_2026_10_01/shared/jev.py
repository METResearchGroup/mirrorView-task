"""Compile the few-shot keep or remove prompt into one Jev request.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_inference_2026_10_01.shared.jev import build_few_shot_remove_request"
"""

from __future__ import annotations

from langchain_typesafe import ClassifierRequest

from experiments.few_shot_jev_inference_2026_10_01.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import (
    REMOVE_QUESTION,
    build_remove_request,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord

_DYNAMIC_BLOCK = "Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n"
_TERMINAL_QUESTION = "Allow Or Remove?"
_REQUIRED_DYNAMIC_BLOCK_COUNT = 1


def build_few_shot_remove_instructions(prompt: str) -> str:
    """Return few-shot instructions with the dynamic pair block removed.

    Parameters
    ----------
    prompt
        Issue 329 prompt, including the ten demonstrations.

    Returns
    -------
    str
        Demonstrations preserved, ending with the state-pointer remove question.

    Raises
    ------
    ValueError
        When the dynamic block is missing or repeated, or the prompt does not
        end with ``Allow Or Remove?``.
    """
    _reject_dynamic_block_count(prompt)
    _reject_nonterminal_question(prompt)
    without_block = prompt.replace(_DYNAMIC_BLOCK, "", _REQUIRED_DYNAMIC_BLOCK_COUNT)
    return without_block[: -len(_TERMINAL_QUESTION)] + REMOVE_QUESTION


def build_few_shot_remove_request(record: Study2InputRecord) -> ClassifierRequest:
    """Build one few-shot classifier request for the current pair.

    Parameters
    ----------
    record
        Prepared Study 2 pair. Its texts go in classifier state only.

    Returns
    -------
    ClassifierRequest
        State for the two posts and one remove Noul using the compiled prompt.
    """
    return build_remove_request(record, instructions=FEW_SHOT_REMOVE_INSTRUCTIONS)


def _reject_dynamic_block_count(prompt: str) -> None:
    if prompt.count(_DYNAMIC_BLOCK) != _REQUIRED_DYNAMIC_BLOCK_COUNT:
        raise ValueError("few-shot prompt must contain one dynamic pair block")


def _reject_nonterminal_question(prompt: str) -> None:
    if not prompt.endswith(_TERMINAL_QUESTION):
        raise ValueError("few-shot prompt must end with Allow Or Remove?")


FEW_SHOT_REMOVE_INSTRUCTIONS = build_few_shot_remove_instructions(
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT
)
