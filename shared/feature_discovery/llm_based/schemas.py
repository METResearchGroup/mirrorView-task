"""Generic Pydantic schemas for LLM-based feature-discovery labeling.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from shared.feature_discovery.llm_based.schemas import ClusterLabelResult
    print(ClusterLabelResult.__name__)
    "
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClusterLabelResult(BaseModel):
    """Structured LLM response labeling one HDBSCAN cluster."""

    cluster_id: int
    cluster_label: str = Field(
        description="Short human-readable category name (≤8 words)."
    )
    definition: str = Field(
        description="One sentence defining the cluster for analysis."
    )
    salience_notes: str = Field(
        description=(
            "Optional brief note on why these features cohere; "
            "empty string if none."
        )
    )
