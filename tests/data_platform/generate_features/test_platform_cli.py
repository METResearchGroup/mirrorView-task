from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from data_platform.generate_features.generate_bluesky_features import (
    BLUESKY_SPEC,
    app as bluesky_app,
)
from data_platform.generate_features.generate_reddit_features import app as reddit_app
from data_platform.generate_features.generate_twitter_features import (
    app as twitter_app,
    generate_twitter_features,
)
from data_platform.generate_features.models import FeatureRunConfig
from data_platform.generate_features.platform_cli import (
    build_feature_config,
    feature_run_dir,
    features_from_cli,
    generate_feature_subset,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageManager, StorageStage
from tests.data_platform.constants import (
    FEATURES_DATASET_ID,
    PREPROCESSED_RUN_DIR,
    VALID_TWITTER_DATASET_ID,
)

OLDER_FEATURE_RUN = "2026_01_01-00:00:00"
MISSING_FEATURE_RUN = "2026_03_01-00:00:00"


def write_feature_checkpoint(
    data_root: Path,
    run_name: str,
    *,
    sync_status: str,
    dataset_id: str = FEATURES_DATASET_ID,
) -> Path:
    run_dir = data_root / "bluesky" / dataset_id / "features" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "sync_status": sync_status,
                "features": {},
            }
        ),
        encoding="utf-8",
    )
    return run_dir


@pytest.fixture
def feature_storage(data_root: Path) -> StorageManager:
    return BlueskyStorageManager(
        StorageStage.FEATURES,
        FEATURES_DATASET_ID,
        records_filename="features",
    )


def test_generate_feature_subset_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown features"):
        generate_feature_subset(["not_a_real_feature"])


def test_generate_feature_subset_none_returns_none() -> None:
    assert generate_feature_subset(None) is None
    assert generate_feature_subset([]) is None


def test_generate_feature_subset_valid_names() -> None:
    assert generate_feature_subset(["is_political"]) == ("is_political",)


def test_features_from_cli_none() -> None:
    assert features_from_cli(None) is None


def test_features_from_cli_comma_and_repeat() -> None:
    assert features_from_cli(["is_political", "is_news_or_opinion,is_self_contained"]) == [
        "is_political",
        "is_news_or_opinion",
        "is_self_contained",
    ]


def test_features_from_cli_empty_strings_returns_none() -> None:
    assert features_from_cli([""]) is None


