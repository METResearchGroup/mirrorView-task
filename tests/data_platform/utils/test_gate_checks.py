from __future__ import annotations

import pytest

from data_platform.generate_features.models import FeatureRunMetadata
from data_platform.utils.gate_checks import require_features_complete
from tests.data_platform.constants import VALID_DATASET_ID


def test_require_features_complete_passes_when_sync_completed() -> None:
    meta = FeatureRunMetadata(
        dataset_id=VALID_DATASET_ID,
        source_preprocessed_runs=[],
        sync_status="completed",
    )
    require_features_complete(meta, VALID_DATASET_ID)


def test_require_features_complete_raises_when_not_completed() -> None:
    meta = FeatureRunMetadata(
        dataset_id=VALID_DATASET_ID,
        source_preprocessed_runs=[],
        sync_status="in_progress",
    )
    with pytest.raises(RuntimeError, match="not complete locally"):
        require_features_complete(meta, VALID_DATASET_ID)
