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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
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
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import ClusterLabelResult

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
    part2_theme_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "definition": self.definition,
            "positive_examples": [ex.to_dict() for ex in self.positive_examples],
            "negative_examples": [ex.to_dict() for ex in self.negative_examples],
            "discovery_arm": self.discovery_arm,
            "source_cluster_ids": self.source_cluster_ids,
            "member_feature_ids": list(self.member_feature_ids),
            "cluster_size": self.cluster_size,
            "part2_theme_id": self.part2_theme_id,
        }


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
    """Normalize a cluster label to a 2–5 word lowercase feature name."""
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


def is_topic_only_feature(
    definition: str,
    members: tuple[dict[str, Any], ...],
) -> bool:
    """Return True when a cluster is pure topic/subject with no rhetoric."""
    if members:
        categories = {str(record.get("category", "")) for record in members}
        non_topic = [cat for cat in categories if cat and cat != constants.TOPIC_ONLY_CATEGORY]
        if not non_topic and constants.TOPIC_ONLY_CATEGORY in categories:
            return True
    return _definition_is_pure_topic(definition)


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
    return CodebookFeature(
        feature_id=feature_id,
        name=normalize_feature_name(cluster.cluster_label),
        definition=cluster.definition.strip(),
        positive_examples=positives,
        negative_examples=negatives,
        discovery_arm=cluster.arm,
        source_cluster_ids=source_ids,
        member_feature_ids=tuple(record["feature_id"] for record in cluster.members),
        cluster_size=cluster.n_members,
        part2_theme_id=None,
    )


def assign_feature_ids(features: list[CodebookFeature]) -> list[CodebookFeature]:
    """Assign sequential cb_NNN ids preserving order."""
    reassigned: list[CodebookFeature] = []
    for index, feature in enumerate(features, start=1):
        feature_id = f"{constants.CODEBOOK_FEATURE_ID_PREFIX}{index:03d}"
        reassigned.append(
            CodebookFeature(
                feature_id=feature_id,
                name=feature.name,
                definition=feature.definition,
                positive_examples=feature.positive_examples,
                negative_examples=feature.negative_examples,
                discovery_arm=feature.discovery_arm,
                source_cluster_ids=feature.source_cluster_ids,
                member_feature_ids=feature.member_feature_ids,
                cluster_size=feature.cluster_size,
                part2_theme_id=feature.part2_theme_id,
            )
        )
    return reassigned


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


def write_codebook_markdown(draft: CodebookDraft, output_path: Path) -> None:
    """Write a human-readable markdown summary of the draft codebook."""
    lines = [f"# Codebook draft {draft.version}", ""]
    for feature in draft.features:
        lines.append(f"## {feature.feature_id}: {feature.name}")
        lines.append(feature.definition)
        lines.append("")
        lines.append(f"- Arm: {feature.discovery_arm}")
        lines.append(f"- Cluster size: {feature.cluster_size}")
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_draft_codebook(
    draft: CodebookDraft,
    dropped: tuple[DroppedFeature, ...],
    metadata: dict[str, Any],
    output_root: Path,
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
    write_codebook_markdown(draft, run_dir / constants.CODEBOOK_MD_FILENAME)
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
) -> tuple[CodebookDraft, tuple[DroppedFeature, ...], dict[str, Any]]:
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
            if is_topic_only_feature(cluster.definition, cluster.members):
                dropped.append(
                    DroppedFeature(
                        cluster_id=cluster.cluster_id,
                        arm=arm,
                        reason=DROP_REASON_TOPIC_ONLY,
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
    synonyms = load_synonym_rows(SYNONYMS_PATH)
    draft = CodebookDraft(version=built_at, features=tuple(features))
    draft = merge_codebook_entries(draft, synonyms)
    metadata = {
        "built_at": built_at,
        "seeds": list(seeds),
        "hdbscan_noise_share_by_arm": noise_by_arm,
    }
    print(f"topic_only_dropped={len(dropped)}")
    print(f"draft_features={len(draft.features)}")
    print(f"arms_merged={len(constants.TEXT_ARMS)}")
    return draft, tuple(dropped), metadata


def _noise_shares_for_seeds(normalize_dir: Path, seeds: tuple[int, ...]) -> dict[str, float]:
    shares: dict[str, float] = {}
    for seed in seeds:
        clusters_dir = cluster_seed_dir(normalize_dir, seed)
        if not clusters_dir.is_dir():
            raise FileNotFoundError(f"Missing clusters dir for seed {seed}: {clusters_dir}")
        assignments = load_hdbscan_assignments(clusters_dir)
        shares[f"seed_{seed}"] = compute_noise_share(assignments)
    return shares


def _resolve_normalize_dir(arm: str, normalize_dirs: dict[str, Path] | None) -> Path:
    if normalize_dirs and arm in normalize_dirs:
        return normalize_dirs[arm]
    return latest_timestamp_subdir(paths.normalize_run_dir(arm))


def main(argv: list[str] | None = None) -> None:
    """CLI entry for draft build, merge suggestions, and approval."""
    parser = argparse.ArgumentParser(description="Build shared codebook from cluster labels.")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(constants.CLUSTER_SEEDS))
    parser.add_argument("--write-draft", action="store_true")
    parser.add_argument("--suggest-merges", action="store_true")
    parser.add_argument("--approve", type=Path, default=None)
    parser.add_argument("--approved-by", type=str, default=None)
    args = parser.parse_args(argv)
    seeds = tuple(args.seeds)
    if args.approve is not None:
        if not args.approved_by:
            raise SystemExit("--approved-by is required with --approve")
        approved_dir = approve_codebook(args.approve, args.approved_by)
        print(f"Wrote {approved_dir / constants.CODEBOOK_JSON_FILENAME}")
        print(f"Wrote {approved_dir / constants.APPROVAL_JSON_FILENAME}")
        return
    if not args.write_draft and not args.suggest_merges:
        raise SystemExit("Specify --write-draft, --suggest-merges, or --approve")
    draft, dropped, metadata = build_draft_from_arms(seeds, None)
    if args.suggest_merges:
        for left, right, score in suggest_merge_pairs(draft):
            print(f"merge_candidate {left} {right} score={score:.3f}")
        return
    run_dir = write_draft_codebook(draft, dropped, metadata, paths.codebook_dir())
    print(f"Wrote {run_dir / constants.CODEBOOK_JSON_FILENAME}")
    print(f"Wrote {run_dir / constants.DROPPED_FEATURES_FILENAME}")


if __name__ == "__main__":
    main()
