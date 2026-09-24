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
    return paths.latest_cohort_run_dir(arm, constants.PARTICIPANT_FILTER_ALL)


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


def default_embed_fn(text: str) -> np.ndarray:
    """Embed text with the shared Bedrock Titan helper."""
    result = create_embedding(
        text,
        model_id=constants.EMBEDDING_MODEL_ID,
        dimensions=constants.EMBEDDING_DIM,
        normalize=constants.EMBEDDING_NORMALIZE,
    )
    return np.asarray(result["embedding"], dtype=np.float32)


def embed_posts(
    posts: pd.DataFrame,
    arm: str,
    embed_fn: Callable[[str], np.ndarray] | None = None,
) -> tuple[list[str], np.ndarray]:
    """Embed one text per discovery post and return aligned IDs and vectors."""
    embed = embed_fn or default_embed_fn
    post_ids = posts["post_id"].astype(str).tolist()
    vectors = [embed(extract_arm_text(row, arm)) for _, row in posts.iterrows()]
    matrix = np.vstack(vectors) if vectors else np.zeros((0, constants.EMBEDDING_DIM))
    return post_ids, matrix


def _silhouette_sample_size(n_posts: int) -> int:
    return min(SILHOUETTE_SAMPLE_SIZE_CAP, n_posts)


def _kmeans_labels(embeddings: np.ndarray, k: int, seed: int) -> tuple[np.ndarray, float]:
    model = KMeans(
        n_clusters=k,
        random_state=seed,
        n_init=KMEANS_N_INIT,
        max_iter=KMEANS_MAX_ITER,
    )
    labels = model.fit_predict(embeddings)
    return labels, float(model.inertia_)


def _safe_silhouette(
    embeddings: np.ndarray,
    labels: np.ndarray,
    sample_size: int,
    random_state: int,
) -> float:
    if len(set(int(label) for label in labels)) < 2:
        return -1.0
    try:
        return float(
            silhouette_score(
                embeddings,
                labels,
                metric="euclidean",
                sample_size=sample_size,
                random_state=random_state,
            )
        )
    except ValueError:
        return -1.0


def select_k_by_silhouette(
    embeddings: np.ndarray,
    kmeans_seed: int,
    silhouette_seed: int,
) -> tuple[int, list[dict[str, float | int]], str]:
    """Sweep k from two through ten and pick the best silhouette score."""
    n_posts = embeddings.shape[0]
    sample_size = _silhouette_sample_size(n_posts)
    rows: list[dict[str, float | int]] = []
    best_k = K_MIN
    best_silhouette = -1.0
    for k in range(K_MIN, K_MAX + 1):
        if k >= n_posts:
            rows.append({"k": k, "inertia": 0.0, "silhouette": -1.0})
            continue
        labels, inertia = _kmeans_labels(embeddings, k, kmeans_seed)
        silhouette = _safe_silhouette(
            embeddings, labels, sample_size, silhouette_seed
        )
        rows.append({"k": k, "inertia": inertia, "silhouette": silhouette})
        if silhouette > best_silhouette or (
            silhouette == best_silhouette and k < best_k
        ):
            best_silhouette = silhouette
            best_k = k
    return best_k, rows, SELECTION_METHOD


def fit_kmeans_assignments(
    embeddings: np.ndarray,
    post_ids: list[str],
    selected_k: int,
    seed: int,
) -> dict[str, int]:
    """Fit K-Means at the selected k and return post-to-cluster assignments."""
    labels, _ = _kmeans_labels(embeddings, selected_k, seed)
    return {
        post_id: int(cluster_id)
        for post_id, cluster_id in zip(post_ids, labels, strict=True)
    }


