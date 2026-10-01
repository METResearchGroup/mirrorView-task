"""Pydantic models for Study 2 zero-shot setup and inference."""

from __future__ import annotations

from pydantic import BaseModel


class ModelDefinition(BaseModel):
    """One Bedrock model entry in the confirmed registry."""

    display_name: str
    folder_name: str
    model_id: str


class Study2InputRecord(BaseModel):
    """One prepared Study 2 post pair for zero-shot inference."""

    post_id: str
    post_1_text: str
    post_2_text: str
    gold_is_remove: bool
    n_keep: int
    n_remove: int
    n_raters: int
    is_unanimous: bool


class RemovePrediction(BaseModel):
    """Model remove label and probability for one pair."""

    is_remove: bool
    p_remove: float


class InputManifest(BaseModel):
    """Immutable manifest describing the prepared input JSONL."""

    schema_version: str
    source_dataset_names: tuple[str, str, str]
    records_s3_key: str
    records_sha256: str
    total_record_count: int
    unanimous_record_count: int
    split_record_count: int
    first_post_id: str
    last_post_id: str
