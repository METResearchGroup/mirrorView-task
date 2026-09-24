"""Prompt templates for discovery, cluster labeling, and post labeling.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
        FEATURE_GENERATION_SYSTEM_PROMPT,
    )
    print(len(FEATURE_GENERATION_SYSTEM_PROMPT))
    "
"""

from __future__ import annotations

from typing import Any


def build_feature_generation_messages(
    batch: dict[str, Any],
    arm: str,
) -> list[dict[str, str]]:
    """Build chat messages for one discovery batch and text arm."""
    raise NotImplementedError


def build_cluster_label_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one HDBSCAN cluster labeling item."""
    raise NotImplementedError


def build_labeling_prompt(
    codebook: list[dict[str, Any]],
    text: str,
    text_surface: str,
) -> list[dict[str, str]]:
    """Build chat messages with a fixed codebook prefix and one post text."""
    raise NotImplementedError
