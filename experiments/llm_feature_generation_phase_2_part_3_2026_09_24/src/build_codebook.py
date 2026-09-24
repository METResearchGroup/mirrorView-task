"""Build a shared moderation codebook from per-arm cluster labels.

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.build_codebook \\
        --seeds 42 43 44 --write-draft
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, llm_client, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import build_codebook_rewrite_messages
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import (
    ClusterLabelResult,
    CodebookRewriteBatch,
)
from shared.embeddings.bedrock import create_embedding
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines import (
    extract_arm_text,
    load_discovery_post_ids,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_clusters import (
    load_hdbscan_assignments,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.paths import (
    latest_timestamp_subdir,
    make_run_timestamp,
)
DISCOVERY_IDS_PATH = paths.post_split_dir() / "discovery_post_ids.csv"
SYNONYMS_PATH = paths.EXPERIMENT_ROOT / "data" / constants.FEATURE_SYNONYMS_FILENAME
DROP_REASON_TOPIC_ONLY = "topic_only"
EMPTY_ARMS_TEMPLATE = {arm: [] for arm in constants.TEXT_ARMS}
_TOPIC_POLICY_RE = re.compile(
    r"\b(?:" + "|".join(constants.TOPIC_ONLY_POLICY_TERMS) + r")\b",
    re.IGNORECASE,
)
_PURE_TOPIC_DEF_RE = re.compile(
    r"^(?:post|posts|content|cluster|features?)\s+(?:is|are|about|discuss(?:es|ing)?|on|regarding)\b",
    re.IGNORECASE,
)
_OUTCOME_LEAKAGE_RE = re.compile(
    r"\b(?:" + "|".join(constants.OUTCOME_LEAKAGE_TERMS) + r")\b",
    re.IGNORECASE,
)
_TOPIC_STANCE_RE = re.compile(
    r"\b(democrats?|republicans?|the left|the right|\bgop\b|\bdnc\b)\b",
    re.IGNORECASE,
)
_TOPIC_POLICY_PHRASE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgun policy\b", re.IGNORECASE),
    re.compile(r"\bsecond amendment\b", re.IGNORECASE),
    re.compile(r"\belection integrity\b", re.IGNORECASE),
    re.compile(r"\bfraud claims?\b", re.IGNORECASE),
    re.compile(r"\benergy policy\b", re.IGNORECASE),
    re.compile(r"\beconomic policy\b", re.IGNORECASE),
    re.compile(r"\beconomic costs?\b", re.IGNORECASE),
)
_RHETORIC_MEMBER_CATEGORIES: frozenset[str] = frozenset(
    {
        "surface_lexical",
        "pragmatics_intent",
        "compositional_syntax",
        "semantic_content",
        "target_directionality",
    }
)


@dataclass(frozen=True)
class PostExample:
    """One discovery-half post example stored in the codebook."""

    post_id: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"post_id": self.post_id, "text": self.text}


@dataclass(frozen=True)
class CodebookFeature:
    """One operationalized feature in the shared codebook."""

    feature_id: str
    name: str
    definition: str
    positive_examples: tuple[PostExample, ...]
    negative_examples: tuple[PostExample, ...]
    discovery_arm: str
    source_cluster_ids: dict[str, list[int]]
    member_feature_ids: tuple[str, ...]
    cluster_size: int
    source_cluster_label: str
    source_definition: str
    member_records: tuple[dict[str, Any], ...] = ()
    discovery_arms: tuple[str, ...] = ()
    merged_source_feature_ids: tuple[str, ...] = ()
    part2_theme_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "feature_id": self.feature_id,
            "name": self.name,
            "definition": self.definition,
            "source_cluster_label": self.source_cluster_label,
            "source_definition": self.source_definition,
            "positive_examples": [ex.to_dict() for ex in self.positive_examples],
            "negative_examples": [ex.to_dict() for ex in self.negative_examples],
            "discovery_arm": self.discovery_arm,
            "source_cluster_ids": self.source_cluster_ids,
            "member_feature_ids": list(self.member_feature_ids),
            "cluster_size": self.cluster_size,
            "part2_theme_id": self.part2_theme_id,
        }
        if self.discovery_arms:
            payload["discovery_arms"] = list(self.discovery_arms)
        if self.merged_source_feature_ids:
            payload["merged_source_feature_ids"] = list(self.merged_source_feature_ids)
        return payload


@dataclass(frozen=True)
class CodebookDraft:
    """Draft codebook payload written to JSON."""

    version: str
    features: tuple[CodebookFeature, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "features": [feature.to_dict() for feature in self.features],
        }


@dataclass(frozen=True)
class DroppedFeature:
    """Audit row for a topic-only cluster removed from the codebook."""

    cluster_id: int
    arm: str
    reason: str
    cluster_label: str
    member_feature_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "arm": self.arm,
            "reason": self.reason,
            "cluster_label": self.cluster_label,
            "member_feature_ids": list(self.member_feature_ids),
        }


@dataclass(frozen=True)
class ArmClusterRecord:
    """One labeled HDBSCAN cluster with member feature rows."""

    cluster_id: int
    cluster_label: str
    definition: str
    n_members: int
    members: tuple[dict[str, Any], ...]
    arm: str
    seed: int


@dataclass
class SynonymRow:
    """One confirmed merge row from feature_synonyms.csv."""

    feature_id_a: str
    feature_id_b: str
    merged_to: str
    confirmed_by: str
    confirmed_at: str
    notes: str


def cluster_seed_dir(normalize_embed_dir: Path, seed: int) -> Path:
    """Return the clusters_seed_<seed> directory under a normalize run."""
    name = constants.CLUSTER_SEED_DIR_TEMPLATE.format(seed=seed)
    return normalize_embed_dir / name


def select_primary_cluster_run(arm: str, normalize_embed_dir: Path) -> Path:
    """Pick the primary (seed 42) clusters directory when present.

    Parameters
    ----------
    arm
        Text arm name (unused; kept for API stability).
    normalize_embed_dir
        Normalize embed timestamp directory.

    Returns
    -------
    Path
        ``clusters_seed_42`` directory.

    Raises
    ------
    FileNotFoundError
        When the primary seed directory is missing.
    """
    _ = arm
    primary = cluster_seed_dir(normalize_embed_dir, constants.DEFAULT_SEED)
    if not primary.is_dir():
        raise FileNotFoundError(f"Missing primary cluster dir: {primary}")
    return primary


def latest_label_dir(clusters_run_dir: Path) -> Path:
    """Return the newest label timestamp directory under a cluster seed dir."""
    labels_parent = clusters_run_dir / "labels"
    return latest_timestamp_subdir(labels_parent)


def load_feature_records(normalize_embed_dir: Path) -> list[dict[str, Any]]:
    """Load features.jsonl records from a normalize embed directory."""
    jsonl_path = normalize_embed_dir / "features.jsonl"
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"Missing features.jsonl in {normalize_embed_dir}")
    return [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_arm_cluster_labels(
    arm: str,
    normalize_embed_dir: Path,
    seed: int,
) -> list[ClusterLabelResult]:
    """Load cluster label results from Step 4 label JSON artifacts.

    Parameters
    ----------
    arm
        Discovery text arm.
    normalize_embed_dir
        Normalize embed run directory.
    seed
        HDBSCAN cluster seed.

    Returns
    -------
    list[ClusterLabelResult]
        Parsed cluster labels sorted by ``cluster_id``.
    """
    clusters_dir = cluster_seed_dir(normalize_embed_dir, seed)
    label_dir = latest_label_dir(clusters_dir)
    results: list[ClusterLabelResult] = []
    for artifact in sorted(label_dir.glob("[0-9]*_*.json")):
        if artifact.name == constants.METADATA_FILENAME:
            continue
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        row = payload.get("cluster_label_row")
        if row is None:
            continue
        parsed = row["result"]
        if row.get("arm") != arm:
            continue
        results.append(
            ClusterLabelResult(
                cluster_id=int(parsed["cluster_id"]),
                cluster_label=str(parsed["cluster_label"]),
                definition=str(parsed["definition"]),
                salience_notes=str(parsed.get("salience_notes", "")),
            )
        )
    return sorted(results, key=lambda item: item.cluster_id)


def load_cluster_members(
    arm: str,
    normalize_embed_dir: Path,
    seed: int,
) -> list[ArmClusterRecord]:
    """Join cluster labels, assignments, and feature rows per cluster."""
    clusters_dir = cluster_seed_dir(normalize_embed_dir, seed)
    assignments = load_hdbscan_assignments(clusters_dir)
    records = load_feature_records(normalize_embed_dir)
    by_id = {record["feature_id"]: record for record in records}
    labels = load_arm_cluster_labels(arm, normalize_embed_dir, seed)
    label_rows = {label.cluster_id: label for label in labels}
    members_by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for feature_id, cluster_id in assignments.items():
        if cluster_id == constants.NOISE_CLUSTER_ID:
            continue
        record = by_id.get(feature_id)
        if record is None:
            raise KeyError(f"Unknown feature_id in assignments: {feature_id}")
        members_by_cluster[int(cluster_id)].append(record)
    clusters: list[ArmClusterRecord] = []
    for cluster_id, label in sorted(label_rows.items()):
        members = tuple(members_by_cluster.get(cluster_id, ()))
        n_members = len(members)
        clusters.append(
            ArmClusterRecord(
                cluster_id=cluster_id,
                cluster_label=label.cluster_label,
                definition=label.definition,
                n_members=n_members,
                members=tuple(members),
                arm=arm,
                seed=seed,
            )
        )
    return clusters


def compute_noise_share(assignments: dict[str, int]) -> float:
    """Return the fraction of features assigned to HDBSCAN noise."""
    if not assignments:
        return 0.0
    noise = sum(1 for cid in assignments.values() if cid == constants.NOISE_CLUSTER_ID)
    return noise / len(assignments)


def normalize_feature_name(label: str) -> str:
    """Normalize a cluster label to a 2–6 word lowercase interim name."""
    return interim_cluster_name(label)


def interim_cluster_name(label: str) -> str:
    """Build a provisional name from the cluster label without mid-phrase cuts."""
    words = label.strip().split()
    if not words:
        raise ValueError("cluster label is empty")
    if len(words) > constants.CODEBOOK_NAME_MAX_WORDS:
        words = words[: constants.CODEBOOK_NAME_MAX_WORDS]
    if len(words) < constants.CODEBOOK_NAME_MIN_WORDS:
        raise ValueError(
            f"cluster label must yield at least {constants.CODEBOOK_NAME_MIN_WORDS} words"
        )
    return " ".join(words).lower()


def validate_outcome_leakage(name: str, definition: str) -> None:
    """Raise when name or definition leaks moderation outcomes."""
    for field_name, text in (("name", name), ("definition", definition)):
        if _OUTCOME_LEAKAGE_RE.search(text):
            raise ValueError(f"Outcome leakage in {field_name}: {text!r}")
    if not definition.strip().lower().startswith(constants.DEFINITION_REQUIRED_PREFIX.lower()):
        raise ValueError(f"Definition must start with '{constants.DEFINITION_REQUIRED_PREFIX}'")


def is_topic_only_feature(
    definition: str,
    members: tuple[dict[str, Any], ...],
    name: str = "",
    cluster_label: str = "",
) -> bool:
    """Return True when a cluster is pure topic/subject with no rhetoric."""
    return topic_only_reason(definition, members, name, cluster_label) is not None


def topic_only_reason(
    definition: str,
    members: tuple[dict[str, Any], ...],
    name: str,
    cluster_label: str,
) -> str | None:
    """Return a drop reason when the feature is topic-only, else None."""
    combined = f"{name} {definition} {cluster_label}".lower()
    if members:
        categories = {str(record.get("category", "")) for record in members}
        non_topic = [cat for cat in categories if cat and cat != constants.TOPIC_ONLY_CATEGORY]
        if not non_topic and constants.TOPIC_ONLY_CATEGORY in categories:
            return "all_members_topic_subject"
    if _definition_is_pure_topic(definition):
        return "policy_domain_definition"
    if _TOPIC_STANCE_RE.search(combined) and not _members_have_rhetoric(members):
        return "party_or_ideological_target"
    for pattern in _TOPIC_POLICY_PHRASE_RES:
        if pattern.search(combined) and not _members_have_rhetoric(members):
            return f"policy_phrase:{pattern.pattern}"
    return None


def _members_have_rhetoric(members: tuple[dict[str, Any], ...]) -> bool:
    if not members:
        return False
    categories = {str(record.get("category", "")) for record in members}
    return bool(categories & _RHETORIC_MEMBER_CATEGORIES)


def _definition_is_pure_topic(definition: str) -> bool:
    if not _TOPIC_POLICY_RE.search(definition):
        return False
    rhetorical_cues = (
        "insult",
        "profan",
        "sarcas",
        "threat",
        "moderat",
        "tone",
        "argument",
        "rhetor",
        "framing",
        "call to action",
    )
    lowered = definition.lower()
    if any(cue in lowered for cue in rhetorical_cues):
        return False
    return bool(_PURE_TOPIC_DEF_RE.search(definition))


def select_example_posts(
    cluster: ArmClusterRecord,
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    arm: str,
    rng: np.random.Generator,
) -> tuple[tuple[PostExample, ...], tuple[PostExample, ...]]:
    """Pick positive and negative discovery-half examples for one cluster."""
    n_each = constants.CODEBOOK_EXAMPLES_PER_POLARITY
    member_post_ids = {str(record["message_id"]) for record in cluster.members}
    positives = _select_positive_examples(cluster, cohort, discovery_ids, arm, rng, n_each)
    negatives = _select_negative_examples(
        cohort,
        discovery_ids,
        member_post_ids,
        arm,
        rng,
        n_each,
    )
    return positives, negatives


def _select_positive_examples(
    cluster: ArmClusterRecord,
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    arm: str,
    rng: np.random.Generator,
    n_each: int,
) -> tuple[PostExample, ...]:
    ranked = sorted(
        cluster.members,
        key=lambda record: len(str(record.get("evidence_span") or "")),
        reverse=True,
    )
    chosen_posts: list[str] = []
    examples: list[PostExample] = []
    for record in ranked:
        post_id = str(record["message_id"])
        if post_id in chosen_posts or post_id not in discovery_ids:
            continue
        text = _post_text(cohort, post_id, arm)
        if not text:
            continue
        chosen_posts.append(post_id)
        examples.append(PostExample(post_id=post_id, text=text))
        if len(examples) >= n_each:
            break
    if len(examples) < n_each:
        examples.extend(
            _fill_examples_from_cohort(
                cohort,
                discovery_ids,
                arm,
                set(chosen_posts),
                n_each - len(examples),
                rng,
            )
        )
    return tuple(examples[:n_each])


def _select_negative_examples(
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    exclude_post_ids: set[str],
    arm: str,
    rng: np.random.Generator,
    n_each: int,
) -> tuple[PostExample, ...]:
    mask = (
        cohort["post_id"].astype(str).isin(discovery_ids)
        & cohort["split"].eq(constants.DISCOVERY_SPLIT)
        & ~cohort["post_id"].astype(str).isin(exclude_post_ids)
    )
    candidates = cohort.loc[mask, "post_id"].astype(str).tolist()
    if len(candidates) < n_each:
        raise ValueError("Not enough discovery negative example candidates")
    indices = rng.choice(len(candidates), size=n_each, replace=False)
    examples: list[PostExample] = []
    for index in indices:
        post_id = candidates[int(index)]
        text = _post_text(cohort, post_id, arm)
        examples.append(PostExample(post_id=post_id, text=text))
    return tuple(examples)


def _fill_examples_from_cohort(
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    arm: str,
    exclude: set[str],
    needed: int,
    rng: np.random.Generator,
) -> list[PostExample]:
    mask = (
        cohort["post_id"].astype(str).isin(discovery_ids)
        & cohort["split"].eq(constants.DISCOVERY_SPLIT)
        & ~cohort["post_id"].astype(str).isin(exclude)
    )
    candidates = cohort.loc[mask, "post_id"].astype(str).tolist()
    if len(candidates) < needed:
        raise ValueError("Not enough discovery posts for positive examples")
    indices = rng.choice(len(candidates), size=needed, replace=False)
    return [
        PostExample(
            post_id=candidates[int(index)],
            text=_post_text(cohort, candidates[int(index)], arm),
        )
        for index in indices
    ]


def _post_text(cohort: pd.DataFrame, post_id: str, arm: str) -> str:
    rows = cohort.loc[cohort["post_id"].astype(str) == post_id]
    if rows.empty:
        return ""
    return extract_arm_text(rows.iloc[0], arm)


def build_codebook_entry(
    cluster: ArmClusterRecord,
    feature_id: str,
    cohort: pd.DataFrame,
    discovery_ids: set[str],
    rng: np.random.Generator,
) -> CodebookFeature:
    """Build one codebook feature from a labeled cluster."""
    positives, negatives = select_example_posts(cluster, cohort, discovery_ids, cluster.arm, rng)
    source_ids = {arm: list(ids) for arm, ids in EMPTY_ARMS_TEMPLATE.items()}
    source_ids[cluster.arm] = [cluster.cluster_id]
    source_definition = cluster.definition.strip()
    return CodebookFeature(
        feature_id=feature_id,
        name=interim_cluster_name(cluster.cluster_label),
        definition=source_definition,
        positive_examples=positives,
        negative_examples=negatives,
        discovery_arm=cluster.arm,
        source_cluster_ids=source_ids,
        member_feature_ids=tuple(record["feature_id"] for record in cluster.members),
        cluster_size=cluster.n_members,
        source_cluster_label=cluster.cluster_label,
        source_definition=source_definition,
        member_records=cluster.members,
        part2_theme_id=None,
    )


def assign_feature_ids(features: list[CodebookFeature]) -> list[CodebookFeature]:
    """Assign sequential cb_NNN ids preserving order."""
    reassigned: list[CodebookFeature] = []
    for index, feature in enumerate(features, start=1):
        feature_id = f"{constants.CODEBOOK_FEATURE_ID_PREFIX}{index:03d}"
        reassigned.append(_with_feature_id(feature, feature_id))
    return reassigned


def _with_feature_id(feature: CodebookFeature, feature_id: str) -> CodebookFeature:
    return CodebookFeature(
        feature_id=feature_id,
        name=feature.name,
        definition=feature.definition,
        positive_examples=feature.positive_examples,
        negative_examples=feature.negative_examples,
        discovery_arm=feature.discovery_arm,
        source_cluster_ids=feature.source_cluster_ids,
        member_feature_ids=feature.member_feature_ids,
        cluster_size=feature.cluster_size,
        source_cluster_label=feature.source_cluster_label,
        source_definition=feature.source_definition,
        member_records=feature.member_records,
        part2_theme_id=feature.part2_theme_id,
    )


def rewrite_codebook_features_with_llm(
    features: list[CodebookFeature],
    output_dir: Path,
) -> dict[str, CodebookRewriteBatch]:
    """Rewrite names/definitions in batches via llm_client."""
    output_dir.mkdir(parents=True, exist_ok=True)
    run_metadata = {
        "model": constants.LLM_MODEL_ID,
        "reasoning_effort": constants.LLM_REASONING_EFFORT,
        "stage": constants.STAGE_CODEBOOK_REWRITE,
        "litellm_model": constants.LLM_LITELLM_MODEL_ID,
    }
    batches: dict[str, CodebookRewriteBatch] = {}
    batch_size = constants.CODEBOOK_REWRITE_BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(features), batch_size)):
        chunk = features[start : start + batch_size]
        payload = [
            {
                "feature_id": feature.feature_id,
                "source_cluster_label": feature.source_cluster_label,
                "source_definition": feature.source_definition,
                "interim_name": feature.name,
            }
            for feature in chunk
        ]
        messages = build_codebook_rewrite_messages(payload)
        parsed = llm_client.complete_structured(
            messages,
            CodebookRewriteBatch,
            stage=constants.STAGE_CODEBOOK_REWRITE,
            arm=None,
            call_index=batch_index,
            output_dir=output_dir,
            run_metadata=run_metadata,
        )
        batches[f"batch_{batch_index}"] = parsed
    return batches


def apply_codebook_rewrites(
    features: list[CodebookFeature],
    rewrite_batches: dict[str, CodebookRewriteBatch],
) -> tuple[list[CodebookFeature], list[DroppedFeature]]:
    """Apply LLM rewrites and drop topic-only features flagged by LLM or rules."""
    rewrite_by_id = _flatten_rewrite_items(rewrite_batches)
    kept: list[CodebookFeature] = []
    dropped: list[DroppedFeature] = []
    for feature in features:
        rewrite = rewrite_by_id.get(feature.feature_id)
        if rewrite is None:
            raise KeyError(f"Missing rewrite for {feature.feature_id}")
        members = _members_for_feature(feature)
        drop_reason = _rewrite_drop_reason(rewrite, feature, members)
        if drop_reason:
            dropped.append(_dropped_from_feature(feature, drop_reason))
            continue
        validate_outcome_leakage(rewrite.name.strip().lower(), rewrite.definition.strip())
        updated = _with_feature_id(
            CodebookFeature(
                feature_id=feature.feature_id,
                name=rewrite.name.strip().lower(),
                definition=rewrite.definition.strip(),
                positive_examples=feature.positive_examples,
                negative_examples=feature.negative_examples,
                discovery_arm=feature.discovery_arm,
                source_cluster_ids=feature.source_cluster_ids,
                member_feature_ids=feature.member_feature_ids,
                cluster_size=feature.cluster_size,
                source_cluster_label=feature.source_cluster_label,
                source_definition=feature.source_definition,
                member_records=feature.member_records,
                part2_theme_id=feature.part2_theme_id,
            ),
            feature.feature_id,
        )
        kept.append(updated)
    return kept, dropped


def _flatten_rewrite_items(
    rewrite_batches: dict[str, CodebookRewriteBatch],
) -> dict[str, Any]:
    by_id: dict[str, Any] = {}
    for batch in rewrite_batches.values():
        for item in batch.items:
            by_id[item.feature_id] = item
    return by_id


def _members_for_feature(feature: CodebookFeature) -> tuple[dict[str, Any], ...]:
    return feature.member_records


def _rewrite_drop_reason(rewrite: Any, feature: CodebookFeature, members: tuple) -> str | None:
    if rewrite.is_topic_only:
        return f"topic_only_llm:{rewrite.topic_only_reason or 'flagged'}"
    heuristic = topic_only_reason(
        rewrite.definition,
        members,
        rewrite.name,
        feature.source_cluster_label,
    )
    if heuristic:
        return f"topic_only_heuristic:{heuristic}"
    return None


def _dropped_from_feature(feature: CodebookFeature, reason: str) -> DroppedFeature:
    cluster_id = feature.source_cluster_ids[feature.discovery_arm][0]
    return DroppedFeature(
        cluster_id=cluster_id,
        arm=feature.discovery_arm,
        reason=reason,
        cluster_label=feature.source_cluster_label,
        member_feature_ids=feature.member_feature_ids,
    )


def embed_codebook_texts(features: tuple[CodebookFeature, ...]) -> np.ndarray:
    """Embed name+definition strings with Titan (256-d, L2-normalized)."""
    vectors: list[list[float]] = []
    for feature in features:
        text = f"{feature.name}. {feature.definition}"
        response = create_embedding(text, normalize=constants.EMBEDDING_NORMALIZE)
        vectors.append(response["embedding"])
    return np.asarray(vectors, dtype=np.float32)


@dataclass(frozen=True)
class MergeCandidateGroup:
    """One proposed merge group at or above the strong cosine threshold."""

    group_id: int
    feature_ids: tuple[str, ...]
    names: tuple[str, ...]
    arms: tuple[str, ...]
    min_cosine: float


def compute_merge_candidates(
    features: tuple[CodebookFeature, ...],
    matrix: np.ndarray,
) -> tuple[tuple[MergeCandidateGroup, ...], list[tuple[str, str, float]]]:
    """Return strong merge groups and borderline feature pairs."""
    ids = [feature.feature_id for feature in features]
    if len(ids) < 2:
        return (), []
    scores = cosine_similarity(matrix)
    strong_edges = _edges_above(scores, ids, constants.CODEBOOK_MERGE_SIMILARITY_THRESHOLD)
    groups = _connected_components(features, strong_edges)
    borderline = _borderline_pairs(scores, ids)
    return groups, borderline


def _edges_above(
    scores: np.ndarray,
    ids: list[str],
    threshold: float,
) -> list[tuple[str, str, float]]:
    edges: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            score = float(scores[i, j])
            if score >= threshold:
                edges.append((ids[i], ids[j], score))
    return edges


def _connected_components(
    features: tuple[CodebookFeature, ...],
    edges: list[tuple[str, str, float]],
) -> tuple[MergeCandidateGroup, ...]:
    ids = [feature.feature_id for feature in features]
    by_id = {feature.feature_id: feature for feature in features}
    parent = {feature_id: feature_id for feature_id in ids}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left, right, _score in edges:
        union(left, right)
    components: dict[str, list[str]] = defaultdict(list)
    for feature_id in ids:
        components[find(feature_id)].append(feature_id)
    groups: list[MergeCandidateGroup] = []
    group_index = 1
    for members in sorted(components.values(), key=lambda group: group[0]):
        if len(members) < 2:
            continue
        edge_scores = [
            score
            for left, right, score in edges
            if left in members and right in members
        ]
        groups.append(
            MergeCandidateGroup(
                group_id=group_index,
                feature_ids=tuple(sorted(members)),
                names=tuple(by_id[mid].name for mid in sorted(members)),
                arms=tuple(by_id[mid].discovery_arm for mid in sorted(members)),
                min_cosine=min(edge_scores) if edge_scores else 1.0,
            )
        )
        group_index += 1
    return tuple(groups)


def _borderline_pairs(
    scores: np.ndarray,
    ids: list[str],
) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    low = constants.MERGE_BORDERLINE_MIN_COSINE
    high = constants.CODEBOOK_MERGE_SIMILARITY_THRESHOLD
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            score = float(scores[i, j])
            if low <= score < high:
                pairs.append((ids[i], ids[j], score))
    return pairs


def merge_codebook_entries(
    draft: CodebookDraft,
    synonyms: tuple[SynonymRow, ...],
) -> CodebookDraft:
    """Return the draft unchanged when no synonym rows are provided."""
    if not synonyms:
        return draft
    return apply_synonym_merges(draft, synonyms)


def load_synonym_rows(synonyms_path: Path) -> tuple[SynonymRow, ...]:
    """Load confirmed synonym merge rows from CSV."""
    if not synonyms_path.is_file():
        return ()
    with synonyms_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[SynonymRow] = []
        for raw in reader:
            if not raw.get("feature_id_a"):
                continue
            rows.append(
                SynonymRow(
                    feature_id_a=str(raw["feature_id_a"]),
                    feature_id_b=str(raw["feature_id_b"]),
                    merged_to=str(raw["merged_to"]),
                    confirmed_by=str(raw.get("confirmed_by", "")),
                    confirmed_at=str(raw.get("confirmed_at", "")),
                    notes=str(raw.get("notes", "")),
                )
            )
        return tuple(rows)


def apply_synonym_merges(
    draft: CodebookDraft,
    synonyms: Path | tuple[SynonymRow, ...],
) -> CodebookDraft:
    """Apply human-confirmed merges from CSV rows."""
    rows = load_synonym_rows(synonyms) if isinstance(synonyms, Path) else synonyms
    if not rows:
        return draft
    by_id = {feature.feature_id: feature for feature in draft.features}
    for row in rows:
        survivor_id = row.merged_to
        other_ids = {row.feature_id_a, row.feature_id_b} - {survivor_id}
        survivor = by_id.get(survivor_id)
        if survivor is None:
            continue
        merged_sources = _merge_source_cluster_maps(survivor, other_ids, by_id)
        merged_members = _merge_member_ids(survivor, other_ids, by_id)
        by_id[survivor_id] = CodebookFeature(
            feature_id=survivor.feature_id,
            name=survivor.name,
            definition=survivor.definition,
            positive_examples=survivor.positive_examples,
            negative_examples=survivor.negative_examples,
            discovery_arm=survivor.discovery_arm,
            source_cluster_ids=merged_sources,
            member_feature_ids=merged_members,
            cluster_size=survivor.cluster_size,
            source_cluster_label=survivor.source_cluster_label,
            source_definition=survivor.source_definition,
            member_records=survivor.member_records,
            part2_theme_id=survivor.part2_theme_id,
        )
        for other_id in other_ids:
            by_id.pop(other_id, None)
    remaining = assign_feature_ids(list(by_id.values()))
    return CodebookDraft(version=draft.version, features=tuple(remaining))


def _merge_source_cluster_maps(
    survivor: CodebookFeature,
    other_ids: set[str],
    by_id: dict[str, CodebookFeature],
) -> dict[str, list[int]]:
    merged = {arm: list(ids) for arm, ids in survivor.source_cluster_ids.items()}
    for other_id in other_ids:
        other = by_id.get(other_id)
        if other is None:
            continue
        for arm, ids in other.source_cluster_ids.items():
            merged[arm] = sorted(set(merged[arm]) | set(ids))
    return merged


def _merge_member_ids(
    survivor: CodebookFeature,
    other_ids: set[str],
    by_id: dict[str, CodebookFeature],
) -> tuple[str, ...]:
    members = set(survivor.member_feature_ids)
    for other_id in other_ids:
        other = by_id.get(other_id)
        if other is None:
            continue
        members.update(other.member_feature_ids)
    return tuple(sorted(members))


def write_operationalize_export(
    arm: str,
    normalize_embed_dir: Path,
    label_dir: Path,
    clusters: list[ArmClusterRecord],
    run_dir: Path,
    built_at: str,
) -> None:
    """Write per-arm clusters.jsonl and metadata.json."""
    run_dir.mkdir(parents=True, exist_ok=True)
    clusters_path = run_dir / constants.OPERATIONALIZE_CLUSTERS_FILENAME
    with clusters_path.open("w", encoding="utf-8") as handle:
        for cluster in clusters:
            row = {
                "cluster_id": cluster.cluster_id,
                "name": normalize_feature_name(cluster.cluster_label),
                "definition": cluster.definition,
                "n_members": cluster.n_members,
                "member_feature_ids": [record["feature_id"] for record in cluster.members],
                "seed": cluster.seed,
            }
            handle.write(json.dumps(row) + "\n")
    metadata = {
        "arm": arm,
        "normalize_embed_dir": str(normalize_embed_dir.relative_to(paths.EXPERIMENT_ROOT)),
        "label_timestamp_dir": str(label_dir.relative_to(paths.EXPERIMENT_ROOT)),
        "seed": constants.DEFAULT_SEED,
        "built_at": built_at,
    }
    (run_dir / constants.METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def write_codebook_markdown(
    draft: CodebookDraft,
    output_path: Path,
    merge_groups: tuple[MergeCandidateGroup, ...],
) -> None:
    """Write a human-readable markdown summary of the draft codebook."""
    lines = [f"# Codebook draft {draft.version}", ""]
    for feature in draft.features:
        lines.append(f"## {feature.feature_id}: {feature.name}")
        lines.append(feature.definition)
        lines.append("")
        lines.append(f"- Arm: {feature.discovery_arm}")
        lines.append(f"- Cluster size: {feature.cluster_size}")
        lines.append("")
    lines.append("## Proposed merges")
    lines.append("")
    if not merge_groups:
        lines.append("_No strong merge groups (cosine >= 0.85)._")
    else:
        for group in merge_groups:
            names = ", ".join(group.names)
            lines.append(f"- Group {group.group_id}: {names}")
    lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_merge_candidates_csv(
    run_dir: Path,
    groups: tuple[MergeCandidateGroup, ...],
    borderline: list[tuple[str, str, float]],
    features: tuple[CodebookFeature, ...],
) -> None:
    """Write merge_candidates.csv with strong groups and borderline pairs."""
    by_id = {feature.feature_id: feature for feature in features}
    path = run_dir / constants.MERGE_CANDIDATES_FILENAME
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["tier", "group_id", "feature_ids", "names", "arms", "cosine"],
        )
        for group in groups:
            writer.writerow(
                [
                    "strong_group",
                    group.group_id,
                    ";".join(group.feature_ids),
                    ";".join(group.names),
                    ";".join(group.arms),
                    f"{group.min_cosine:.4f}",
                ]
            )
        for left, right, score in borderline:
            names = f"{by_id[left].name};{by_id[right].name}"
            arms = f"{by_id[left].discovery_arm};{by_id[right].discovery_arm}"
            writer.writerow(
                ["borderline_pair", "", f"{left};{right}", names, arms, f"{score:.4f}"],
            )


def count_features_after_strong_merges(
    n_features: int,
    groups: tuple[MergeCandidateGroup, ...],
) -> int:
    """Return feature count if every strong merge group were collapsed."""
    removed = sum(len(group.feature_ids) - 1 for group in groups)
    return n_features - removed


def write_draft_codebook(
    draft: CodebookDraft,
    dropped: tuple[DroppedFeature, ...],
    metadata: dict[str, Any],
    output_root: Path,
    merge_groups: tuple[MergeCandidateGroup, ...],
    borderline_pairs: list[tuple[str, str, float]],
) -> Path:
    """Write draft codebook artifacts under outputs/shared/codebook/."""
    run_dir = output_root / f"{constants.CODEBOOK_DRAFT_DIR_PREFIX}{draft.version}"
    run_dir.mkdir(parents=True, exist_ok=True)
    codebook_path = run_dir / constants.CODEBOOK_JSON_FILENAME
    codebook_path.write_text(json.dumps(draft.to_dict(), indent=2) + "\n", encoding="utf-8")
    dropped_path = run_dir / constants.DROPPED_FEATURES_FILENAME
    dropped_path.write_text(
        json.dumps({"dropped": [row.to_dict() for row in dropped]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / constants.METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    write_merge_candidates_csv(run_dir, merge_groups, borderline_pairs, draft.features)
    write_codebook_markdown(draft, run_dir / constants.CODEBOOK_MD_FILENAME, merge_groups)
    return run_dir


def approve_codebook(draft_codebook_path: Path, approved_by: str) -> Path:
    """Copy an approved draft into approved_<timestamp> with approval.json."""
    if not draft_codebook_path.is_file():
        raise FileNotFoundError(draft_codebook_path)
    draft_dir = draft_codebook_path.parent
    version = json.loads(draft_codebook_path.read_text(encoding="utf-8"))["version"]
    approved_at = make_run_timestamp()
    approved_dir = paths.codebook_dir() / f"{constants.CODEBOOK_APPROVED_DIR_PREFIX}{approved_at}"
    approved_dir.mkdir(parents=True, exist_ok=True)
    approved_codebook = approved_dir / constants.CODEBOOK_JSON_FILENAME
    approved_codebook.write_text(draft_codebook_path.read_text(encoding="utf-8"), encoding="utf-8")
    approval = {
        "approved_by": approved_by,
        "approved_at": approved_at,
        "codebook_version": version,
    }
    (approved_dir / constants.APPROVAL_JSON_FILENAME).write_text(
        json.dumps(approval, indent=2) + "\n",
        encoding="utf-8",
    )
    return approved_dir


def suggest_merge_pairs(draft: CodebookDraft) -> list[tuple[str, str, float]]:
    """Return feature-id pairs whose name+definition TF-IDF cosine exceeds threshold."""
    texts = [f"{feature.name} {feature.definition}" for feature in draft.features]
    ids = [feature.feature_id for feature in draft.features]
    if len(texts) < 2:
        return []
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(texts)
    scores = cosine_similarity(matrix)
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            score = float(scores[i, j])
            if score >= constants.CODEBOOK_MERGE_SIMILARITY_THRESHOLD:
                pairs.append((ids[i], ids[j], score))
    return pairs


def build_draft_from_arms(
    seeds: tuple[int, ...],
    normalize_dirs: dict[str, Path] | None,
) -> tuple[
    CodebookDraft,
    tuple[DroppedFeature, ...],
    dict[str, Any],
    tuple[MergeCandidateGroup, ...],
    list[tuple[str, str, float]],
]:
    """Build draft codebook features from all text arms."""
    discovery_ids = load_discovery_post_ids(DISCOVERY_IDS_PATH)
    built_at = make_run_timestamp()
    rng = np.random.default_rng(constants.DEFAULT_SEED)
    features: list[CodebookFeature] = []
    dropped: list[DroppedFeature] = []
    noise_by_arm: dict[str, dict[str, float]] = {}
    for arm in constants.TEXT_ARMS:
        normalize_dir = _resolve_normalize_dir(arm, normalize_dirs)
        cohort_dir = paths.latest_cohort_run_dir(arm, constants.PARTICIPANT_FILTER_ALL)
        cohort = pd.read_parquet(cohort_dir / constants.COHORT_FILENAME)
        clusters_dir = select_primary_cluster_run(arm, normalize_dir)
        label_dir = latest_label_dir(clusters_dir)
        clusters = load_cluster_members(arm, normalize_dir, constants.DEFAULT_SEED)
        op_dir = paths.operationalize_dir(arm) / built_at
        write_operationalize_export(arm, normalize_dir, label_dir, clusters, op_dir, built_at)
        noise_by_arm[arm] = _noise_shares_for_seeds(normalize_dir, seeds)
        for cluster in clusters:
            interim_name = interim_cluster_name(cluster.cluster_label)
            drop_reason = topic_only_reason(
                cluster.definition,
                cluster.members,
                interim_name,
                cluster.cluster_label,
            )
            if drop_reason:
                dropped.append(
                    DroppedFeature(
                        cluster_id=cluster.cluster_id,
                        arm=arm,
                        reason=f"{DROP_REASON_TOPIC_ONLY}:{drop_reason}",
                        cluster_label=cluster.cluster_label,
                        member_feature_ids=tuple(r["feature_id"] for r in cluster.members),
                    )
                )
                continue
            feature_id = f"{constants.CODEBOOK_FEATURE_ID_PREFIX}000"
            features.append(
                build_codebook_entry(cluster, feature_id, cohort, discovery_ids, rng)
            )
        print(
            f"arm={arm} seed={constants.DEFAULT_SEED} clusters={len(clusters)}"
        )
    features = assign_feature_ids(features)
    rewrite_dir = paths.codebook_dir() / f"rewrite_{built_at}"
    rewrite_batches = rewrite_codebook_features_with_llm(features, rewrite_dir)
    features, rewrite_drops = apply_codebook_rewrites(features, rewrite_batches)
    dropped.extend(rewrite_drops)
    features = assign_feature_ids(features)
    for feature in features:
        validate_outcome_leakage(feature.name, feature.definition)
    synonyms = load_synonym_rows(SYNONYMS_PATH)
    draft = CodebookDraft(version=built_at, features=tuple(features))
    draft = merge_codebook_entries(draft, synonyms)
    matrix = embed_codebook_texts(draft.features)
    merge_groups, borderline = compute_merge_candidates(draft.features, matrix)
    metadata = {
        "built_at": built_at,
        "seeds": list(seeds),
        "hdbscan_noise_share_by_arm": noise_by_arm,
        "merge_strong_groups": len(merge_groups),
        "features_if_strong_merges": count_features_after_strong_merges(
            len(draft.features),
            merge_groups,
        ),
    }
    print(f"topic_only_dropped={len(dropped)}")
    print(f"draft_features={len(draft.features)}")
    print(f"arms_merged={len(constants.TEXT_ARMS)}")
    return draft, tuple(dropped), metadata, merge_groups, borderline


def _noise_shares_for_seeds(normalize_dir: Path, seeds: tuple[int, ...]) -> dict[str, float]:
    shares: dict[str, float] = {}
    for seed in seeds:
        clusters_dir = cluster_seed_dir(normalize_dir, seed)
        if not clusters_dir.is_dir():
            raise FileNotFoundError(f"Missing clusters dir for seed {seed}: {clusters_dir}")
        assignments = load_hdbscan_assignments(clusters_dir)
        shares[f"seed_{seed}"] = compute_noise_share(assignments)
    return shares


def _resolve_local_codebook_path(raw_path: Path) -> Path:
    if raw_path.is_absolute():
        return raw_path
    from_experiment = paths.EXPERIMENT_ROOT / raw_path
    if from_experiment.is_file():
        return from_experiment
    if raw_path.is_file():
        return raw_path
    return from_experiment


def _resolve_normalize_dir(arm: str, normalize_dirs: dict[str, Path] | None) -> Path:
    if normalize_dirs and arm in normalize_dirs:
        return normalize_dirs[arm]
    return latest_timestamp_subdir(paths.normalize_run_dir(arm))


def gate_b_approved_groups() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return user-approved Gate B merge groups as (canonical_key, member names)."""
    return (
        ("emphatic typography", (
            "emphatic capitalization", "emphatic capitalization",
            "emphatic punctuation and formatting", "typographic emphasis",
            "emphatic all caps", "emphatic heated rhetoric",
        )),
        ("political insults", (
            "political insults and mockery", "political insults and mockery",
            "political derogatory language", "direct political insults",
            "insults and derogatory labels",
        )),
        ("sarcasm and mockery", (
            "political sarcasm and irony", "political ridicule and mockery",
            "sarcastic political mockery", "political sarcasm and mockery",
        )),
        ("criticism of political actors", (
            "political actor criticism", "criticism of political actors",
            "partisan political criticism", "hostile political criticism",
        )),
        ("persuasive argumentation", (
            "persuasive argumentation", "political persuasion",
            "political argumentation and advocacy",
        )),
        ("qualified claims", (
            "qualified and tentative claims", "qualified claims",
            "qualified or tentative stances",
        )),
        ("unqualified claims as fact", (
            "unqualified political claims", "assertive political claims",
            "political claims stated as fact",
        )),
        ("conditional reasoning", (
            "conditional if-then claims", "conditional consequences",
            "conditional reasoning",
        )),
        ("quoted or attributed speech", (
            "quoted claims and responses", "attributed political claims",
            "quoted or attributed speech",
        )),
        ("lists", (
            "lists and enumerations", "enumerated political claims",
            "lists of related points",
        )),
        ("parallel repetition", (
            "emphatic parallel denunciation", "parallel condemnations",
            "repetitive parallel emphasis",
        )),
        ("contrastive framing", (
            "contrastive argumentation", "contrastive framing",
            "contrastive framing and rebuttal",
        )),
        ("rhetorical questions", (
            "challenging rhetorical questions", "pointed political questions",
            "pointed rhetorical questions",
        )),
        ("conspiracy claims", (
            "unsupported conspiracy claims", "conspiratorial political claims",
            "political conspiracy allegations",
        )),
        ("anti-elite framing", (
            "elite self-interest criticism", "populist anti-elite framing",
            "elite versus ordinary people",
        )),
        ("persecution framing", (
            "group persecution framing", "political persecution claims",
            "political persecution framing",
        )),
        ("us versus them", (
            "hostile group division", "partisan us versus them", "partisan us versus them",
        )),
        ("causal claims", (
            "explicit causal attribution", "political causal claims", "political causal claims",
        )),
        ("moral condemnation", (
            "explicit moral judgment", "moralized political condemnation",
            "moral condemnation of politics",
        )),
        ("political outrage", (
            "emphatic political outrage", "emphatic political outrage", "emphatic political outrage",
        )),
        ("calls to action", (
            "civic action appeals", "political action appeals", "political calls to action",
        )),
        ("profane insults", (
            "profane political insults", "profane political insults",
            "political profanity and insults",
        )),
        ("slang and colloquial insults", (
            "informal slang and colloquial language", "colloquial insults",
            "informal slang and insults",
        )),
        ("partisan left-right framing", (
            "partisan political framing", "partisan left right framing",
        )),
        ("hashtags and mentions", (
            "hashtags and account mentions", "political hashtags",
        )),
        ("confrontational direct address", (
            "confrontational direct address", "confrontational direct address",
        )),
        ("direct second-person address (neutral)", ("direct second-person address",)),
        ("personal political distress", ("personal political distress",)),
        ("violent political rhetoric", ("violent political rhetoric",)),
        ("specific policy advocacy", ("specific policy advocacy",)),
    )


