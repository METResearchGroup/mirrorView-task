"""Jev state text and per-feature instructions."""

from __future__ import annotations

import json

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    JEV_STATE_KEY,
)

NOUL_INSTRUCTION_TEMPLATE = """You are labeling one social-media post pair against one approved feature. The pair is in `pair`. Each pair is an original post and a mirror of that post. The two texts are labeled text 1 and text 2. Those labels do not say which text is the original.

Return true when the feature clearly applies to the post text, otherwise return false. Use only the provided feature definition.

Feature:
{feature_json}
"""


def render_pair_state(original_text: str, mirror_text: str) -> dict[str, str]:
    """Build the Jev state for one post pair.

    Parameters
    ----------
    original_text
        Stimulus original post. The prompt calls this text 1.
    mirror_text
        Stimulus mirror post. The prompt calls this text 2.

    Returns
    -------
    dict[str, str]
        One key, ``pair``, whose value is the two texts.
    """
    pair = f"Text 1: {original_text}\n\nText 2: {mirror_text}"
    return {JEV_STATE_KEY: pair}


def render_feature_instruction(detail: dict[str, str]) -> str:
    """Build one Noul instruction from a feature name and description.

    Parameters
    ----------
    detail
        Mapping with ``name`` and ``description``.

    Returns
    -------
    str
        Instruction text for one feature question.
    """
    feature_json = json.dumps(
        {"name": detail["name"], "description": detail["description"]},
        ensure_ascii=False,
    )
    return NOUL_INSTRUCTION_TEMPLATE.replace("{feature_json}", feature_json)