def write_kmeans_seed_outputs(
    output_dir: Path,
    embeddings: np.ndarray,
    post_ids: list[str],
    seed: int,
    cli_seed: int,
) -> None:
    """Write k_selection.json and assignments_kmeans.json for one seed."""
    selected_k, rows, selection_method = select_k_by_silhouette(
        embeddings, seed, cli_seed
    )
    assignments = fit_kmeans_assignments(embeddings, post_ids, selected_k, seed)
    seed_dir = output_dir / KMEANS_DIRNAME / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    k_payload = {
        "seed": seed,
        "k_min": K_MIN,
        "k_max": K_MAX,
        "rows": rows,
        "selected_k": selected_k,
        "selection_method": selection_method,
    }
    (seed_dir / K_SELECTION_FILENAME).write_text(
        json.dumps(k_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    assignment_payload = {"selected_k": selected_k, "assignments": assignments}
    (seed_dir / ASSIGNMENTS_KMEANS_FILENAME).write_text(
        json.dumps(assignment_payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _count_decision(posts: pd.DataFrame, decision: str) -> int:
    return int(posts["modal_decision"].eq(decision).sum())


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_metadata(
    config: BaselineConfig,
    run_timestamp: str,
    n_posts: int,
    n_keep: int,
    n_remove: int,
    cohort_run_dir: Path,
) -> dict[str, Any]:
    """Build metadata.json for one baseline run."""
    cohort_glob = (
        f"outputs/{config.arm}/cohort/*/cohort.parquet"
    )
    return {
        "arm": config.arm,
        "split": config.split,
        "run_timestamp": run_timestamp,
        "n_posts": n_posts,
        "n_keep": n_keep,
        "n_remove": n_remove,
        "bedrock_model_id": constants.EMBEDDING_MODEL_ID,
        "embedding_dimensions": constants.EMBEDDING_DIM,
        "embedding_normalize": constants.EMBEDDING_NORMALIZE,
        "kmeans_k_values": list(range(K_MIN, K_MAX + 1)),
        "kmeans_seeds": list(constants.CLUSTER_SEEDS),
        "discovery_post_ids_path": f"data/post_split/{DISCOVERY_IDS_FILENAME}",
        "cohort_source_glob": cohort_glob,
    }


def write_baseline_outputs(
    config: BaselineConfig,
    posts: pd.DataFrame,
    embed_fn: Callable[[str], np.ndarray] | None = None,
) -> BaselineRunSummary:
    """Write doc-frequency, embeddings, K-Means, and metadata artifacts."""
    run_timestamp = paths.make_run_timestamp()
    run_dir = paths.baselines_dir(config.arm) / run_timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    docfreq_outputs = build_docfreq_outputs(posts, config.arm)
    for key, rows in docfreq_outputs.items():
        _write_json(run_dir / f"{key}.json", rows)
    post_ids, embeddings = embed_posts(posts, config.arm, embed_fn)
    np.save(run_dir / POST_EMBEDDINGS_FILENAME, embeddings)
    _write_json(run_dir / POST_IDS_FILENAME, post_ids)
    for cluster_seed in constants.CLUSTER_SEEDS:
        write_kmeans_seed_outputs(
            run_dir, embeddings, post_ids, cluster_seed, config.seed
        )
    metadata = build_metadata(
        config,
        run_timestamp,
        len(posts),
        _count_decision(posts, constants.DECISION_KEEP),
        _count_decision(posts, constants.DECISION_REMOVE),
        paths.cohort_dir(config.arm),
    )
    _write_json(run_dir / constants.METADATA_FILENAME, metadata)
    docfreq_terms = sum(len(rows) for rows in docfreq_outputs.values())
    return BaselineRunSummary(
        arm=config.arm,
        split=config.split,
        n_posts=len(posts),
        docfreq_terms=docfreq_terms,
        run_dir=run_dir,
    )


def run_baselines(config: BaselineConfig) -> BaselineRunSummary:
    """Run the full baseline pipeline for one text arm."""
    if config.split != constants.DISCOVERY_SPLIT:
        raise ValueError(f"baselines only support split={constants.DISCOVERY_SPLIT}")
    if config.arm not in constants.TEXT_ARMS:
        raise ValueError(f"unsupported arm: {config.arm}")
    cohort_run_dir = resolve_cohort_run_dir(config.arm, config.cohort_run_dir)
    cohort = load_cohort_frame(cohort_run_dir)
    discovery_ids = load_discovery_post_ids(
        paths.post_split_dir() / DISCOVERY_IDS_FILENAME
    )
    posts = load_discovery_posts(cohort, discovery_ids, config.split)
    if config.max_posts is not None:
        posts = posts.head(config.max_posts).copy()
    return write_baseline_outputs(config, posts)


def parse_args(argv: list[str] | None = None) -> BaselineConfig:
    """Parse CLI arguments into a baseline configuration."""
    parser = argparse.ArgumentParser(description="Run discovery baselines.")
    parser.add_argument("--arm", required=True, choices=list(constants.TEXT_ARMS))
    parser.add_argument("--split", required=True, choices=[constants.DISCOVERY_SPLIT])
    parser.add_argument("--seed", type=int, default=constants.DEFAULT_SEED)
    parser.add_argument("--cohort-run-dir", default=None)
    parser.add_argument("--max-posts", type=int, default=None)
    args = parser.parse_args(argv)
    cohort_path = Path(args.cohort_run_dir) if args.cohort_run_dir else None
    return BaselineConfig(
        arm=args.arm,
        split=args.split,
        seed=args.seed,
        cohort_run_dir=cohort_path,
        max_posts=args.max_posts,
    )


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for discovery baselines."""
    config = parse_args(argv)
    summary = run_baselines(config)
    k_values = len(range(K_MIN, K_MAX + 1))
    seed_list = ",".join(str(value) for value in constants.CLUSTER_SEEDS)
    print(
        f"arm={summary.arm} split={summary.split} n_posts={summary.n_posts} "
        f"docfreq_terms={summary.docfreq_terms} kmeans_k_values={k_values} "
        f"kmeans_seeds={seed_list}"
    )
    print(f"Wrote {summary.run_dir.relative_to(paths.EXPERIMENT_ROOT)}/")


if __name__ == "__main__":
    main()
