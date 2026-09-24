"""Cross-role topic comparisons for Part 3 original and mirror text.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_cross_role.py \\
      --original-topics-run-dir <dir> --mirror-topics-run-dir <dir> \\
      --joint-topics-run-dir <dir> --mirror-assignments-run-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import binomtest
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from statsmodels.stats.multitest import multipletests

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)

NOISE_TOPIC_ID = -1
ROLE_SHARE_LOW = 0.35
ROLE_SHARE_HIGH = 0.65
FDR_Q = 0.05
DIRICHLET_ALPHA = 0.01
TOP_TERMS_PER_ROLE = 15
DEFAULT_BOOTSTRAP_N = 1000
DEFAULT_SEED = 42
CI_LOW_PERCENTILE = 2.5
CI_HIGH_PERCENTILE = 97.5
VECTORIZER_MIN_DF = 2
Q4_COLUMNS = ["topic", "term", "role", "rank", "log_odds", "count_original", "count_mirror"]


def apply_bh_fdr(pvalues: list[float]) -> np.ndarray:
    """Return Benjamini-Hochberg q-values for ``pvalues``."""
    if not pvalues:
        return np.array([], dtype=np.float64)
    _rejected, q_values, _alphac, _alphac_bonf = multipletests(pvalues, method="fdr_bh")
    return np.asarray(q_values, dtype=np.float64)


def agreement_rate_all(pairs: pd.DataFrame) -> float:
    """Fraction of pairs whose original and mirror topics match, including noise."""
    return float((pairs["original_topic"] == pairs["mirror_topic"]).mean())


def agreement_rate_excl_noise(pairs: pd.DataFrame) -> float:
    """Agreement among pairs where neither topic is the noise topic."""
    labeled = pairs.loc[
        (pairs["original_topic"] != NOISE_TOPIC_ID) & (pairs["mirror_topic"] != NOISE_TOPIC_ID)
    ]
    if labeled.empty:
        return float("nan")
    return float((labeled["original_topic"] == labeled["mirror_topic"]).mean())


def bootstrap_rate_ci(flags: np.ndarray, bootstrap_n: int, seed: int) -> tuple[float, float, float]:
    """Return the point estimate and percentile CI for a boolean rate.

    Parameters
    ----------
    flags
        One boolean per pair.
    bootstrap_n
        Resamples with replacement.
    seed
        NumPy Generator seed.

    Returns
    -------
    tuple[float, float, float]
        Point estimate, 2.5th percentile, 97.5th percentile.
    """
    point = float(np.mean(flags))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(flags), size=(bootstrap_n, len(flags)))
    rates = flags[draws].mean(axis=1)
    return point, float(np.percentile(rates, CI_LOW_PERCENTILE)), float(np.percentile(rates, CI_HIGH_PERCENTILE))


def match_topics_hungarian(
    sim_matrix: np.ndarray,
    orig_ids: list[int],
    mirror_ids: list[int],
) -> dict[int, int]:
    """Match original topics to mirror topics by cosine similarity.

    Parameters
    ----------
    sim_matrix
        Rows are original topics, columns are mirror topics.
    orig_ids
        Topic ids for rows.
    mirror_ids
        Topic ids for columns.

    Returns
    -------
    dict[int, int]
        Original topic id to mirror topic id.
    """
    cost = 1.0 - np.asarray(sim_matrix, dtype=np.float64)
    row_index, col_index = linear_sum_assignment(cost)
    return {int(orig_ids[int(row)]): int(mirror_ids[int(col)]) for row, col in zip(row_index, col_index)}


def ari_after_mapping(original_topics: list[int], mirror_topics: list[int], mapping: dict[int, int]) -> float:
    """Adjusted Rand index after remapping mirror topics onto original ids."""
    remapped = [mapping.get(topic, topic) for topic in mirror_topics]
    return float(adjusted_rand_score(original_topics, remapped))


def nmi_after_mapping(original_topics: list[int], mirror_topics: list[int], mapping: dict[int, int]) -> float:
    """Normalized mutual information after the same remapping."""
    remapped = [mapping.get(topic, topic) for topic in mirror_topics]
    return float(normalized_mutual_info_score(original_topics, remapped))


def flag_role_dominated(original_share: float, q_value_bh: float) -> bool:
    """True when a topic's original share is outside [0.35, 0.65] and q < 0.05."""
    outside = original_share < ROLE_SHARE_LOW or original_share > ROLE_SHARE_HIGH
    return bool(outside and q_value_bh < FDR_Q)


