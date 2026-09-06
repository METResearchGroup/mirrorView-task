"""Contracts for the resumable feature-generation batch engine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from data_platform.utils.feature_labels import FeatureLabelQuery
from data_platform.utils.storage import StorageManager

EngineType = Literal["langchain", "thread_pool", "openai"]


@dataclass(frozen=True)
class LabelTask:
    uri: str
    text: str


@dataclass(frozen=True)
class FeatureRunConfig:
    batch_size: int = 64
    max_concurrency: int = 80
    max_label_retries: int = 3


@dataclass
class FeatureStatus:
    status: Literal["pending", "in_progress", "completed"] = "pending"
    labeled: int = 0
    failed_batches: int = 0
    model_id: str | None = None
    prompt_hash: str | None = None


@dataclass
class FeatureRunMetadata:
    dataset_id: str
    source_preprocessed_runs: list[str]
    sync_status: Literal["pending", "in_progress", "completed"] = "pending"
    features: dict[str, FeatureStatus] = field(default_factory=dict)
    config: FeatureRunConfig = field(default_factory=FeatureRunConfig)
    migrated_from: str | None = None
    migrated_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to the features/{timestamp}/metadata.json document shape."""
        return {
            "dataset_id": self.dataset_id,
            "source_preprocessed_runs": self.source_preprocessed_runs,
            "sync_status": self.sync_status,
            "features": {
                name: {
                    "status": status.status,
                    "labeled": status.labeled,
                    "failed_batches": status.failed_batches,
                    "model_id": status.model_id,
                    "prompt_hash": status.prompt_hash,
                }
                for name, status in self.features.items()
            },
            "config": {
                "batch_size": self.config.batch_size,
                "max_concurrency": self.config.max_concurrency,
                "max_label_retries": self.config.max_label_retries,
            },
            **(
                {"migrated_from": self.migrated_from, "migrated_at": self.migrated_at}
                if self.migrated_from
                else {}
            ),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureRunMetadata:
        """Load metadata from a parsed features/{timestamp}/metadata.json dict."""
        config_raw = data.get("config", {})
        config = FeatureRunConfig(
            batch_size=config_raw.get("batch_size", 64),
            max_concurrency=config_raw.get("max_concurrency", 80),
            max_label_retries=config_raw.get("max_label_retries", 3),
        )
        features: dict[str, FeatureStatus] = {}
        for name, feat in data.get("features", {}).items():
            features[name] = FeatureStatus(
                status=feat.get("status", "pending"),
                labeled=feat.get("labeled", 0),
                failed_batches=feat.get("failed_batches", 0),
                model_id=feat.get("model_id"),
                prompt_hash=feat.get("prompt_hash"),
            )
        legacy_single = data.get("source_preprocessed_run")
        source_preprocessed_runs = data.get(
            "source_preprocessed_runs",
            [legacy_single] if legacy_single else [],
        )
        return cls(
            dataset_id=data["dataset_id"],
            source_preprocessed_runs=source_preprocessed_runs,
            sync_status=data.get("sync_status", "pending"),
            features=features,
            config=config,
            migrated_from=data.get("migrated_from"),
            migrated_at=data.get("migrated_at"),
            updated_at=data.get("updated_at"),
        )


FeatureFn = Callable[[str, str], BaseModel]


@dataclass(frozen=True)
class FeatureSpec:
    """One named feature in the feature registry.

    A LangChain or OpenAI feature sets ``system_prompt`` and ``llm_output_schema``,
    and it leaves ``generate_fn`` unset. The LangChain engine labels a batch of
    rows through a structured-output chain. The OpenAI engine labels the same
    rows through the OpenAI Batch API. A thread-pool feature must set
    ``generate_fn``, because that engine calls the function on each row.
    """

    name: str
    model: type[BaseModel]
    engine_type: EngineType
    generate_fn: FeatureFn | None = None
    system_prompt: str | None = None
    llm_output_schema: type[BaseModel] | None = None


@dataclass(frozen=True)
class FeatureGenerationConfig:
    platform: str
    id_column: str
    text_column: str
    feature_registry: dict[str, FeatureSpec]
    input_storage: StorageManager
    features_dir: Path
    feature_label_query: FeatureLabelQuery
    run_config: FeatureRunConfig


@dataclass
class BatchRunStats:
    labeled: int = 0
    failed_batches: int = 0


@dataclass(frozen=True)
class CampaignRunConfig:
    """Identity of one S3 backed labeling campaign run for one platform dataset."""

    campaign_id: str
    dataset_id: str
    preprocessed_run: str
    platform: str
    batch_size: int


class LabelRowMetadataModel(BaseModel):
    """The six identity and audit columns every campaign label row carries."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    batch_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    attempt_count: int = Field(ge=1, le=4)
    label_timestamp: str = Field(min_length=1)