GATE_B_DROP_FEATURE_NAME = "criticism of democrats and left"
GATE_B_DROP_REASON = (
    "gate_b_drop:one-sided stance-specific; mirror flip confounds Q2/Q3"
)


def assign_gate_b_member_ids(
    features: list[dict[str, Any]],
) -> tuple[list[tuple[str, tuple[str, ...]]], str, dict[str, dict[str, Any]]]:
    """Map draft features to Gate B groups; return groups, drop_id, by_id."""
    pools: dict[str, list[str]] = {}
    by_id = {feature["feature_id"]: feature for feature in features}
    for feature in features:
        pools.setdefault(feature["name"], []).append(feature["feature_id"])
    grouped: list[tuple[str, tuple[str, ...]]] = []
    mapped: set[str] = set()
    for group_key, names in gate_b_approved_groups():
        member_ids: list[str] = []
        for name in names:
            if not pools.get(name):
                raise ValueError(f"Gate B mapping missing draft feature name: {name}")
            member_ids.append(pools[name].pop(0))
        grouped.append((group_key, tuple(member_ids)))
        mapped.update(member_ids)
    if not pools.get(GATE_B_DROP_FEATURE_NAME) or len(pools[GATE_B_DROP_FEATURE_NAME]) != 1:
        raise ValueError(f"Expected exactly one drop feature: {GATE_B_DROP_FEATURE_NAME}")
    drop_id = pools[GATE_B_DROP_FEATURE_NAME].pop(0)
    mapped.add(drop_id)
    leftover = {name: ids for name, ids in pools.items() if ids}
    if leftover:
        raise ValueError(f"Unmapped draft features remain: {leftover}")
    if len(mapped) != len(features):
        raise ValueError(f"Mapped {len(mapped)} of {len(features)} draft features")
    return grouped, drop_id, by_id


