"""OpenAI Batch API runner for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.models import FeatureSpec, LabelTask


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through the OpenAI Batch API."""
    raise NotImplementedError