def role_share_table(assignments: pd.DataFrame) -> pd.DataFrame:
    """Per-topic original share, binomial test, and BH flag for a joint fit."""
    grouped = (
        assignments.groupby("topic")
        .agg(n_docs=("text_role", "size"), n_original=("text_role", lambda roles: int((roles == "original").sum())))
        .reset_index()
    )
    grouped["n_mirror"] = grouped["n_docs"] - grouped["n_original"]
    grouped["original_share"] = grouped["n_original"] / grouped["n_docs"]
    pvalues = [
        float(binomtest(int(row.n_original), int(row.n_docs), 0.5).pvalue)
        for row in grouped.itertuples(index=False)
    ]
    grouped["binomial_pvalue"] = pvalues
    grouped["q_value_bh"] = apply_bh_fdr(pvalues)
    grouped["role_dominated_flag"] = [
        flag_role_dominated(float(share), float(q_value))
        for share, q_value in zip(grouped["original_share"], grouped["q_value_bh"])
    ]
    return grouped


def pair_coassignment_rate(joint_assignments: pd.DataFrame) -> dict:
    """Fraction of posts whose original and mirror rows share a joint topic."""
    original = joint_assignments.loc[joint_assignments["text_role"] == "original", ["post_id", "topic"]]
    mirror = joint_assignments.loc[joint_assignments["text_role"] == "mirror", ["post_id", "topic"]]
    paired = original.merge(mirror, on="post_id", suffixes=("_original", "_mirror"))
    n_coassigned = int((paired["topic_original"] == paired["topic_mirror"]).sum())
    n_pairs = int(len(paired))
    rate = float(n_coassigned / n_pairs) if n_pairs else float("nan")
    return {"pair_coassignment_rate": rate, "n_pairs": n_pairs, "n_coassigned": n_coassigned}


def log_odds_with_dirichlet(count_o: int, count_m: int, n_o: int, n_m: int, alpha: float) -> float:
    """Monroe-style log-odds. Positive values favor the original side.

    Parameters
    ----------
    count_o
        Original count of the term.
    count_m
        Mirror count of the term.
    n_o
        Original token total.
    n_m
        Mirror token total.
    alpha
        Dirichlet prior strength.
    """
    original_odds = (count_o + alpha) / (n_o - count_o + alpha)
    mirror_odds = (count_m + alpha) / (n_m - count_m + alpha)
    return float(math.log(original_odds) - math.log(mirror_odds))


def top_contrast_terms(
    topic: int,
    original_counts: dict[str, int],
    mirror_counts: dict[str, int],
    alpha: float = DIRICHLET_ALPHA,
    top_n: int = TOP_TERMS_PER_ROLE,
) -> pd.DataFrame:
    """Keep the top terms favoring each role inside one topic."""
    terms = sorted(set(original_counts) | set(mirror_counts))
    if not terms:
        return pd.DataFrame(columns=["topic", "term", "role", "rank", "log_odds", "count_original", "count_mirror"])
    n_o = sum(original_counts.values())
    n_m = sum(mirror_counts.values())
    rows = []
    for term in terms:
        count_o = int(original_counts.get(term, 0))
        count_m = int(mirror_counts.get(term, 0))
        rows.append(
            {
                "topic": topic,
                "term": term,
                "log_odds": log_odds_with_dirichlet(count_o, count_m, n_o, n_m, alpha),
                "count_original": count_o,
                "count_mirror": count_m,
            }
        )
    frame = pd.DataFrame(rows)
    original_side = frame.sort_values("log_odds", ascending=False).head(top_n).copy()
    original_side["role"] = "original"
    mirror_side = frame.sort_values("log_odds", ascending=True).head(top_n).copy()
    mirror_side["role"] = "mirror"
    chosen = pd.concat([original_side, mirror_side], ignore_index=True)
    chosen["rank"] = chosen.groupby("role").cumcount() + 1
    return chosen[["topic", "term", "role", "rank", "log_odds", "count_original", "count_mirror"]]