def write_gate_b_synonym_csv(
    grouped: list[tuple[str, tuple[str, ...]]],
    canonical_ids: dict[str, str],
    confirmed_at: str,
) -> None:
    """Write feature_synonyms.csv for all Gate B merges."""
    rows: list[list[str]] = []
    for group_key, member_ids in grouped:
        canonical_id = canonical_ids[group_key]
        survivor_draft_id = member_ids[0]
        for member_id in member_ids[1:]:
            rows.append(
                [
                    member_id,
                    survivor_draft_id,
                    canonical_id,
                    constants.GATE_B_APPROVED_BY,
                    confirmed_at,
                    group_key,
                ]
            )
    with SYNONYMS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "feature_id_a",
                "feature_id_b",
                "merged_to",
                "confirmed_by",
                "confirmed_at",
                "notes",
            ]
        )
        for row in rows:
            writer.writerow(row)


def _merge_example_lists(
    members: list[dict[str, Any]],
    field: str,
    limit: int,
    exclude_post_ids: set[str] | None = None,
) -> tuple[PostExample, ...]:
    exclude = exclude_post_ids or set()
    chosen: list[PostExample] = []
    seen: set[str] = set()
    for member in members:
        for raw in member.get(field, []):
            post_id = str(raw["post_id"])
            if post_id in seen or post_id in exclude:
                continue
            seen.add(post_id)
            chosen.append(PostExample(post_id=post_id, text=str(raw["text"])))
            if len(chosen) >= limit:
                return tuple(chosen)
    if len(chosen) < limit:
        raise ValueError(f"Not enough {field} examples after merge")
    return tuple(chosen)


