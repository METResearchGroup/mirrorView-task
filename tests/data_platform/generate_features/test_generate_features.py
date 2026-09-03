from __future__ import annotations

import json

import pandas as pd

from data_platform.generate_features.generate_features import generate_features
from data_platform.generate_features.metadata import (
    flush_metadata,
    init_feature_run_metadata,
    load_feature_run_metadata,
    metadata_path,
)
from data_platform.generate_features.models import (
    BatchRunStats,
    FeatureRunConfig,
    FeatureRunMetadata,
    FeatureSpec,
    FeatureStatus,
)
from tests.data_platform.constants import (
    LABEL_TIMESTAMP,
    URI_POST_A,
    URI_POST_B,
)
from tests.data_platform.generate_features.conftest import (
    DummyModel,
    make_feature_generation_config,
    sample_preprocessed_records,
    write_preprocessed_posts,
)


def _dummy_spec(name: str) -> FeatureSpec:
    return FeatureSpec(
        name=name,
        model=DummyModel,  # type: ignore[arg-type]
        engine_type="thread_pool",
        generate_fn=lambda _u, _t: None,  # type: ignore[arg-type]
    )


class TestGenerateFeatures:
    """Tests for generate_features()."""

    def test_skips_completed_features(
        self,
        data_root,
        features_dir,
        mock_build_engine,
    ) -> None:
        write_preprocessed_posts(data_root, sample_preprocessed_records(1))
        spec = _dummy_spec("feat_a")
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec},
        )
        metadata = init_feature_run_metadata(config, ("feat_a",))
        metadata.features["feat_a"] = FeatureStatus(status="completed", labeled=1)
        flush_metadata(features_dir, metadata)
        pd.DataFrame(
            [{"source_record_id": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "x": 1}],
        ).to_csv(features_dir / "feat_a.csv", index=False)

        records = pd.DataFrame([{"uri": URI_POST_A, "text": "one"}])
        generate_features(records, config, resume=True)

        mock_build_engine.label_records.assert_not_called()

    def test_does_not_reopen_completed_feature_with_new_posts(
        self,
        data_root,
        features_dir,
        mock_build_engine,
    ) -> None:
        write_preprocessed_posts(data_root, sample_preprocessed_records(2))
        spec = _dummy_spec("feat_a")
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec},
        )
        metadata = init_feature_run_metadata(config, ("feat_a",))
        metadata.features["feat_a"] = FeatureStatus(status="completed", labeled=1)
        flush_metadata(features_dir, metadata)
        pd.DataFrame(
            [{"source_record_id": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "x": 1}],
        ).to_csv(features_dir / "feat_a.csv", index=False)

        records = pd.DataFrame(
            [
                {"uri": URI_POST_A, "text": "one"},
                {"uri": URI_POST_B, "text": "two"},
            ]
        )
        generate_features(records, config, resume=True)

        mock_build_engine.label_records.assert_not_called()
        reloaded = load_feature_run_metadata(config, ("feat_a",))
        assert reloaded.features["feat_a"].status == "completed"
        assert reloaded.features["feat_a"].labeled == 1

    def test_orchestrator_calls_label_records(
        self,
        data_root,
        features_dir,
        mock_build_engine,
    ) -> None:
        write_preprocessed_posts(data_root, sample_preprocessed_records(2))
        spec = _dummy_spec("feat_a")
        mock_build_engine.label_records.return_value = BatchRunStats(
            labeled=2, failed_batches=0
        )
        records = pd.DataFrame(
            [
                {"uri": URI_POST_A, "text": "one"},
                {"uri": URI_POST_B, "text": "two"},
            ]
        )
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec},
            run_config=FeatureRunConfig(batch_size=2),
        )

        generate_features(records, config, resume=False)

        mock_build_engine.label_records.assert_called_once()

    def test_does_not_mark_feature_completed_when_batches_fail(
        self,
        data_root,
        features_dir,
        mock_build_engine,
    ) -> None:
        write_preprocessed_posts(data_root, sample_preprocessed_records(1))
        spec = _dummy_spec("feat_a")
        config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec},
        )
        mock_build_engine.label_records.return_value = BatchRunStats(
            labeled=0, failed_batches=1
        )
        records = pd.DataFrame([{"uri": URI_POST_A, "text": "one"}])

        generate_features(records, config, resume=False)

        metadata = load_feature_run_metadata(config, ("feat_a",))
        assert metadata.features["feat_a"].status == "in_progress"
        assert metadata.features["feat_a"].failed_batches == 1
        assert metadata.sync_status != "completed"

    def test_subset_run_does_not_complete_when_other_features_are_pending(
        self,
        data_root,
        features_dir,
        mock_build_engine,
    ) -> None:
        write_preprocessed_posts(data_root, sample_preprocessed_records(1))
        spec_a = _dummy_spec("feat_a")
        spec_b = _dummy_spec("feat_b")
        full_config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec_a, "feat_b": spec_b},
        )
        metadata = init_feature_run_metadata(full_config, ("feat_a", "feat_b"))
        metadata.features["feat_a"] = FeatureStatus(status="completed", labeled=1)
        metadata.features["feat_b"] = FeatureStatus(status="pending", labeled=0)
        flush_metadata(features_dir, metadata)
        pd.DataFrame(
            [{"source_record_id": URI_POST_A, "label_timestamp": LABEL_TIMESTAMP, "x": 1}],
        ).to_csv(features_dir / "feat_a.csv", index=False)
        subset_config = make_feature_generation_config(
            features_dir,
            feature_registry={"feat_a": spec_a},
        )
        records = pd.DataFrame([{"uri": URI_POST_A, "text": "one"}])

        generate_features(records, subset_config, resume=True)

        reloaded = load_feature_run_metadata(full_config, ("feat_a", "feat_b"))
        assert reloaded.sync_status != "completed"
        assert reloaded.features["feat_b"].status == "pending"
