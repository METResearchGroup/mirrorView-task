"""LLM response schemas for Phase 2 Part 3 feature generation.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import (
        BatchFeatureGeneration,
    )
    print(BatchFeatureGeneration.model_fields.keys())
    "
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    MAX_KEEP_FEATURES_PER_BATCH,
    MAX_REMOVE_FEATURES_PER_BATCH,
)

MAX_SINGLE_CLASS_FEATURES_PER_BATCH = MAX_KEEP_FEATURES_PER_BATCH


class FeatureCategory(str, Enum):
    """Fixed feature categories from the July-31 extraction lineage."""

    SURFACE_LEXICAL = "surface_lexical"
    TOPIC_SUBJECT = "topic_subject"
    SEMANTIC_CONTENT = "semantic_content"
    PRAGMATICS_INTENT = "pragmatics_intent"
    TARGET_DIRECTIONALITY = "target_directionality"
    COMPOSITIONAL_SYNTAX = "compositional_syntax"
    OPEN_ENDED = "open_ended"


class ExtractedFeature(BaseModel):
    """One linguistic or content feature attributed to a post in the batch."""

    message_id: str = Field(description="Post this feature was extracted from.")
    feature_name: str = Field(
        description="Short snake_case feature name, e.g. 'second_amendment_framing'."
    )
    feature_value: str = Field(description="Human-readable value or short description.")
    category: FeatureCategory
    is_open_ended: bool = Field(
        description="True if not from the fixed category checklist."
    )
    evidence_span: str = Field(
        description="Short quoted substring from the original or mirror text."
    )
    rationale: str = Field(description="One sentence explaining why the feature applies.")


class BatchFeatureGeneration(BaseModel):
    """Structured LLM response for one mixed keep/remove batch."""

    batch_index: int = Field(description="Zero-based batch index within the run.")
    keep_features: list[ExtractedFeature] = Field(
        max_length=MAX_KEEP_FEATURES_PER_BATCH,
        description="Up to 8 features total across all keep-rated posts in the batch.",
    )
    remove_features: list[ExtractedFeature] = Field(
        max_length=MAX_REMOVE_FEATURES_PER_BATCH,
        description="Up to 8 features total across all remove-rated posts in the batch.",
    )


class SingleClassBatchFeatureGeneration(BaseModel):
    """Structured LLM response for one single-class keep or remove batch."""

    batch_index: int = Field(description="Zero-based batch index within the run.")
    features: list[ExtractedFeature] = Field(
        max_length=MAX_SINGLE_CLASS_FEATURES_PER_BATCH,
        description="Up to 8 features total across all posts in the batch.",
    )


class ClusterLabelResult(BaseModel):
    """Structured LLM response labeling one HDBSCAN cluster."""

    cluster_id: int
    cluster_label: str = Field(
        description="Short human-readable category name (8 words or fewer)."
    )
    definition: str = Field(
        description="One sentence defining the cluster for moderation analysis."
    )
    salience_notes: str = Field(
        description="Optional brief note on why these features cohere; empty string if none."
    )


class PostLabelResult(BaseModel):
    """Structured LLM response for one post text surface labeling call."""

    labels: dict[str, bool] = Field(
        description="Present (true) or absent (false) per codebook feature_id (cb_*)."
    )
