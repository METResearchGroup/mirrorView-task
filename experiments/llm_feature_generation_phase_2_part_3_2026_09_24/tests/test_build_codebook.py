"""Tests for shared codebook build and approval."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import build_codebook as bc
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants


def _write_label_artifact(
    label_dir: Path,
    call_index: int,
    cluster_id: int,
    arm: str,
    label: str,
    definition: str,
) -> None:
    payload = {
        "cluster_label_row": {
            "cluster_id": cluster_id,
            "arm": arm,
            "seed": 42,
            "n_members": 2,
            "sampled_feature_ids": [],
            "result": {
                "cluster_id": cluster_id,
                "cluster_label": label,
                "definition": definition,
                "salience_notes": "",
            },
        }
    }
    label_dir.mkdir(parents=True, exist_ok=True)
    artifact = label_dir / f"{call_index:05d}_2026-01-01T00-00-00.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")


def _minimal_normalize_tree(tmp_path: Path, arm: str) -> Path:
    embed_dir = tmp_path / "normalize" / "2026-01-01T00-00-00"
    clusters_dir = embed_dir / "clusters_seed_42"
    label_dir = clusters_dir / "labels" / "2026-01-01T00-00-01"
    _write_label_artifact(label_dir, 0, 0, arm, "Short Label Name", "A definition.")
    assignments = {"feat_a": 0, "feat_b": 0}
    (clusters_dir / constants.ASSIGNMENTS_HDBSCAN_FILENAME).write_text(
        json.dumps(assignments),
        encoding="utf-8",
    )
    records = [
        {
            "feature_id": "feat_a",
            "message_id": "post_a",
            "category": "pragmatics_intent",
            "evidence_span": "hello world",
        },
        {
            "feature_id": "feat_b",
            "message_id": "post_b",
            "category": "semantic_content",
            "evidence_span": "foo bar",
        },
    ]
    features_path = embed_dir / "features.jsonl"
    features_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return embed_dir


class TestLoadArmClusterLabels:
    """Tests for load_arm_cluster_labels."""

    def test_load_arm_cluster_labels_reads_normalize_label_json(self, tmp_path: Path) -> None:
        embed_dir = _minimal_normalize_tree(tmp_path, "original_only")
        results = bc.load_arm_cluster_labels("original_only", embed_dir, 42)
        assert len(results) == 1
        assert results[0].cluster_id == 0
        assert results[0].cluster_label == "Short Label Name"
        assert results[0].definition == "A definition."


class TestSelectPrimaryClusterRun:
    """Tests for select_primary_cluster_run."""

    def test_select_primary_seed_prefers_seed_42(self, tmp_path: Path) -> None:
        embed_dir = tmp_path / "normalize" / "embed"
        for seed in (42, 43, 44):
            cluster_dir = embed_dir / f"clusters_seed_{seed}"
            (cluster_dir / "labels" / "2026-01-01T00-00-00").mkdir(parents=True)
        primary = bc.select_primary_cluster_run("original_only", embed_dir)
        assert primary.name == "clusters_seed_42"


class TestBuildCodebookEntry:
    """Tests for build_codebook_entry."""

    def test_build_entry_assigns_discovery_examples(self, tmp_path: Path) -> None:
        discovery_ids = {"post_a", "post_b", "post_c", "post_d"}
        cohort = pd.DataFrame(
            {
                "post_id": ["post_a", "post_b", "post_c", "post_d"],
                "original_text": ["ta", "tb", "tc", "td"],
                "mirror_text": ["ma", "mb", "mc", "md"],
                "split": ["discovery"] * 4,
            }
        )
        cluster = bc.ArmClusterRecord(
            cluster_id=0,
            cluster_label="Two Word Name",
            definition="Defines the cluster.",
            n_members=2,
            members=(
                {
                    "feature_id": "f1",
                    "message_id": "post_a",
                    "category": "semantic_content",
                    "evidence_span": "long evidence",
                },
                {
                    "feature_id": "f2",
                    "message_id": "post_b",
                    "category": "semantic_content",
                    "evidence_span": "ev",
                },
            ),
            arm="original_only",
            seed=42,
        )
        rng = __import__("numpy").random.default_rng(42)
        entry = bc.build_codebook_entry(cluster, "cb_001", cohort, discovery_ids, rng)
        assert len(entry.positive_examples) == constants.CODEBOOK_EXAMPLES_PER_POLARITY
        assert len(entry.negative_examples) == constants.CODEBOOK_EXAMPLES_PER_POLARITY
        for example in entry.positive_examples + entry.negative_examples:
            assert example.post_id in discovery_ids
            row = cohort.loc[cohort["post_id"] == example.post_id].iloc[0]
            assert example.text == row["original_text"]


class TestIsTopicOnlyFeature:
    """Tests for is_topic_only_feature."""

    def test_topic_only_drop_flags_topic_subject_without_rhetoric(self) -> None:
        members = (
            {"feature_id": "f1", "category": constants.TOPIC_ONLY_CATEGORY},
            {"feature_id": "f2", "category": constants.TOPIC_ONLY_CATEGORY},
        )
        definition = "Posts are about guns policy domain only."
        assert bc.is_topic_only_feature(definition, members) is True


class TestMergeCodebookEntries:
    """Tests for merge_codebook_entries."""

    def test_no_auto_merge_without_synonym_row(self) -> None:
        feature = _sample_feature("cb_001", "original_only")
        other = _sample_feature("cb_002", "mirror_only")
        draft = bc.CodebookDraft(version="v", features=(feature, other))
        merged = bc.merge_codebook_entries(draft, ())
        assert len(merged.features) == 2


class TestApplySynonymMerges:
    """Tests for apply_synonym_merges."""

    def test_synonym_csv_merge_combines_source_cluster_ids(self, tmp_path: Path) -> None:
        feature_a = _sample_feature("cb_001", "original_only", cluster_id=1)
        feature_b = _sample_feature("cb_002", "mirror_only", cluster_id=2)
        draft = bc.CodebookDraft(version="v", features=(feature_a, feature_b))
        csv_path = tmp_path / "synonyms.csv"
        csv_path.write_text(
            "feature_id_a,feature_id_b,merged_to,confirmed_by,confirmed_at,notes\n"
            "cb_001,cb_002,cb_001,reviewer,2026-01-01T00-00-00,ok\n",
            encoding="utf-8",
        )
        before = csv_path.read_text(encoding="utf-8")
        result = bc.apply_synonym_merges(draft, csv_path)
        assert len(result.features) == 1
        survivor = result.features[0]
        assert set(survivor.source_cluster_ids["original_only"]) == {1}
        assert set(survivor.source_cluster_ids["mirror_only"]) == {2}
        assert csv_path.read_text(encoding="utf-8") == before


class TestWriteDraftCodebook:
    """Tests for write_draft_codebook."""

    def test_write_draft_emits_timestamped_dir(self, tmp_path: Path) -> None:
        draft = bc.CodebookDraft(version="2026-01-01T00-00-00", features=())
        run_dir = bc.write_draft_codebook(draft, (), {"built_at": "2026-01-01T00-00-00"}, tmp_path)
        expected = tmp_path / "draft_2026-01-01T00-00-00" / constants.CODEBOOK_JSON_FILENAME
        assert run_dir == expected.parent
        assert expected.is_file()


class TestApproveCodebook:
    """Tests for approve_codebook and CLI approve."""

    def test_approve_writes_approval_json(self, tmp_path: Path) -> None:
        draft_dir = tmp_path / "draft_2026-01-01T00-00-00"
        draft_dir.mkdir()
        codebook = {"version": "2026-01-01T00-00-00", "features": []}
        draft_path = draft_dir / constants.CODEBOOK_JSON_FILENAME
        draft_path.write_text(json.dumps(codebook), encoding="utf-8")
        with patch.object(bc.paths, "codebook_dir", return_value=tmp_path):
            approved_dir = bc.approve_codebook(draft_path, "reviewer")
        approval_path = approved_dir / constants.APPROVAL_JSON_FILENAME
        payload = json.loads(approval_path.read_text(encoding="utf-8"))
        assert payload["approved_by"] == "reviewer"
        assert payload["codebook_version"] == "2026-01-01T00-00-00"

    def test_approve_copies_codebook_to_approved_dir(self, tmp_path: Path) -> None:
        draft_dir = tmp_path / "draft_2026-01-01T00-00-00"
        draft_dir.mkdir()
        features = [_sample_feature(f"cb_{i:03d}", "paired").to_dict() for i in range(1, 4)]
        draft_path = draft_dir / constants.CODEBOOK_JSON_FILENAME
        draft_path.write_text(
            json.dumps({"version": "2026-01-01T00-00-00", "features": features}),
            encoding="utf-8",
        )
        with patch.object(bc.paths, "codebook_dir", return_value=tmp_path):
            approved_dir = bc.approve_codebook(draft_path, "reviewer")
        approved = json.loads(
            (approved_dir / constants.CODEBOOK_JSON_FILENAME).read_text(encoding="utf-8")
        )
        assert len(approved["features"]) == 3


class TestNormalizeFeatureName:
    """Tests for normalize_feature_name."""

    def test_name_word_count_enforced(self) -> None:
        long_label = "This is a very long cluster name beyond five words"
        result = bc.normalize_feature_name(long_label)
        assert len(result.split()) <= constants.CODEBOOK_NAME_MAX_WORDS


def _sample_feature(
    feature_id: str,
    arm: str,
    cluster_id: int = 0,
) -> bc.CodebookFeature:
    example = bc.PostExample(post_id="p1", text="t1")
    source_ids = {a: [] for a in constants.TEXT_ARMS}
    source_ids[arm] = [cluster_id]
    return bc.CodebookFeature(
        feature_id=feature_id,
        name="sample name",
        definition="A sample definition.",
        positive_examples=(example, example),
        negative_examples=(example, example),
        discovery_arm=arm,
        source_cluster_ids=source_ids,
        member_feature_ids=("m1",),
        cluster_size=3,
    )
