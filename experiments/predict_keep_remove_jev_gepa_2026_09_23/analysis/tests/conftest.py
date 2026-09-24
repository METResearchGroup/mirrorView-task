"""Shared fixtures for analysis unit tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.cluster_errors import (
    ErrorRecord,
)


@pytest.fixture
def tiny_labels_parquet(tmp_path: Path) -> Path:
    """Synthetic labels with one FN and one FP on the test split."""
    frame = pd.DataFrame(
        {
            "post_id": ["post-fn", "post-fp"],
            "split": ["test", "test"],
            "keep_remove_label": [1, 0],
            "predicted_label": [0, 1],
            "p_remove": [0.2, 0.85],
            "sampled_stance": ["left", "right"],
            "sample_toxicity_type": ["sample_high_toxicity", "sample_low_toxicity"],
            "remove_share": [0.75, 0.2],
            "is_unanimous": [False, True],
            "n_raters": [5, 4],
        }
    )
    path = tmp_path / "labels.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture
def tiny_cohort_parquet(tmp_path: Path) -> Path:
    """Synthetic cohort texts keyed by post_id."""
    frame = pd.DataFrame(
        {
            "post_id": ["post-fn", "post-fp"],
            "original_text": ["original fn text", "original fp text"],
            "mirror_text": ["mirror fn text", "mirror fp text"],
            "split": ["test", "test"],
        }
    )
    path = tmp_path / "cohort.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture
def mirror_fp_label_error_record() -> ErrorRecord:
    """FP on mirror with high p_remove and gold keep."""
    return ErrorRecord(
        post_id="post-fp",
        model_id="A1",
        error_type="false_positive",
        text_role="mirror",
        text="mirror fp text",
        sampled_stance="right",
        sample_toxicity_type="sample_low_toxicity",
        p_remove=0.85,
        remove_share=0.2,
    )
