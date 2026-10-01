"""Run manifest for one Jev keep or remove process."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelRunManifestStatus

JEV_RUN_MANIFEST_SCHEMA_VERSION = "study2-zero-shot-jev-run-v1"


class JevRunManifest(BaseModel):
    """Immutable manifest for one Jev folder. Replaces max tokens with worker count."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    model_display_name: str = Field(min_length=1)
    model_folder: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prepared_input_records_key: str = Field(min_length=1)
    prepared_input_records_sha256: str = Field(min_length=1)
    configured_batch_size: int = Field(ge=1)
    max_workers: int = Field(ge=1)
    configured_limit: int | None = Field(default=None)
    requested_record_count: int = Field(ge=0)
    completed_prediction_count: int = Field(ge=0)
    unresolved_failure_count: int = Field(ge=0)
    prediction_object_keys: tuple[str, ...]
    failure_object_keys: tuple[str, ...]
    status: ModelRunManifestStatus
