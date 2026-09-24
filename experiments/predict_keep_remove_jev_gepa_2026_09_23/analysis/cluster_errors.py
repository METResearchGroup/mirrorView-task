"""Cluster test-set false positives and false negatives for A1 and B1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_SEED = 20260924
PREDICTION_THRESHOLD = 0.5
KMEANS_CLUSTER_COUNTS = (5, 10)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
COHORT_PATH = EXPERIMENT_ROOT / "data" / "cohort_a_splits.parquet"
LABELS_PATHS: dict[str, Path] = {
    "A1": EXPERIMENT_ROOT
    / "jev_baseline"
    / "outputs"
    / "A1_pair_study_prompt"
    / "labels.parquet",
    "B1": EXPERIMENT_ROOT
    / "jev_gepa"
    / "outputs"
    / "B1_gepa_pair"
    / "test_eval"
    / "labels.parquet",
}


@dataclass(frozen=True)
class ErrorRecord:
    post_id: str
    model_id: str
    error_type: str
    text_role: str
    text: str
    sampled_stance: str
    sample_toxicity_type: str
    p_remove: float
    remove_share: float


def extract_errors(labels_path: Path, model_id: str) -> list[ErrorRecord]:
    """Return FN and FP rows for test split; one ErrorRecord per (post, text_role)."""
    raise NotImplementedError


def precompute_embeddings(
    texts: list[str],
    *,
    model_name: str = EMBEDDING_MODEL,
    seed: int = EMBEDDING_SEED,
    cache_path: Path,
) -> np.ndarray:
    """Write embeddings to cache_path (npy). Reuse cache when present and hash matches."""
    raise NotImplementedError


def kmeans_baseline(
    embeddings: np.ndarray,
    *,
    n_clusters: int,
    seed: int = EMBEDDING_SEED,
) -> np.ndarray:
    """Return cluster labels."""
    raise NotImplementedError


def run_bertopic(
    texts: list[str],
    embeddings: np.ndarray,
    *,
    seed: int = EMBEDDING_SEED,
) -> pd.DataFrame:
    """Return topic table with topic id, representative terms, and post_id mapping."""
    raise NotImplementedError


def classify_error_kind(record: ErrorRecord) -> str:
    """Return grouping_error or label_error."""
    raise NotImplementedError


def spot_check_table(cluster_df: pd.DataFrame, n_per_topic: int = 3) -> pd.DataFrame:
    """Sample post ids and texts for manual review."""
    raise NotImplementedError


def run_cluster_analysis(*, output_dir: Path) -> dict[str, Any]:
    """Extract, embed, cluster, and write A1/B1 error outputs."""
    raise NotImplementedError
