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


def _load_cohort_texts() -> pd.DataFrame:
    if not COHORT_PATH.is_file():
        from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import (
            download_if_missing,
        )

        download_if_missing(
            COHORT_PATH,
            "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet",
        )
    cohort = pd.read_parquet(COHORT_PATH, columns=["post_id", "original_text", "mirror_text"])
    return cohort.set_index("post_id")


def extract_errors(labels_path: Path, model_id: str) -> list[ErrorRecord]:
    """Return FN and FP rows for test split; one ErrorRecord per (post, text_role)."""
    labels = pd.read_parquet(labels_path)
    test_labels = labels[labels["split"] == "test"].copy()
    cohort_texts = _load_cohort_texts()

    false_negative_mask = (test_labels["keep_remove_label"] == 1) & (
        test_labels["predicted_label"] == 0
    )
    false_positive_mask = (test_labels["keep_remove_label"] == 0) & (
        test_labels["predicted_label"] == 1
    )
    error_rows = test_labels[false_negative_mask | false_positive_mask]

    records: list[ErrorRecord] = []
    for row in error_rows.itertuples(index=False):
        error_type = "false_negative" if row.keep_remove_label == 1 else "false_positive"
        post_texts = cohort_texts.loc[row.post_id]
        for text_role, text in (
            ("original", str(post_texts.original_text)),
            ("mirror", str(post_texts.mirror_text)),
        ):
            records.append(
                ErrorRecord(
                    post_id=str(row.post_id),
                    model_id=model_id,
                    error_type=error_type,
                    text_role=text_role,
                    text=text,
                    sampled_stance=str(row.sampled_stance),
                    sample_toxicity_type=str(row.sample_toxicity_type),
                    p_remove=float(row.p_remove),
                    remove_share=float(row.remove_share),
                )
            )
    return records


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
    """Return grouping_error or label_error.

    Heuristic (pair-view scorer, per-text clustering arms):
    - false_positive with p_remove >= threshold: model confidently predicts remove while
      humans kept the pair -> label_error on that text view.
    - false_negative with remove_share >= threshold: humans wanted remove but model kept
      the pair -> grouping_error (pair framing hid the remove signal on this text).
    - remaining cases: label_error (model applied a stable criterion that disagrees).
    """
    if record.error_type == "false_positive" and record.p_remove >= PREDICTION_THRESHOLD:
        return "label_error"
    if record.error_type == "false_negative" and record.remove_share >= PREDICTION_THRESHOLD:
        return "grouping_error"
    return "label_error"


def spot_check_table(cluster_df: pd.DataFrame, n_per_topic: int = 3) -> pd.DataFrame:
    """Sample post ids and texts for manual review."""
    raise NotImplementedError


def run_cluster_analysis(*, output_dir: Path) -> dict[str, Any]:
    """Extract, embed, cluster, and write A1/B1 error outputs."""
    raise NotImplementedError