def q2_agreement_table(pairs: pd.DataFrame, bootstrap_n: int, seed: int) -> pd.DataFrame:
    """Point estimates and bootstrap CIs for the two agreement rates."""
    all_flags = (pairs["original_topic"] == pairs["mirror_topic"]).to_numpy()
    labeled = pairs.loc[
        (pairs["original_topic"] != NOISE_TOPIC_ID) & (pairs["mirror_topic"] != NOISE_TOPIC_ID)
    ]
    excl_flags = (labeled["original_topic"] == labeled["mirror_topic"]).to_numpy()
    rows = []
    for metric, flags, n_pairs in (
        ("agreement_rate_all", all_flags, len(pairs)),
        ("agreement_rate_excl_noise", excl_flags, len(labeled)),
    ):
        point, low, high = bootstrap_rate_ci(flags, bootstrap_n, seed)
        rows.append(
            {
                "metric": metric,
                "point_estimate": point,
                "ci_low": low,
                "ci_high": high,
                "n_pairs": int(n_pairs),
                "bootstrap_n": bootstrap_n,
                "seed": seed,
            }
        )
    return pd.DataFrame(rows)


def keyword_count_map(texts: list[str]) -> dict[str, int]:
    """Token counts for one role inside one topic, with English stopwords.

    Terms must appear in at least two documents. Fewer than two documents
    yields an empty map.
    """
    usable = [text for text in texts if isinstance(text, str) and text.strip()]
    if len(usable) < VECTORIZER_MIN_DF:
        return {}
    vectorizer = CountVectorizer(stop_words="english", min_df=VECTORIZER_MIN_DF)
    try:
        matrix = vectorizer.fit_transform(usable)
    except ValueError:
        return {}
    totals = np.asarray(matrix.sum(axis=0)).ravel()
    return {
        term: int(count)
        for term, count in zip(vectorizer.get_feature_names_out(), totals)
        if int(count) > 0
    }


def compute_q4_keyword_contrast(joint_assignments: pd.DataFrame, corpus: pd.DataFrame) -> pd.DataFrame:
    """Log-odds keyword contrast for each non-noise joint topic."""
    joined = joint_assignments.merge(
        corpus[["post_id", "text_role", "text"]],
        on=["post_id", "text_role"],
        how="inner",
    )
    frames = []
    for topic, group in joined.groupby("topic"):
        if int(topic) == NOISE_TOPIC_ID:
            continue
        original_texts = group.loc[group["text_role"] == "original", "text"].astype(str).tolist()
        mirror_texts = group.loc[group["text_role"] == "mirror", "text"].astype(str).tolist()
        contrast = top_contrast_terms(
            int(topic),
            keyword_count_map(original_texts),
            keyword_count_map(mirror_texts),
        )
        if not contrast.empty:
            frames.append(contrast)
    if not frames:
        return pd.DataFrame(columns=Q4_COLUMNS)
    return pd.concat(frames, ignore_index=True)[Q4_COLUMNS]


def _vectors_by_post_id(role: str) -> dict[str, np.ndarray]:
    """Titan vectors for one text role, keyed by post id."""
    cache = paths.embeddings_dir(role)
    matrix = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    return {str(row.post_id): matrix[int(row.row_id)] for row in index.itertuples(index=False)}


