"""Pydantic models for Study 2 zero-shot setup and inference."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

FIVE_RATER_COUNT = 5
PROBABILITY_THRESHOLD = 0.5
UNANIMOUS_REMOVE_VOTES = frozenset({0, FIVE_RATER_COUNT})


class ModelDefinition(BaseModel):
    """One Bedrock model entry in the confirmed registry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display_name: str = Field(min_length=1)
    folder_name: str = Field(min_length=1)
    model_id: str = Field(min_length=1)


class Study2InputRecord(BaseModel):
    """One prepared Study 2 post pair for zero-shot inference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    post_id: str
    post_1_text: str
    post_2_text: str
    gold_is_remove: bool
    n_keep: int
    n_remove: int
    n_raters: int
    is_unanimous: bool

    @model_validator(mode="after")
    def _check_invariants(self) -> Study2InputRecord:
        _validate_nonempty_text(self.post_id, "post_id")
        _validate_nonempty_text(self.post_1_text, "post_1_text")
        _validate_nonempty_text(self.post_2_text, "post_2_text")
        _validate_rater_counts(self.n_raters, self.n_keep, self.n_remove)
        if self.gold_is_remove != (self.n_remove > self.n_keep):
            raise ValueError("gold_is_remove must equal n_remove > n_keep")
        if self.is_unanimous != (self.n_remove in UNANIMOUS_REMOVE_VOTES):
            raise ValueError("is_unanimous must match unanimous remove votes")
        return self


class RemovePrediction(BaseModel):
    """Model remove label and probability for one pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_remove: bool
    p_remove: float

    @model_validator(mode="after")
    def _check_threshold(self) -> RemovePrediction:
        if self.p_remove < 0.0 or self.p_remove > 1.0:
            raise ValueError("p_remove must be between 0 and 1 inclusive")
        expected = self.p_remove >= PROBABILITY_THRESHOLD
        if self.is_remove != expected:
            raise ValueError("is_remove must match the 0.5 probability threshold")
        return self


class InputManifest(BaseModel):
    """Immutable manifest describing the prepared input JSONL."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    source_dataset_names: tuple[str, str, str]
    records_s3_key: str = Field(min_length=1)
    records_sha256: str = Field(min_length=1)
    total_record_count: int = Field(ge=0)
    unanimous_record_count: int = Field(ge=0)
    split_record_count: int = Field(ge=0)
    first_post_id: str = Field(min_length=1)
    last_post_id: str = Field(min_length=1)


def _validate_nonempty_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must be nonempty")


def _validate_rater_counts(n_raters: int, n_keep: int, n_remove: int) -> None:
    if n_raters != FIVE_RATER_COUNT:
        raise ValueError("n_raters must equal five")
    if n_keep + n_remove != FIVE_RATER_COUNT:
        raise ValueError("n_keep and n_remove must sum to five")
