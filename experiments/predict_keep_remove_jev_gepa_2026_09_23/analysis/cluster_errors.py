"""Cluster test-set false positives and false negatives for A1 and B1."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

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


def _texts_cache_hash(texts: list[str], model_name: str, seed: int) -> str:
    payload = json.dumps(
        {"model_name": model_name, "seed": seed, "texts": texts},
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _encode_texts(texts: list[str], *, model_name: str, seed: int) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    model.max_seq_length = 256
    try:
        model.set_seed(seed)
    except AttributeError:
        np.random.seed(seed)
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype=np.float32)


def precompute_embeddings(
    texts: list[str],
    *,
    model_name: str = EMBEDDING_MODEL,
    seed: int = EMBEDDING_SEED,
    cache_path: Path,
) -> np.ndarray:
    """Write embeddings to cache_path (npy). Reuse cache when present and hash matches."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    hash_path = cache_path.with_suffix(".hash")
    digest = _texts_cache_hash(texts, model_name, seed)

    if cache_path.is_file() and hash_path.is_file() and hash_path.read_text().strip() == digest:
        logger.info("embedding cache hit for %s", cache_path.name)
        return np.load(cache_path)

    embeddings = _encode_texts(texts, model_name=model_name, seed=seed)
    np.save(cache_path, embeddings)
    hash_path.write_text(digest, encoding="utf-8")
    return embeddings


def kmeans_baseline(
    embeddings: np.ndarray,
    *,
    n_clusters: int,
    seed: int = EMBEDDING_SEED,
) -> np.ndarray:
    """Return cluster labels."""
    if len(embeddings) < n_clusters:
        return np.zeros(len(embeddings), dtype=int)
    clusterer = KMeans(n_clusters=n_clusters, random_state=seed, n_init=1, algorithm="lloyd")
    return clusterer.fit_predict(embeddings)


def run_bertopic(
    texts: list[str],
    embeddings: np.ndarray,
    *,
    seed: int = EMBEDDING_SEED,
    post_ids: list[str] | None = None,
) -> pd.DataFrame:
    """Return topic table with topic id, representative terms, and post_id mapping."""
    if len(texts) < 5:
        return pd.DataFrame(
            columns=["post_id", "topic", "topic_label", "representative_terms", "status"]
        )

    try:
        from bertopic import BERTopic
    except ImportError:
        return pd.DataFrame(
            {
                "post_id": post_ids or [str(index) for index in range(len(texts))],
                "topic": [-1] * len(texts),
                "topic_label": ["bertopic_unavailable"] * len(texts),
                "representative_terms": [""] * len(texts),
                "status": ["skipped_import"] * len(texts),
            }
        )

    try:
        topic_model = BERTopic(
            embedding_model=None,
            calculate_probabilities=False,
            verbose=False,
            seed_model=seed,
        )
        topics, _ = topic_model.fit_transform(texts, embeddings=embeddings)
        topic_info = topic_model.get_topic_info()
        label_by_topic = {
            int(row.Topic): str(row.Name)
            for row in topic_info.itertuples(index=False)
        }
        terms_by_topic: dict[int, str] = {}
        for topic_id in sorted(set(topics)):
            if topic_id == -1:
                terms_by_topic[topic_id] = "outlier"
                continue
            terms = topic_model.get_topic(topic_id) or []
            terms_by_topic[topic_id] = ", ".join(term for term, _weight in terms[:5])

        resolved_post_ids = post_ids or [str(index) for index in range(len(texts))]
        return pd.DataFrame(
            {
                "post_id": resolved_post_ids,
                "topic": topics,
                "topic_label": [label_by_topic.get(int(topic), str(topic)) for topic in topics],
                "representative_terms": [
                    terms_by_topic.get(int(topic), "") for topic in topics
                ],
                "status": ["ok"] * len(texts),
            }
        )
    except Exception as exc:  # noqa: BLE001 - record BERTopic failures and keep K-means
        logger.warning("BERTopic failed: %s", exc)
        return pd.DataFrame(
            {
                "post_id": post_ids or [str(index) for index in range(len(texts))],
                "topic": [-1] * len(texts),
                "topic_label": ["bertopic_failed"] * len(texts),
                "representative_terms": [str(exc)] * len(texts),
                "status": ["failed"] * len(texts),
            }
        )


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
    if cluster_df.empty:
        return pd.DataFrame(columns=["topic", "post_id", "text", "error_type", "error_kind"])

    topic_column = "kmeans_k10" if "kmeans_k10" in cluster_df.columns else "topic"
    sampled_rows: list[dict[str, object]] = []
    for _topic_value, group in cluster_df.groupby(topic_column, sort=True):
        sampled_rows.extend(group.head(n_per_topic).to_dict("records"))
    return pd.DataFrame(sampled_rows)