def centroids_for_assignments(
    assignments: pd.DataFrame,
    vectors: dict[str, np.ndarray],
) -> tuple[list[int], np.ndarray]:
    """L2-normalized mean embedding per non-noise topic."""
    sums: dict[int, np.ndarray] = {}
    counts: dict[int, int] = {}
    width = next(iter(vectors.values())).shape[0] if vectors else 0
    for row in assignments.itertuples(index=False):
        topic = int(row.topic)
        if topic == NOISE_TOPIC_ID:
            continue
        vector = vectors.get(str(row.post_id))
        if vector is None:
            continue
        if topic not in sums:
            sums[topic] = np.zeros(width, dtype=np.float64)
            counts[topic] = 0
        sums[topic] = sums[topic] + np.asarray(vector, dtype=np.float64)
        counts[topic] += 1
    topic_ids = sorted(sums)
    rows = []
    for topic in topic_ids:
        mean = sums[topic] / counts[topic]
        norm = float(np.linalg.norm(mean))
        rows.append(mean / norm if norm else mean)
    if not rows:
        return [], np.zeros((0, width))
    return topic_ids, np.vstack(rows)


def _single_role_assignments(assignments: pd.DataFrame, role: str) -> pd.DataFrame:
    """Keep one text role when a run stores both."""
    if "text_role" not in assignments.columns:
        return assignments
    return assignments.loc[assignments["text_role"] == role].copy()


