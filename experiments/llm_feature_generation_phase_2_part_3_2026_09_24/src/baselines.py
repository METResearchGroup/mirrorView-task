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
import re
import string
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, TypedDict

import numpy as np
import pandas as pd
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from shared.embeddings.bedrock import create_embedding

K_MIN: int = 2
K_MAX: int = 10
KMEANS_N_INIT: int = 10
KMEANS_MAX_ITER: int = 300
SILHOUETTE_SAMPLE_SIZE_CAP: int = 4000
MIN_TOKEN_LENGTH: int = 2
PAIRED_TEXT_SEPARATOR: str = "\n\n"
NOISY_WORDS: frozenset[str] = frozenset(
    {
        "thinking",
        "keeping",
        "deciding",
        "response",
        "post",
        "content",
        "comment",
    }
)
DISCOVERY_IDS_FILENAME: str = "discovery_post_ids.csv"
DOCFREQ_KEEP_UNIGRAMS_FILENAME: str = "docfreq_keep_unigrams.json"
DOCFREQ_REMOVE_UNIGRAMS_FILENAME: str = "docfreq_remove_unigrams.json"
DOCFREQ_KEEP_BIGRAMS_FILENAME: str = "docfreq_keep_bigrams.json"
DOCFREQ_REMOVE_BIGRAMS_FILENAME: str = "docfreq_remove_bigrams.json"
POST_IDS_FILENAME: str = "post_ids.json"
POST_EMBEDDINGS_FILENAME: str = "post_embeddings.npy"
KMEANS_DIRNAME: str = "kmeans"
K_SELECTION_FILENAME: str = "k_selection.json"
ASSIGNMENTS_KMEANS_FILENAME: str = "assignments_kmeans.json"
SELECTION_METHOD: str = "silhouette_max"

ARM_TEXT_COLUMNS: dict[str, str | tuple[str, str]] = {
    "original_only": "original_text",
    "mirror_only": "mirror_text",
    "paired": ("original_text", "mirror_text"),
}


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


def resolve_cohort_run_dir(arm: str, cohort_run_dir: Path | None) -> Path:
    """Return the cohort run directory from an explicit path or the latest run."""
    if cohort_run_dir is not None:
        return cohort_run_dir
    return paths.latest_timestamp_subdir(paths.cohort_dir(arm))


def load_cohort_frame(cohort_run_dir: Path) -> pd.DataFrame:
    """Load cohort.parquet from one cohort run directory."""
    cohort_path = cohort_run_dir / constants.COHORT_FILENAME
    if not cohort_path.is_file():
        raise FileNotFoundError(f"Missing cohort parquet: {cohort_path}")
    return pd.read_parquet(cohort_path)


def load_discovery_post_ids(discovery_ids_path: Path) -> set[str]:
    """Load discovery post IDs from the committed CSV."""
    frame = pd.read_csv(discovery_ids_path)
    return set(frame["post_id"].astype(str))


def load_discovery_posts(
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    split: str,
) -> pd.DataFrame:
    """Return discovery-split posts intersected with the ID list."""
    post_ids = cohort["post_id"].astype(str)
    mask = post_ids.isin(discovery_ids) & cohort["split"].eq(split)
    return cohort.loc[mask].copy()


def extract_arm_text(row: pd.Series, arm: str) -> str:
    """Return the text surface embedded for one text arm."""
    mapping = ARM_TEXT_COLUMNS[arm]
    if isinstance(mapping, tuple):
        original = str(row[mapping[0]])
        mirror = str(row[mapping[1]])
        return f"{original}{PAIRED_TEXT_SEPARATOR}{mirror}"
    return str(row[mapping])


@lru_cache(maxsize=1)
def _english_stopwords() -> frozenset[str]:
    return frozenset(STOP_WORDS) | NOISY_WORDS


@lru_cache(maxsize=1)
def _spacy_nlp() -> spacy.language.Language:
    return spacy.load("en_core_web_sm")