def _merge_group_feature_dict(
    group_key: str,
    member_ids: tuple[str, ...],
    by_id: dict[str, dict[str, Any]],
    rewrite_name: str,
    rewrite_definition: str,
    new_feature_id: str,
) -> dict[str, Any]:
    members = [by_id[member_id] for member_id in member_ids]
    source_cluster_ids = {arm: [] for arm in constants.TEXT_ARMS}
    member_feature_ids: list[str] = []
    cluster_size = 0
    arms: set[str] = set()
    for member in members:
        arms.add(str(member["discovery_arm"]))
        cluster_size += int(member.get("cluster_size", 0))
        member_feature_ids.extend(member.get("member_feature_ids", []))
        for arm, ids in member.get("source_cluster_ids", {}).items():
            source_cluster_ids[arm] = sorted(set(source_cluster_ids[arm]) | set(ids))
    positives = _merge_example_lists(members, "positive_examples", constants.CODEBOOK_EXAMPLES_PER_POLARITY)
    positive_posts = {example.post_id for example in positives}
    negatives = _merge_example_lists(
        members,
        "negative_examples",
        constants.CODEBOOK_EXAMPLES_PER_POLARITY,
        exclude_post_ids=positive_posts,
    )
    discovery_arms = tuple(sorted(arms))
    return {
        "feature_id": new_feature_id,
        "name": rewrite_name.strip().lower(),
        "definition": rewrite_definition.strip(),
        "source_cluster_label": group_key,
        "source_definition": "; ".join(
            member.get("source_definition", member.get("definition", "")) for member in members
        )[:500],
        "positive_examples": [example.to_dict() for example in positives],
        "negative_examples": [example.to_dict() for example in negatives],
        "discovery_arm": discovery_arms[0],
        "discovery_arms": list(discovery_arms),
        "source_cluster_ids": source_cluster_ids,
        "member_feature_ids": sorted(set(member_feature_ids)),
        "merged_source_feature_ids": list(member_ids),
        "cluster_size": cluster_size,
        "part2_theme_id": None,
    }


