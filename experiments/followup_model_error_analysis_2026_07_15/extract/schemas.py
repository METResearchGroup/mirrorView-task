"""Pydantic schemas for unified multi-category LLM feature extraction."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FeatureCategory(str, Enum):
    SURFACE_LEXICAL = "surface_lexical"
    TOPIC_SUBJECT = "topic_subject"
    SEMANTIC_CONTENT = "semantic_content"
    PRAGMATICS_INTENT = "pragmatics_intent"
    TARGET_DIRECTIONALITY = "target_directionality"
    COMPOSITIONAL_SYNTAX = "compositional_syntax"
    OPEN_ENDED = "open_ended"


class ExtractedFeature(BaseModel):
    """One feature assertion for one post."""

    feature_name: str = Field(
        description="Short snake_case feature name, e.g. 'second_amendment_framing'"
    )
    feature_value: str = Field(description="Human-readable value or short description")
    category: FeatureCategory
    is_open_ended: bool = Field(description="True if not from the fixed category checklist")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Model confidence this feature is present"
    )
    evidence_span: str = Field(
        description="Short quoted substring from original or mirror supporting the feature"
    )
    rationale: str = Field(description="One sentence explaining why the feature applies")


class PostFeatureExtraction(BaseModel):
    """Structured LLM response for one post — all categories in a single pass."""

    post_id: str
    features: list[ExtractedFeature] = Field(
        default_factory=list,
        description=(
            "All confident features across all six fixed categories "
            "plus any open-ended features"
        ),
    )


class BatchFeatureExtraction(BaseModel):
    """Structured LLM response for a chunk of posts (one API call, all categories)."""

    bucket: Literal["tp", "tn", "fp", "fn"]
    chunk_idx: int
    posts: list[PostFeatureExtraction]


class BucketMix(BaseModel):
    """Counts of posts per confusion bucket in a cluster."""

    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0


class FeatureCluster(BaseModel):
    cluster_id: int
    cluster_label: str
    defining_features: list[str]
    example_post_ids: list[str] = Field(default_factory=list)
    bucket_mix: BucketMix
    interpretation: str


class ClusteringResult(BaseModel):
    shard_id: str
    clusters: list[FeatureCluster]
    cross_cutting_themes: list[str]
    fp_specific_themes: list[str]


CONFIDENCE_THRESHOLD = 0.85


def keep_feature(f: ExtractedFeature) -> bool:
    return f.confidence >= CONFIDENCE_THRESHOLD
