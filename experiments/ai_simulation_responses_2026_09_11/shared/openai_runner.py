"""OpenAI Batch runner for remove-index labeling."""

from __future__ import annotations

from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.models import FeatureSpec, LabelTask


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through the OpenAI Batch API."""
    raise NotImplementedError