def rewrite_gate_b_groups_with_llm(
    grouped: list[tuple[str, tuple[str, ...]]],
    by_id: dict[str, dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    """LLM rewrite for merged Gate B groups (batched)."""
    payload: list[dict[str, Any]] = []
    for index, (group_key, member_ids) in enumerate(grouped, start=1):
        members = [by_id[member_id] for member_id in member_ids]
        payload.append(
            {
                "feature_id": f"grp_{index:02d}",
                "source_cluster_label": group_key,
                "source_definition": "\n".join(
                    f"- {member['name']}: {member['definition']}" for member in members
                ),
                "interim_name": group_key,
            }
        )
    features_for_rewrite = payload
    output_dir.mkdir(parents=True, exist_ok=True)
    run_metadata = {
        "model": constants.LLM_MODEL_ID,
        "reasoning_effort": constants.LLM_REASONING_EFFORT,
        "stage": constants.STAGE_CODEBOOK_REWRITE,
        "litellm_model": constants.LLM_LITELLM_MODEL_ID,
        "gate_b": True,
    }
    rewrite_by_grp: dict[str, Any] = {}
    batch_size = constants.CODEBOOK_REWRITE_BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(features_for_rewrite), batch_size)):
        chunk = features_for_rewrite[start : start + batch_size]
        messages = build_codebook_rewrite_messages(chunk)
        parsed = llm_client.complete_structured(
            messages,
            CodebookRewriteBatch,
            stage=constants.STAGE_CODEBOOK_REWRITE,
            arm=None,
            call_index=batch_index,
            output_dir=output_dir,
            run_metadata=run_metadata,
        )
        for item in parsed.items:
            rewrite_by_grp[item.feature_id] = item
    return rewrite_by_grp


