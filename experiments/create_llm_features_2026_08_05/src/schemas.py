"""Experiment-local Pydantic schemas for feature generation and cluster labeling."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

MAX_FEATURES_PER_BATCH = 8


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


class SingleClassBatchFeatureGeneration(BaseModel):
    """Structured LLM response for one single-class keep or remove batch."""

    batch_index: int = Field(description="Zero-based batch index within the run.")
    features: list[ExtractedFeature] = Field(
        max_length=MAX_FEATURES_PER_BATCH,
        description="Up to 8 features total across all posts in the batch.",
    )


class ClusterLabelResult(BaseModel):
    """Structured LLM response labeling one HDBSCAN cluster."""

    cluster_id: int
    cluster_label: str = Field(
        description="Short human-readable category name (≤8 words)."
    )
    definition: str = Field(
        description="One sentence defining the cluster for moderation analysis."
    )
    salience_notes: str = Field(
        description="Optional brief note on why these features cohere; empty string if none."
    )