def _records_to_frame(records: list[ErrorRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "post_id": record.post_id,
                "model_id": record.model_id,
                "error_type": record.error_type,
                "text_role": record.text_role,
                "text": record.text,
                "sampled_stance": record.sampled_stance,
                "sample_toxicity_type": record.sample_toxicity_type,
                "p_remove": record.p_remove,
                "remove_share": record.remove_share,
                "error_kind": classify_error_kind(record),
            }
            for record in records
        ]
    )


def _cluster_one_arm(
    records: list[ErrorRecord],
    *,
    output_dir: Path,
    cache_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not records:
        empty = pd.DataFrame(
            columns=[
                "post_id",
                "model_id",
                "error_type",
                "text_role",
                "text",
                "error_kind",
                "kmeans_k5",
                "kmeans_k10",
                "topic",
                "topic_label",
                "representative_terms",
            ]
        )
        empty.to_parquet(output_dir / "cluster_assignments.parquet", index=False)
        (output_dir / "topic_summary.json").write_text("{}", encoding="utf-8")
        empty_spot = spot_check_table(empty)
        empty_spot.to_csv(output_dir / "spot_checks.csv", index=False)
        return {"n_errors": 0, "bertopic_status": "skipped_empty"}

    frame = _records_to_frame(records)
    texts = frame["text"].tolist()
    post_ids = frame["post_id"].tolist()
    cache_key = f"{frame.iloc[0]['model_id']}_{frame.iloc[0]['text_role']}_{len(texts)}"
    cache_path = cache_dir / f"{cache_key}.npy"
    embeddings = precompute_embeddings(texts, cache_path=cache_path)

    for cluster_count in KMEANS_CLUSTER_COUNTS:
        frame[f"kmeans_k{cluster_count}"] = kmeans_baseline(
            embeddings,
            n_clusters=cluster_count,
        )

    bertopic_df = run_bertopic(texts, embeddings, post_ids=post_ids)
    if not bertopic_df.empty:
        frame = frame.merge(
            bertopic_df[["post_id", "topic", "topic_label", "representative_terms", "status"]],
            on="post_id",
            how="left",
        )
    else:
        frame["topic"] = -1
        frame["topic_label"] = "skipped"
        frame["representative_terms"] = ""
        frame["status"] = "skipped"

    frame.to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    topic_summary: dict[str, Any] = {
        "n_errors": len(frame),
        "error_kind_counts": frame["error_kind"].value_counts().to_dict(),
        "kmeans_k5_counts": frame["kmeans_k5"].value_counts().to_dict(),
        "kmeans_k10_counts": frame["kmeans_k10"].value_counts().to_dict(),
        "stance_counts": {
            f"{stance}|{error_type}": int(count)
            for (stance, error_type), count in frame.groupby(
                ["sampled_stance", "error_type"]
            ).size().items()
        },
        "toxicity_counts": {
            f"{toxicity}|{error_type}": int(count)
            for (toxicity, error_type), count in frame.groupby(
                ["sample_toxicity_type", "error_type"]
            ).size().items()
        },
    }
    if "status" in frame.columns:
        topic_summary["bertopic_status"] = frame["status"].iloc[0]
        topic_summary["bertopic_topic_counts"] = frame["topic"].value_counts().to_dict()
    (output_dir / "topic_summary.json").write_text(
        json.dumps(topic_summary, indent=2, default=str),
        encoding="utf-8",
    )

    spot_checks = spot_check_table(frame)
    spot_checks.to_csv(output_dir / "spot_checks.csv", index=False)
    return topic_summary


def run_cluster_analysis(*, output_dir: Path) -> dict[str, Any]:
    """Extract, embed, cluster, and write A1/B1 error outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "embeddings_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, Any] = {"models": {}, "cluster_arms_written": 0}
    for model_id, labels_path in LABELS_PATHS.items():
        records = extract_errors(labels_path, model_id)
        summaries["models"][model_id] = {"total_error_records": len(records)}
        for text_role in ("original", "mirror"):
            role_records = [record for record in records if record.text_role == text_role]
            arm_dir = output_dir / model_id / text_role
            arm_summary = _cluster_one_arm(
                role_records,
                output_dir=arm_dir,
                cache_dir=cache_dir,
            )
            summaries["models"][model_id][text_role] = arm_summary
            summaries["cluster_arms_written"] += 1

    summary_path = output_dir / "cluster_analysis_summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2, default=str), encoding="utf-8")
    return summaries