def finalize_gate_b_codebook(
    draft_codebook_path: Path,
    approved_by: str,
) -> tuple[Path, Path]:
    """Build final merged codebook, approve it, and return final and approved dirs."""
    draft_codebook_path = _resolve_local_codebook_path(draft_codebook_path)
    draft_payload = json.loads(draft_codebook_path.read_text(encoding="utf-8"))
    draft_version = draft_payload["version"]
    features = draft_payload["features"]
    grouped, drop_id, by_id = assign_gate_b_member_ids(features)
    confirmed_at = make_run_timestamp()
    final_version = confirmed_at
    canonical_ids = {
        group_key: f"{constants.CODEBOOK_FEATURE_ID_PREFIX}{index:03d}"
        for index, (group_key, _) in enumerate(grouped, start=1)
    }
    write_gate_b_synonym_csv(grouped, canonical_ids, confirmed_at)
    rewrite_dir = paths.codebook_dir() / f"rewrite_gate_b_{final_version}"
    rewrite_by_grp = rewrite_gate_b_groups_with_llm(grouped, by_id, rewrite_dir)
    final_features: list[dict[str, Any]] = []
    for index, (group_key, member_ids) in enumerate(grouped, start=1):
        rewrite = rewrite_by_grp[f"grp_{index:02d}"]
        validate_outcome_leakage(rewrite.name, rewrite.definition)
        final_features.append(
            _merge_group_feature_dict(
                group_key,
                member_ids,
                by_id,
                rewrite.name,
                rewrite.definition,
                canonical_ids[group_key],
            )
        )
    drop_feature = by_id[drop_id]
    draft_dropped_path = draft_codebook_path.parent / constants.DROPPED_FEATURES_FILENAME
    prior_dropped: list[dict[str, Any]] = []
    if draft_dropped_path.is_file():
        prior_dropped = json.loads(draft_dropped_path.read_text())["dropped"]
    gate_b_drop = {
        "feature_id": drop_id,
        "cluster_id": drop_feature["source_cluster_ids"][drop_feature["discovery_arm"]][0],
        "arm": drop_feature["discovery_arm"],
        "reason": GATE_B_DROP_REASON,
        "cluster_label": drop_feature["name"],
        "member_feature_ids": drop_feature.get("member_feature_ids", []),
    }
    dropped_all = prior_dropped + [gate_b_drop]
    final_dir = paths.codebook_dir() / f"{constants.CODEBOOK_FINAL_DIR_PREFIX}{final_version}"
    final_dir.mkdir(parents=True, exist_ok=True)
    codebook_payload = {"version": final_version, "features": final_features}
    (final_dir / constants.CODEBOOK_JSON_FILENAME).write_text(
        json.dumps(codebook_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (final_dir / constants.DROPPED_FEATURES_FILENAME).write_text(
        json.dumps({"dropped": dropped_all}, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "built_at": final_version,
        "source_draft": str(
            draft_codebook_path.resolve().relative_to(paths.EXPERIMENT_ROOT.resolve())
        ),
        "source_draft_version": draft_version,
        "gate_b_groups": len(grouped),
        "gate_b_approved_by": approved_by,
    }
    (final_dir / constants.METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    md_lines = [f"# Final codebook {final_version}", ""]
    for feature in final_features:
        md_lines.append(f"## {feature['feature_id']}: {feature['name']}")
        md_lines.append(feature["definition"])
        md_lines.append("")
    (final_dir / constants.CODEBOOK_MD_FILENAME).write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    approved_dir = approve_codebook(final_dir / constants.CODEBOOK_JSON_FILENAME, approved_by)
    print(f"final_features={len(final_features)}")
    print(f"Wrote {final_dir / constants.CODEBOOK_JSON_FILENAME}")
    print(f"Wrote {SYNONYMS_PATH}")
    return final_dir, approved_dir


def main(argv: list[str] | None = None) -> None:
    """CLI entry for draft build, merge suggestions, and approval."""
    parser = argparse.ArgumentParser(description="Build shared codebook from cluster labels.")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(constants.CLUSTER_SEEDS))
    parser.add_argument("--write-draft", action="store_true")
    parser.add_argument("--suggest-merges", action="store_true")
    parser.add_argument("--approve", type=Path, default=None)
    parser.add_argument("--approved-by", type=str, default=None)
    parser.add_argument("--finalize-gate-b", type=Path, default=None)
    args = parser.parse_args(argv)
    seeds = tuple(args.seeds)
    if args.finalize_gate_b is not None:
        approved_by = args.approved_by or constants.GATE_B_APPROVED_BY
        _final_dir, approved_dir = finalize_gate_b_codebook(args.finalize_gate_b, approved_by)
        print(f"Wrote {approved_dir / constants.APPROVAL_JSON_FILENAME}")
        return
    if args.approve is not None:
        if not args.approved_by:
            raise SystemExit("--approved-by is required with --approve")
        approved_dir = approve_codebook(args.approve, args.approved_by)
        print(f"Wrote {approved_dir / constants.CODEBOOK_JSON_FILENAME}")
        print(f"Wrote {approved_dir / constants.APPROVAL_JSON_FILENAME}")
        return
    if not args.write_draft and not args.suggest_merges:
        raise SystemExit("Specify --write-draft, --suggest-merges, or --approve")
    draft, dropped, metadata, merge_groups, borderline = build_draft_from_arms(seeds, None)
    if args.suggest_merges:
        for left, right, score in suggest_merge_pairs(draft):
            print(f"merge_candidate {left} {right} score={score:.3f}")
        return
    run_dir = write_draft_codebook(
        draft,
        dropped,
        metadata,
        paths.codebook_dir(),
        merge_groups,
        borderline,
    )
    print(f"Wrote {run_dir / constants.CODEBOOK_JSON_FILENAME}")
    print(f"Wrote {run_dir / constants.DROPPED_FEATURES_FILENAME}")


if __name__ == "__main__":
    main()
