"""Experiment-local structured response schemas for feature generation and theme synthesis."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

MAX_KEEP_FEATURES_PER_BATCH = 8
MAX_REMOVE_FEATURES_PER_BATCH = 8


class FeatureCategory(str, Enum):
    """Fixed feature categories from the 2026-07-15 extraction prompt."""

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


class Theme(BaseModel):
    """A recurring thematic pattern across extracted features."""

    id: int
    label: str
    defining_features: list[str]
    example_message_ids: list[str] = Field(
        description="Example message ids illustrating the theme."
    )
    keep_count: int = Field(
        ge=0,
        description="Number of keep-rated posts associated with this theme.",
    )
    remove_count: int = Field(
        ge=0,
        description="Number of remove-rated posts associated with this theme.",
    )
    interpretation: str = Field(
        description="Short interpretation of what the theme means for moderation."
    )


class ThemeSynthesisResult(BaseModel):
    """Structured LLM response for thematic commonality synthesis."""

    themes: list[Theme] = Field(description="Recurring thematic patterns in the corpus.")
    cross_cutting_themes: list[str] = Field(
        description="Themes that span multiple clusters or both keep and remove groups.",
    )
