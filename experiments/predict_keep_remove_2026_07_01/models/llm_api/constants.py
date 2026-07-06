"""Shared constants for LLM prompting variants.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

from typing import Literal

PromptType = Literal["one_shot", "few_shot"]
InputMode = Literal["original", "original_plus_mirror"]
ModelSize = Literal["small", "large"]

MODEL_ID_BY_SIZE: dict[ModelSize, str] = {
    "small": "gpt-5.4-nano",
    "large": "gpt-5.5",
}

PROMPT_TYPE_TO_LABEL: dict[PromptType, str] = {
    "one_shot": "one-shot",
    "few_shot": "few-shot",
}

INPUT_MODE_TO_ABLATION_LABEL: dict[InputMode, str] = {
    "original": "original",
    "original_plus_mirror": "original plus mirror",
}

