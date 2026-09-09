"""Bedrock Converse runner for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.engines.bedrock_campaign import (
    BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
)
from data_platform.generate_features.engines.bedrock_engine import (
    create_bedrock_runtime_client,
    label_tasks_collecting_failures,
)
from data_platform.generate_features.models import FeatureSpec, LabelTask
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    BEDROCK_LABEL_MAX_TOKENS,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO
from lib.timestamp_utils import get_current_timestamp


def label_tasks(
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Label tasks through Bedrock Converse without OpenAI fallback.

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
    outcome = label_tasks_collecting_failures(
        create_bedrock_runtime_client(),
        DEFAULT_BEDROCK_NOVA_MICRO,
        spec,
        tasks,
        BEDROCK_CAMPAIGN_MAX_CONCURRENCY,
        get_current_timestamp(),
        max_tokens=BEDROCK_LABEL_MAX_TOKENS,
    )
    failures = [*outcome.content_filter_failures, *outcome.other_failures]
    return outcome.rows, failures