def write_empty_twitter_preprocessed_run(data_root: Path) -> Path:
    run_dir = (
        data_root / "twitter" / VALID_TWITTER_DATASET_ID / "preprocessed" / PREPROCESSED_RUN_DIR
    )
    run_dir.mkdir(parents=True)
    (run_dir / "posts.csv").write_text("tweet_id,text\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(json.dumps({}), encoding="utf-8")
    return run_dir


def test_empty_twitter_input_does_not_create_feature_run(data_root: Path) -> None:
    """Given an empty completed preprocessed run, when generating features, then no features run dir is created."""
    write_empty_twitter_preprocessed_run(data_root)

    result = generate_twitter_features(VALID_TWITTER_DATASET_ID)

    assert result == {}
    features_root = data_root / "twitter" / VALID_TWITTER_DATASET_ID / "features"
    assert not features_root.exists()


def test_empty_twitter_input_with_missing_checkpoint_fails(data_root: Path) -> None:
    write_empty_twitter_preprocessed_run(data_root)

    with pytest.raises(FileNotFoundError, match=MISSING_FEATURE_RUN):
        generate_twitter_features(
            VALID_TWITTER_DATASET_ID, checkpoint=MISSING_FEATURE_RUN
        )


def test_empty_twitter_input_with_completed_checkpoint_fails(data_root: Path) -> None:
    write_empty_twitter_preprocessed_run(data_root)
    completed = (
        data_root / "twitter" / VALID_TWITTER_DATASET_ID / "features" / OLDER_FEATURE_RUN
    )
    completed.mkdir(parents=True)
    (completed / "metadata.json").write_text(
        json.dumps(
            {
                "dataset_id": VALID_TWITTER_DATASET_ID,
                "sync_status": "completed",
                "features": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="already completed"):
        generate_twitter_features(
            VALID_TWITTER_DATASET_ID, checkpoint=OLDER_FEATURE_RUN
        )


class TestFeatureRunDir:
    """Tests for feature_run_dir()."""

    def test_starts_new_timestamped_folder_when_no_checkpoint(
        self, feature_storage: StorageManager
    ) -> None:
        result = feature_run_dir(feature_storage, None)

        assert result.parent == feature_storage.root_dir
        assert result.name != "features"
        assert result.is_dir()

    def test_resumes_named_unfinished_checkpoint_without_creating_another_folder(
        self, data_root: Path, feature_storage: StorageManager
    ) -> None:
        expected = write_feature_checkpoint(
            data_root, OLDER_FEATURE_RUN, sync_status="in_progress"
        )

        result = feature_run_dir(feature_storage, OLDER_FEATURE_RUN)

        assert result == expected
        feature_dirs = [path for path in feature_storage.root_dir.iterdir() if path.is_dir()]
        assert feature_dirs == [expected]

    def test_new_run_fails_when_unfinished_run_exists(
        self, data_root: Path, feature_storage: StorageManager
    ) -> None:
        unfinished = write_feature_checkpoint(
            data_root, OLDER_FEATURE_RUN, sync_status="in_progress"
        )

        with pytest.raises(ValueError, match="unfinished"):
            feature_run_dir(feature_storage, None)

        assert unfinished.is_dir()

    def test_new_run_succeeds_when_existing_runs_are_completed(
        self, data_root: Path, feature_storage: StorageManager
    ) -> None:
        write_feature_checkpoint(data_root, OLDER_FEATURE_RUN, sync_status="completed")

        result = feature_run_dir(feature_storage, None)

        assert result != feature_storage.root_dir / OLDER_FEATURE_RUN
        assert result.is_dir()

    def test_new_run_fails_when_folder_has_no_metadata(
        self, feature_storage: StorageManager
    ) -> None:
        run_dir = feature_storage.root_dir / OLDER_FEATURE_RUN
        run_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="--checkpoint"):
            feature_run_dir(feature_storage, None)

        assert run_dir.is_dir()
        assert not (run_dir / "metadata.json").exists()

    def test_named_checkpoint_resumes_folder_without_metadata(
        self, feature_storage: StorageManager
    ) -> None:
        run_dir = feature_storage.root_dir / OLDER_FEATURE_RUN
        run_dir.mkdir(parents=True)

        result = feature_run_dir(feature_storage, OLDER_FEATURE_RUN)

        assert result == run_dir
        assert not (run_dir / "metadata.json").exists()

    def test_named_checkpoint_fails_when_folder_is_missing(
        self, feature_storage: StorageManager
    ) -> None:
        with pytest.raises(FileNotFoundError, match=MISSING_FEATURE_RUN):
            feature_run_dir(feature_storage, MISSING_FEATURE_RUN)

        assert not (feature_storage.root_dir / MISSING_FEATURE_RUN).exists()

    def test_named_checkpoint_fails_when_run_is_completed(
        self, data_root: Path, feature_storage: StorageManager
    ) -> None:
        completed = write_feature_checkpoint(
            data_root, OLDER_FEATURE_RUN, sync_status="completed"
        )

        with pytest.raises(ValueError, match="already completed"):
            feature_run_dir(feature_storage, OLDER_FEATURE_RUN)

        assert completed.is_dir()

    def test_rejects_path_escape(self, feature_storage: StorageManager) -> None:
        with pytest.raises(ValueError, match="single feature run directory name"):
            feature_run_dir(feature_storage, "../other-dir")


class TestBuildFeatureConfig:
    """Tests for build_feature_config() run-directory resolution."""

    def test_uses_timestamped_features_dir(self, data_root: Path) -> None:
        config = build_feature_config(
            BLUESKY_SPEC,
            FEATURES_DATASET_ID,
            run_config=FeatureRunConfig(),
        )

        assert config.features_dir.parent.name == "features"
        assert config.features_dir.name != "features"
        assert config.features_dir.is_dir()

    def test_resumes_named_checkpoint(self, data_root: Path) -> None:
        write_feature_checkpoint(
            data_root, PREPROCESSED_RUN_DIR, sync_status="in_progress"
        )

        config = build_feature_config(
            BLUESKY_SPEC,
            FEATURES_DATASET_ID,
            run_config=FeatureRunConfig(),
            checkpoint=PREPROCESSED_RUN_DIR,
        )

        assert config.features_dir.name == PREPROCESSED_RUN_DIR
        assert config.features_dir.parent.name == "features"


class TestFeatureGenerationCli:
    """Tests that platform feature CLIs use optional --checkpoint."""

    @pytest.mark.parametrize("cli_app", [bluesky_app, twitter_app, reddit_app])
    def test_help_lists_checkpoint_and_not_subcommands(self, cli_app) -> None:
        result = CliRunner().invoke(cli_app, ["--help"])

        assert result.exit_code == 0
        assert "--checkpoint" in result.stdout
        assert "--run-dir" not in result.stdout
        assert "--latest" not in result.stdout
        assert "new-run" not in result.stdout
