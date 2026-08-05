"""Part-2-local Pydantic schemas for free-response feature generation.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.schemas import BatchFeatureGeneration
    print(BatchFeatureGeneration.__name__)
    "
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

MAX_FEATURES_PER_BATCH = 8


class QaStatus(str, Enum):
    """QA gate outcome for one free-response batch."""

    USABLE = "usable"
    REJECTED_GARBAGE = "rejected_garbage"


class ExtractedReflectionFeature(BaseModel):
    """One thematic feature attributed to a participant reflection."""

    participant_id: str = Field(
        description="Source participant id for this feature."
    )
    feature_name: str = Field(
        description="Short snake_case feature name."
    )
    feature_value: str = Field(
        description="Human-readable value or short description."
    )
    category: str = Field(
        description=(
            "Open thematic category, e.g. pair_comparison_strategy, "
            "decision_criteria, affect_or_confidence, content_cues, "
            "process_meta, other."
        )
    )
    is_open_ended: bool = Field(
        description="True when the theme is not one of the guided categories."
    )
    evidence_span: str = Field(
        description="Short quoted substring from the reflection text."
    )
    rationale: str = Field(
        description="One sentence explaining why the feature applies."
    )


class BatchFeatureGeneration(BaseModel):
    """Structured LLM response for one free-response reflection batch."""

    batch_index: int = Field(description="Zero-based batch index within the run.")
    qa_status: QaStatus = Field(
        description="usable or rejected_garbage after the QA gate."
    )
    qa_notes: str = Field(
        description="Short reject reason when rejected; empty string when usable."
    )
    features: list[ExtractedReflectionFeature] = Field(
        default_factory=list,
        max_length=MAX_FEATURES_PER_BATCH,
        description=(
            "Up to 8 features across the batch; must be empty when "
            "qa_status is rejected_garbage."
        ),
    )
