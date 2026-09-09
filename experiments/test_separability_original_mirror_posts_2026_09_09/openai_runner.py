"""OpenAI Batch API runner for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.engines.openai_engine import build_openai_engine
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    ATTEMPT_COUNT,
)


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through the OpenAI Batch API.

    Parameters
    ----------
    spec
        Separability feature definition.
    tasks
        Pending label tasks for one chunk.

    Returns
    -------
    tuple[list[dict], list[RecordLabelFailure]]
        Successful rows and per-record failures.
    """
    if not tasks:
        return [], []
    engine = build_openai_engine(spec, FeatureRunConfig())
    try:
        rows = engine.batch_label_records(tasks)
    except Exception as error:
        return [], _failures_for_tasks(tasks, str(error))
    return rows, []


def _failures_for_tasks(
    tasks: list[LabelTask], error: str
) -> list[RecordLabelFailure]:
    return [
        RecordLabelFailure(
            source_record_id=task.uri,
            error=error,
            attempts=ATTEMPT_COUNT,
        )
        for task in tasks
    ]
