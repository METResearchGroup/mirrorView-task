"""Run manifest for one Jev keep or remove process.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest"
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import (
    JevInferenceVariant,
    ZERO_SHOT_VARIANT,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import ModelRunManifestStatus

JEV_RUN_MANIFEST_SCHEMA_VERSION = ZERO_SHOT_VARIANT.run_manifest_schema_version


class JevRunManifest(BaseModel):
    """Frozen manifest for one Jev run folder, including the worker count.

    Manifests stored before prompt identity existed load with the zero-shot
    experiment name, prompt name, and digests.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    experiment_name: str = Field(default=ZERO_SHOT_VARIANT.experiment_name, min_length=1)
    prompt_name: str = Field(default=ZERO_SHOT_VARIANT.prompt_name, min_length=1)
    prompt_sha256: str = Field(default=ZERO_SHOT_VARIANT.prompt_sha256, min_length=1)
    instructions_sha256: str = Field(
        default=ZERO_SHOT_VARIANT.instructions_sha256,
        min_length=1,
    )
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


def reject_run_manifest_identity(
    manifest: JevRunManifest,
    variant: JevInferenceVariant,
    run_id: str,
    model_folder: str,
    model_id: str,
) -> None:
    """Reject a stored manifest whose identity differs from the active run.

    Parameters
    ----------
    manifest
        Manifest loaded from the run folder.
    variant
        Experiment configuration that owns this run.
    run_id
        Run identifier supplied by the caller.
    model_folder
        Expected Jev model folder.
    model_id
        Expected Jev model identifier.

    Raises
    ------
    ValueError
        When schema, experiment, prompt, run, or model identity differs.
    """
    expected = _manifest_identity_values(manifest, variant, run_id, model_folder, model_id)
    for field_name, actual, wanted in expected:
        if actual != wanted:
            raise ValueError(f"manifest {field_name} mismatch")


def _manifest_identity_values(
    manifest: JevRunManifest,
    variant: JevInferenceVariant,
    run_id: str,
    model_folder: str,
    model_id: str,
) -> tuple[tuple[str, str, str], ...]:
    return (
        ("schema_version", manifest.schema_version, variant.run_manifest_schema_version),
        ("experiment_name", manifest.experiment_name, variant.experiment_name),
        ("prompt_name", manifest.prompt_name, variant.prompt_name),
        ("prompt_sha256", manifest.prompt_sha256, variant.prompt_sha256),
        ("instructions_sha256", manifest.instructions_sha256, variant.instructions_sha256),
        ("run_id", manifest.run_id, run_id),
        ("model_folder", manifest.model_folder, model_folder),
        ("model_id", manifest.model_id, model_id),
    )
