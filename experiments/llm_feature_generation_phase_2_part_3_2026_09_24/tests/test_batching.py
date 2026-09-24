"""Tests for discovery batch formation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching import (
    form_mixed_batches,
    form_mixed_topup_batches,
    form_single_class_batches,
    load_discovery_cohort,
)


def _sample_cohort() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(30):
        rows.append(
            {
                "post_id": f"keep_{index}",
                "original_text": f"keep original {index}",
                "mirror_text": f"keep mirror {index}",
                "modal_decision": constants.DECISION_KEEP,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    for index in range(30):
        rows.append(
            {
                "post_id": f"remove_{index}",
                "original_text": f"remove original {index}",
                "mirror_text": f"remove mirror {index}",
                "modal_decision": constants.DECISION_REMOVE,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    return pd.DataFrame(rows)


def _large_cohort() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(600):
        rows.append(
            {
                "post_id": f"keep_{index}",
                "original_text": f"keep original {index}",
                "mirror_text": f"keep mirror {index}",
                "modal_decision": constants.DECISION_KEEP,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    for index in range(600):
        rows.append(
            {
                "post_id": f"remove_{index}",
                "original_text": f"remove original {index}",
                "mirror_text": f"remove mirror {index}",
                "modal_decision": constants.DECISION_REMOVE,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    return pd.DataFrame(rows)


def test_form_mixed_batches_counts() -> None:
    """Mixed batching returns three full batches without duplicate message ids."""
    cohort = _sample_cohort()
    batches = form_mixed_batches(cohort, keep_per_batch=10, remove_per_batch=10)
    assert len(batches) == 3
    seen: set[str] = set()
    for batch in batches:
        assert len(batch["keep_posts"]) == 10
        assert len(batch["remove_posts"]) == 10
        for message_id in batch["message_ids"]:
            assert message_id not in seen
            seen.add(message_id)


def test_form_mixed_batches_zero_when_insufficient() -> None:
    """Mixed batching raises when keep rows cannot fill one batch."""
    rows = [
        {
            "post_id": f"keep_{index}",
            "original_text": "text",
            "mirror_text": "mirror",
            "modal_decision": constants.DECISION_KEEP,
            "split": constants.DISCOVERY_SPLIT,
        }
        for index in range(5)
    ] + [
        {
            "post_id": f"remove_{index}",
            "original_text": "text",
            "mirror_text": "mirror",
            "modal_decision": constants.DECISION_REMOVE,
            "split": constants.DISCOVERY_SPLIT,
        }
        for index in range(20)
    ]
    with pytest.raises(ValueError):
        form_mixed_batches(pd.DataFrame(rows))


def test_form_single_class_batch_count() -> None:
    """Single-class batching returns 50 keep and 50 remove batches of 10 posts."""
    cohort = _large_cohort()
    batches = form_single_class_batches(
        cohort,
        keep_sample_size=500,
        remove_sample_size=500,
        posts_per_batch=10,
        seed=42,
    )
    keep_batches = [batch for batch in batches if batch["label_class"] == constants.DECISION_KEEP]
    remove_batches = [
        batch for batch in batches if batch["label_class"] == constants.DECISION_REMOVE
    ]
    assert len(keep_batches) == 50
    assert len(remove_batches) == 50
    for batch in batches:
        assert len(batch["posts"]) == 10


def test_form_mixed_topup_batches_excludes_covered_posts(tmp_path: Path) -> None:
    """Top-up batches only include union-new discovery posts not in the mixed run."""
    rows: list[dict[str, object]] = []
    for index in range(15):
        rows.append(
            {
                "post_id": f"new_keep_{index}",
                "original_text": "text",
                "mirror_text": "mirror",
                "modal_decision": constants.DECISION_KEEP,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    for index in range(15):
        rows.append(
            {
                "post_id": f"new_remove_{index}",
                "original_text": "text",
                "mirror_text": "mirror",
                "modal_decision": constants.DECISION_REMOVE,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    rows.append(
        {
            "post_id": "legacy_keep_0",
            "original_text": "text",
            "mirror_text": "mirror",
            "modal_decision": constants.DECISION_KEEP,
            "split": constants.DISCOVERY_SPLIT,
        }
    )
    cohort = pd.DataFrame(rows)
    new_ids = frozenset(
        {f"new_keep_{index}" for index in range(15)}
        | {f"new_remove_{index}" for index in range(15)}
    )
    covered = frozenset({"new_keep_0", "new_remove_0"})
    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching.union_new_discovery_post_ids",
        return_value=new_ids,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching.covered_mixed_discovery_post_ids",
        return_value=covered,
    ):
        batches = form_mixed_topup_batches(cohort, "original_only", keep_per_batch=5, remove_per_batch=5)
    assert len(batches) == 2
    batched_ids: set[str] = set()
    for batch in batches:
        batched_ids.update(batch["message_ids"])
    assert "legacy_keep_0" not in batched_ids
    assert "new_keep_0" not in batched_ids
    assert "new_remove_0" not in batched_ids


def test_discovery_filter() -> None:
    """load_discovery_cohort keeps only discovery-split rows."""
    cohort = pd.concat(
        [
            _sample_cohort(),
            pd.DataFrame(
                [
                    {
                        "post_id": "test_only",
                        "original_text": "text",
                        "mirror_text": "mirror",
                        "modal_decision": constants.DECISION_KEEP,
                        "split": constants.TEST_SPLIT,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching._load_cohort_frame",
        return_value=cohort,
    ):
        result = load_discovery_cohort("original_only")
    assert (result["split"] == constants.DISCOVERY_SPLIT).all()
    assert "test_only" not in set(result["post_id"])
