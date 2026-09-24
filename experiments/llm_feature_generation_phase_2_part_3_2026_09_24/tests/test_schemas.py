"""Tests for LLM response schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import (
    BatchFeatureGeneration,
    ExtractedFeature,
    FeatureCategory,
    SingleClassBatchFeatureGeneration,
)


def _feature(message_id: str, name: str) -> ExtractedFeature:
    return ExtractedFeature(
        message_id=message_id,
        feature_name=name,
        feature_value="value",
        category=FeatureCategory.SURFACE_LEXICAL,
        is_open_ended=False,
        evidence_span="quoted text",
        rationale="because",
    )


def test_batch_feature_generation_rejects_ninth_keep() -> None:
    """BatchFeatureGeneration rejects more than eight keep features."""
    keep_features = [_feature("p1", f"feature_{index}") for index in range(9)]
    with pytest.raises(ValidationError):
        BatchFeatureGeneration(batch_index=0, keep_features=keep_features, remove_features=[])


def test_single_class_max_eight() -> None:
    """SingleClassBatchFeatureGeneration rejects more than eight features."""
    features = [_feature("p1", f"feature_{index}") for index in range(9)]
    with pytest.raises(ValidationError):
        SingleClassBatchFeatureGeneration(batch_index=0, features=features)


def test_extracted_feature_requires_evidence_span() -> None:
    """ExtractedFeature requires evidence_span."""
    with pytest.raises(ValidationError):
        ExtractedFeature(
            message_id="p1",
            feature_name="name",
            feature_value="value",
            category=FeatureCategory.SURFACE_LEXICAL,
            is_open_ended=False,
            rationale="because",
        )