def _normalize_surface(text: str) -> str:
    lowered = text.lower()
    table = str.maketrans(string.punctuation, " " * len(string.punctuation))
    return re.sub(r"\s+", " ", lowered.translate(table)).strip()


def _lemma_for_token(token: spacy.tokens.Token, nlp_model: spacy.language.Language) -> str:
    lemma = token.lemma_.lower()
    surface = token.text.lower()
    if lemma != surface or not surface.endswith("ing"):
        return lemma
    probe = nlp_model(f"they are {surface}")
    for probe_token in probe:
        if probe_token.text.lower() == surface:
            return probe_token.lemma_.lower()
    return lemma


def tokenize_text(text: str) -> list[str]:
    """Lemmatize text and drop stopwords plus noisy terms."""
    surface = _normalize_surface(text)
    if not surface:
        return []
    nlp_model = _spacy_nlp()
    doc = nlp_model(surface)
    blocked = _english_stopwords()
    lemmas = [_lemma_for_token(token, nlp_model) for token in doc]
    return [lemma for lemma in lemmas if lemma not in blocked and lemma.strip()]


def unigrams_from_tokens(tokens: list[str]) -> list[str]:
    """Return unigrams with length at least two characters."""
    return [token for token in tokens if len(token) >= MIN_TOKEN_LENGTH]


def bigrams_from_tokens(tokens: list[str]) -> list[str]:
    """Return adjacent token bigrams joined with a space."""
    pairs = zip(tokens, tokens[1:])
    return [f"{left} {right}" for left, right in pairs]


def compute_docfreq(terms_per_doc: list[set[str]]) -> list[DocfreqEntry]:
    """Score terms by document frequency across posts."""
    n_docs = len(terms_per_doc)
    counts: dict[str, int] = {}
    for term_set in terms_per_doc:
        for term in term_set:
            counts[term] = counts.get(term, 0) + 1
    rows = [
        DocfreqEntry(term=term, doc_count=doc_count, n_docs=n_docs)
        for term, doc_count in counts.items()
    ]
    return sorted(rows, key=lambda row: (-row["doc_count"], row["term"]))


def terms_for_post(text: str) -> tuple[set[str], set[str]]:
    """Return unigram and bigram term sets for one post after preprocessing."""
    tokens = tokenize_text(text)
    unigrams = set(unigrams_from_tokens(tokens))
    bigrams = set(bigrams_from_tokens(tokens))
    return unigrams, bigrams


def _labeled_posts(posts: pd.DataFrame, decision: str) -> pd.DataFrame:
    return posts.loc[posts["modal_decision"].eq(decision)].copy()


def _terms_by_post(posts: pd.DataFrame, arm: str) -> list[tuple[set[str], set[str]]]:
    return [
        terms_for_post(extract_arm_text(row, arm))
        for _, row in posts.iterrows()
    ]


def compute_docfreq_for_class(
    posts: pd.DataFrame,
    arm: str,
    decision: str,
) -> tuple[list[DocfreqEntry], list[DocfreqEntry]]:
    """Return unigram and bigram doc-frequency lists for one decision class."""
    labeled = _labeled_posts(posts, decision)
    term_pairs = _terms_by_post(labeled, arm)
    unigram_sets = [pair[0] for pair in term_pairs]
    bigram_sets = [pair[1] for pair in term_pairs]
    return compute_docfreq(unigram_sets), compute_docfreq(bigram_sets)


def build_docfreq_outputs(
    posts: pd.DataFrame,
    arm: str,
) -> dict[str, list[DocfreqEntry]]:
    """Build keep and remove unigram and bigram doc-frequency outputs."""
    keep_uni, keep_bi = compute_docfreq_for_class(
        posts, arm, constants.DECISION_KEEP
    )
    remove_uni, remove_bi = compute_docfreq_for_class(
        posts, arm, constants.DECISION_REMOVE
    )
    return {
        "docfreq_keep_unigrams": keep_uni,
        "docfreq_remove_unigrams": remove_uni,
        "docfreq_keep_bigrams": keep_bi,
        "docfreq_remove_bigrams": remove_bi,
    }


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
