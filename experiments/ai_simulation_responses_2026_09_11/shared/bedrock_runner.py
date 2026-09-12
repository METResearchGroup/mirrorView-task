"""Bedrock Converse runner for remove-index labeling."""

from __future__ import annotations

from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.models import FeatureSpec, LabelTask


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
    model_id: str,
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through Bedrock Converse without OpenAI fallback."""
    raise NotImplementedError
