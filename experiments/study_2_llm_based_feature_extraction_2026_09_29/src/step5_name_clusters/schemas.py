"""Structured output models for cluster names."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ClusterName(BaseModel):
    """Name and one-sentence definition for one cluster."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the cluster, at most eight words.")
    definition: str = Field(description="One sentence that defines the cluster.")


class ClusterNameRow(ClusterName):
    """One cluster name with label metadata."""

    source_record_id: str
    label_timestamp: str
