"""Naive baselines for discovery posts per text arm.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines \\
      --arm original_only \\
      --split discovery \\
      --seed 42
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

import numpy as np
import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths


class DocfreqEntry(TypedDict):
    """One document-frequency row for a unigram or bigram."""

    term: str
    doc_count: int
    n_docs: int


@dataclass(frozen=True)
class BaselineConfig:
    """CLI configuration for one baseline run."""

    arm: str
    split: str
    seed: int
    cohort_run_dir: Path | None
    max_posts: int | None


@dataclass(frozen=True)
class BaselineRunSummary:
    """Summary printed after a baseline run."""

    arm: str
    split: str
    n_posts: int
    docfreq_terms: int
    run_dir: Path


def load_discovery_post_ids(discovery_ids_path: Path) -> set[str]:
    """Load discovery post IDs from the committed CSV."""
    raise NotImplementedError


def load_discovery_posts(
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    split: str,
) -> pd.DataFrame:
    """Return discovery-split posts intersected with the ID list."""
    raise NotImplementedError


def extract_arm_text(row: pd.Series, arm: str) -> str:
    """Return the text surface embedded for one text arm."""
    raise NotImplementedError


def tokenize_text(text: str) -> list[str]:
    """Lemmatize text and drop stopwords plus noisy terms."""
    raise NotImplementedError


def unigrams_from_tokens(tokens: list[str]) -> list[str]:
    """Return unigrams with length at least two characters."""
    raise NotImplementedError


def bigrams_from_tokens(tokens: list[str]) -> list[str]:
    """Return adjacent token bigrams joined with a space."""
    raise NotImplementedError


def compute_docfreq(terms_per_doc: list[set[str]]) -> list[DocfreqEntry]:
    """Score terms by document frequency across posts."""
    raise NotImplementedError


def compute_docfreq_for_class(
    posts: pd.DataFrame,
    arm: str,
    decision: str,
) -> tuple[list[DocfreqEntry], list[DocfreqEntry]]:
    """Return unigram and bigram doc-frequency lists for one decision class."""
    raise NotImplementedError


def embed_posts(
    posts: pd.DataFrame,
    arm: str,
    embed_fn: Callable[[str], np.ndarray],
) -> tuple[list[str], np.ndarray]:
    """Embed one text per discovery post and return aligned IDs and vectors."""
    raise NotImplementedError


def select_k_by_silhouette(
    embeddings: np.ndarray,
    seed: int,
) -> tuple[int, list[dict[str, float | int]], str]:
    """Sweep k from two through ten and pick the best silhouette score."""
    raise NotImplementedError


def fit_kmeans_assignments(
    embeddings: np.ndarray,
    post_ids: list[str],
    selected_k: int,
    seed: int,
) -> dict[str, int]:
    """Fit K-Means at the selected k and return post-to-cluster assignments."""
    raise NotImplementedError


def write_kmeans_seed_outputs(
    output_dir: Path,
    embeddings: np.ndarray,
    post_ids: list[str],
    seed: int,
    cli_seed: int,
) -> None:
    """Write k_selection.json and assignments_kmeans.json for one seed."""
    raise NotImplementedError


def build_metadata(
    config: BaselineConfig,
    run_timestamp: str,
    n_posts: int,
    n_keep: int,
    n_remove: int,
    cohort_run_dir: Path,
) -> dict[str, Any]:
    """Build metadata.json for one baseline run."""
    raise NotImplementedError


def write_baseline_outputs(
    config: BaselineConfig,
    posts: pd.DataFrame,
    embed_fn: Callable[[str], np.ndarray],
) -> BaselineRunSummary:
    """Write doc-frequency, embeddings, K-Means, and metadata artifacts."""
    raise NotImplementedError


def run_baselines(config: BaselineConfig) -> BaselineRunSummary:
    """Run the full baseline pipeline for one text arm."""
    raise NotImplementedError


def parse_args(argv: list[str] | None = None) -> BaselineConfig:
    """Parse CLI arguments into a baseline configuration."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for discovery baselines."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