def run_cross_role_analysis(
    original_topics_run_dir: Path,
    mirror_topics_run_dir: Path,
    joint_topics_run_dir: Path,
    mirror_assignments_run_dir: Path,
    seed: int = DEFAULT_SEED,
    bootstrap_n: int = DEFAULT_BOOTSTRAP_N,
    output_dir: Path | None = None,
) -> Path:
    """Write Q2 to Q4 tables for one set of production runs.

    Separate-model ARI remaps mirror topic ids with Hungarian matching on
    topic-centroid cosine similarity. Pair agreement still uses the original
    model's ``transform`` assignments.
    """
    pairs = pd.read_parquet(mirror_assignments_run_dir / "pair_assignments.parquet")
    joint = pd.read_parquet(joint_topics_run_dir / "assignments.parquet")
    agreement = q2_agreement_table(pairs, bootstrap_n, seed)
    shares = role_share_table(joint)
    coassignment = pair_coassignment_rate(joint)
    contrast = compute_q4_keyword_contrast(joint, data_mod.load_fit_corpus("joint"))
    run_dir = output_dir or (paths.analyses_dir() / "cross_role" / paths.new_run_timestamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    agreement.to_parquet(run_dir / "q2_pair_agreement.parquet", index=False)
    shares.to_parquet(run_dir / "q3_role_shares.parquet", index=False)
    contrast.to_parquet(run_dir / "q4_keyword_contrast.parquet", index=False)
    (run_dir / "q3_coassignment.json").write_text(json.dumps(coassignment, indent=2) + "\n", encoding="utf-8")
    ari_payload = _ari_from_saved_assignments(original_topics_run_dir, mirror_topics_run_dir)
    (run_dir / "q2_ari_nmi.json").write_text(json.dumps(ari_payload, indent=2) + "\n", encoding="utf-8")
    summary = {
        "q2": {
            "agreement_rate_all": float(agreement.loc[agreement.metric == "agreement_rate_all", "point_estimate"].iloc[0]),
            "agreement_rate_excl_noise": float(
                agreement.loc[agreement.metric == "agreement_rate_excl_noise", "point_estimate"].iloc[0]
            ),
            "ari": ari_payload["ari"],
            "nmi": ari_payload["nmi"],
        },
        "q3": {
            "n_role_dominated": int(shares["role_dominated_flag"].sum()),
            "pair_coassignment_rate": coassignment["pair_coassignment_rate"],
        },
        "dirichlet_alpha": DIRICHLET_ALPHA,
        "artifact_paths": {
            "original_topics_run": str(original_topics_run_dir),
            "mirror_topics_run": str(mirror_topics_run_dir),
            "joint_topics_run": str(joint_topics_run_dir),
            "mirror_assignments_run": str(mirror_assignments_run_dir),
        },
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"analysis_run_dir={run_dir}")
    return run_dir


def _remap_mirror_topic(topic: int, mirror_to_original: dict[int, int]) -> int:
    """Map a mirror topic onto the original id space without id collisions."""
    if topic in mirror_to_original:
        return mirror_to_original[topic]
    if topic == NOISE_TOPIC_ID:
        return NOISE_TOPIC_ID
    return -(topic + 2)


def _ari_from_saved_assignments(
    original_topics_run_dir: Path,
    mirror_topics_run_dir: Path,
) -> dict:
    """ARI/NMI after Hungarian matching of topic centroids.

    Centroids are mean Titan embeddings of non-noise documents. Unmatched
    mirror topics keep a private id so they cannot collide with an original topic.
    """
    original = _single_role_assignments(
        pd.read_parquet(original_topics_run_dir / "assignments.parquet"),
        "original",
    )
    mirror = _single_role_assignments(
        pd.read_parquet(mirror_topics_run_dir / "assignments.parquet"),
        "mirror",
    )
    paired = original[["post_id", "topic"]].merge(
        mirror[["post_id", "topic"]],
        on="post_id",
        suffixes=("_original", "_mirror"),
    )
    original_ids, original_centroids = centroids_for_assignments(original, _vectors_by_post_id("original"))
    mirror_ids, mirror_centroids = centroids_for_assignments(mirror, _vectors_by_post_id("mirror"))
    if not original_ids or not mirror_ids or paired.empty:
        return {
            "n_pairs": int(len(paired)),
            "n_original_topics_matched": 0,
            "n_mirror_topics_matched": 0,
            "ari": 0.0,
            "nmi": 0.0,
            "matching": "hungarian_centroid",
            "topic_mapping": [],
        }
    similarity = original_centroids @ mirror_centroids.T
    forward = match_topics_hungarian(similarity, original_ids, mirror_ids)
    mirror_to_original = {mirror_topic: original_topic for original_topic, mirror_topic in forward.items()}
    remapped = [
        _remap_mirror_topic(int(topic), mirror_to_original) for topic in paired["topic_mirror"].tolist()
    ]
    original_labels = [int(topic) for topic in paired["topic_original"].tolist()]
    original_index = {topic: index for index, topic in enumerate(original_ids)}
    mirror_index = {topic: index for index, topic in enumerate(mirror_ids)}
    topic_mapping = [
        {
            "original_topic": int(original_topic),
            "mirror_topic": int(mirror_topic),
            "cosine_sim": float(similarity[original_index[original_topic], mirror_index[mirror_topic]]),
        }
        for original_topic, mirror_topic in forward.items()
    ]
    return {
        "n_pairs": int(len(paired)),
        "n_original_topics_matched": len(forward),
        "n_mirror_topics_matched": len(forward),
        "ari": float(adjusted_rand_score(original_labels, remapped)),
        "nmi": float(normalized_mutual_info_score(original_labels, remapped)),
        "matching": "hungarian_centroid",
        "topic_mapping": topic_mapping,
    }


def main() -> None:
    """CLI entry for Q2 to Q4."""
    parser = argparse.ArgumentParser(description="Compare original, mirror, and joint topics.")
    parser.add_argument("--original-topics-run-dir", type=Path, required=True)
    parser.add_argument("--mirror-topics-run-dir", type=Path, required=True)
    parser.add_argument("--joint-topics-run-dir", type=Path, required=True)
    parser.add_argument("--mirror-assignments-run-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bootstrap-n", type=int, default=DEFAULT_BOOTSTRAP_N)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run_cross_role_analysis(
        args.original_topics_run_dir,
        args.mirror_topics_run_dir,
        args.joint_topics_run_dir,
        args.mirror_assignments_run_dir,
        args.seed,
        args.bootstrap_n,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
