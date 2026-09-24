"""Shared fixtures for Step 7 analysis tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants


@pytest.fixture
def synthetic_feature_ids() -> list[str]:
    return ["cb_001", "cb_026", "cb_027"]


@pytest.fixture
def synthetic_test_post_ids() -> set[str]:
    return {"post_test_a", "post_test_b", "post_catalog"}


@pytest.fixture
def synthetic_label_matrix(
    tmp_path: Path,
    synthetic_feature_ids: list[str],
    synthetic_test_post_ids: set[str],
) -> Path:
    rows: list[dict[str, object]] = []
    discovery_id = "post_discovery"
    for post_id in synthetic_test_post_ids | {discovery_id}:
        split = constants.TEST_SPLIT if post_id in synthetic_test_post_ids else constants.DISCOVERY_SPLIT
        for surface in ("original", "mirror"):
            record: dict[str, object] = {
                "post_id": post_id,
                "text_surface": surface,
                "split": split,
                "modal_decision": "remove" if post_id.endswith("a") else "keep",
            }
            for index, feature_id in enumerate(synthetic_feature_ids):
                record[feature_id] = int(index % 2 == 0)
            rows.append(record)
    frame = pd.DataFrame(rows)
    path = tmp_path / "label_matrix.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture
def synthetic_cohort_frame(synthetic_test_post_ids: set[str]) -> pd.DataFrame:
    rows = []
    for post_id in synthetic_test_post_ids | {"post_discovery"}:
        rows.append(
            {
                "post_id": post_id,
                "in_part2_catalog": post_id == "post_catalog",
                "three_group_label": constants.GROUP_SPLIT,
                "sampled_stance": "left",
                "sample_toxicity_type": "low",
                "modal_decision": "remove" if post_id.endswith("a") else "keep",
                "split": constants.TEST_SPLIT if post_id in synthetic_test_post_ids else constants.DISCOVERY_SPLIT,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_part3_cohort(synthetic_cohort_frame: pd.DataFrame) -> pd.DataFrame:
    part3 = synthetic_cohort_frame.copy()
    part3["modal_decision"] = "keep"
    return part3
