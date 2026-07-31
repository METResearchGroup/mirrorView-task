"""Experiment-local schemas for feature generation and theme synthesis."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    """Base model compatible with OpenAI structured-output JSON Schema rules.

    OpenAI requires every key in ``properties`` to also appear in ``required``.
    Fields therefore have no defaults; callers pass empty lists/zeros explicitly.
    """

    model_config = ConfigDict(extra="forbid")


class ExtractedFeature(_StrictModel):
    """One feature assertion for one post."""

    feature_name: str = Field(
        description="Short snake_case feature name, e.g. 'second_amendment_framing'"
    )
    feature_value: str = Field(description="Human-readable value or short description")
    category: str = Field(
        description=(
            "One of: surface_lexical, topic_subject, semantic_content, "
            "pragmatics_intent, target_directionality, compositional_syntax, open_ended"
        )
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Model confidence this feature is present"
    )
    evidence_span: str = Field(
        description="Short quoted substring from original or mirror supporting the feature"
    )
    rationale: str = Field(description="One sentence explaining why the feature applies")


class PostFeatures(_StrictModel):
    """Features for a single post."""

    message_id: str
    decision: str = Field(description="'keep' or 'remove' human modal label")
    features: list[ExtractedFeature] = Field(
        description=(
            "All confident features for this post; use an empty list if none qualify"
        )
    )


class BatchFeatureGeneration(_StrictModel):
    """Structured LLM response for one mixed keep/remove batch."""

    batch_id: int
    keep_posts: list[PostFeatures]
    remove_posts: list[PostFeatures]


class LabelMix(_StrictModel):
    """Counts of example posts per human keep/remove label in a theme."""

    keep: int = Field(description="Number of keep-labeled example posts")
    remove: int = Field(description="Number of remove-labeled example posts")


class Theme(_StrictModel):
    """One thematic commonality across extracted features."""

    theme_id: int
    theme_label: str
    defining_features: list[str]
    example_message_ids: list[str] = Field(
        description="Up to 10 example message ids; empty list if none"
    )
    label_mix: LabelMix
    interpretation: str


class ThemeSynthesisResult(_StrictModel):
    """Structured LLM response for thematic commonality synthesis."""

    themes: list[Theme]
    cross_cutting_themes: list[str] = Field(
        description="Themes that cut across multiple theme groups; empty list if none"
    )
