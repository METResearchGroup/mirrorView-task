"""Experiment-local structured response schemas for feature generation and theme synthesis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedFeature(BaseModel):
    """One high-confidence linguistic or content feature for a post."""

    name: str = Field(description="Short snake_case feature name.")
    value: str = Field(description="Human-readable value or short description.")
    category: str = Field(
        description="Feature category label, e.g. surface_lexical or open_ended."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence that the feature is present.",
    )
    evidence_span: str = Field(
        description="Short quoted substring from the original or mirror text."
    )
    rationale: str = Field(description="One sentence explaining why the feature applies.")


class PostFeatures(BaseModel):
    """Feature list for one post in a keep/remove batch."""

    message_id: str
    features: list[ExtractedFeature] = Field(
        description="High-confidence features extracted for this post."
    )


class BatchFeatureGeneration(BaseModel):
    """Structured LLM response for one mixed keep/remove batch."""

    batch_index: int = Field(description="Zero-based batch index within the run.")
    keep_group: list[PostFeatures] = Field(
        description="Feature extractions for keep-rated posts in the batch.",
    )
    remove_group: list[PostFeatures] = Field(
        description="Feature extractions for remove-rated posts in the batch.",
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
