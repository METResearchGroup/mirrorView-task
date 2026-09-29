"""Structured output models for candidate feature mining."""

from __future__ import annotations

from pydantic import BaseModel


class FeatureCategoryLists(BaseModel):
    extra: str = "forbid"  # placeholder for contract phase


class CandidateFeatures(BaseModel):
    extra: str = "forbid"


class CandidateFeatureRow(CandidateFeatures):
    source_record_id: str
    label_timestamp: str
