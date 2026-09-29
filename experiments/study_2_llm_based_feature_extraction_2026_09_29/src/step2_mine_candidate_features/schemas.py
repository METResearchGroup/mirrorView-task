"""Structured output models for candidate feature mining."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    FEATURE_CATEGORIES,
    FEATURE_SIDES,
)

_CATEGORY_DESCRIPTIONS = {
    "lexical": "Surface and lexical",
    "topic_subject": "Topic and subject matter",
    "semantic_content": "Semantic content",
    "pragmatics": "Pragmatics and communicative intent",
    "target": "Target and directionality",
    "structure": "Compositional and syntactic structure",
}


def _category_field(category: str) -> tuple[str, Field]:
    return (
        category,
        Field(description=_CATEGORY_DESCRIPTIONS[category]),
    )


class FeatureCategoryLists(BaseModel):
    """Feature phrases grouped by mining category."""

    model_config = ConfigDict(extra="forbid")

    lexical: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["lexical"])
    topic_subject: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["topic_subject"])
    semantic_content: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["semantic_content"])
    pragmatics: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["pragmatics"])
    target: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["target"])
    structure: list[str] = Field(description=_CATEGORY_DESCRIPTIONS["structure"])


class CandidateFeatures(BaseModel):
    """Candidate features for kept and removed post pairs."""

    model_config = ConfigDict(extra="forbid")

    features_from_kept_posts: FeatureCategoryLists
    features_from_removed_posts: FeatureCategoryLists


class CandidateFeatureRow(CandidateFeatures):
    """One batch's mined features with label metadata."""

    source_record_id: str
    label_timestamp: str


__all__ = [
    "FEATURE_CATEGORIES",
    "FEATURE_SIDES",
    "CandidateFeatureRow",
    "CandidateFeatures",
    "FeatureCategoryLists",
]
