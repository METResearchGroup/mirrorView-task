from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.utils.config_paths import (
    load_yaml_config,
    resolve_config_path,
    to_repo_relative,
)
from lib.constants import REPO_ROOT


def test_resolve_config_path_bare_filename(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    config_file = configs_dir / "mirrorview.yaml"
    config_file.write_text("name: test\n", encoding="utf-8")

    resolved = resolve_config_path(Path("mirrorview"), configs_dir)

    assert resolved == config_file.resolve()


def test_resolve_config_path_adds_yaml_suffix(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    config_file = configs_dir / "default.yaml"
    config_file.write_text("name: default\n", encoding="utf-8")

    resolved = resolve_config_path(Path("default"), configs_dir)

    assert resolved == config_file.resolve()


def test_resolve_config_path_absolute_path(tmp_path: Path) -> None:
    config_file = tmp_path / "custom.yaml"
    config_file.write_text("dataset_id: bluesky_test\n", encoding="utf-8")
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    resolved = resolve_config_path(config_file, configs_dir)

    assert resolved == config_file.resolve()


def test_resolve_config_path_missing_raises(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Config not found"):
        resolve_config_path(Path("missing.yaml"), configs_dir)


def test_load_yaml_config(tmp_path: Path) -> None:
    config_file = tmp_path / "test.yaml"
    config_file.write_text("dataset_id: bluesky_abc\n", encoding="utf-8")

    loaded = load_yaml_config(config_file)

    assert loaded == {"dataset_id": "bluesky_abc"}


def test_load_yaml_config_rejects_non_dict_root(tmp_path: Path) -> None:
    config_file = tmp_path / "list.yaml"
    config_file.write_text("- item\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mapping"):
        load_yaml_config(config_file)


class TestToRepoRelative:
    """Tests for to_repo_relative()."""

    def test_absolute_path_under_repo_returns_posix_relative(self, tmp_path: Path) -> None:
        """Verifies an absolute path under repo_root becomes a POSIX relative string."""
        repo_root = tmp_path
        absolute_path = (
            repo_root
            / "data_platform"
            / "ingestion"
            / "configs"
            / "bluesky"
            / "mirrorview.yaml"
        )
        expected = "data_platform/ingestion/configs/bluesky/mirrorview.yaml"

        result = to_repo_relative(absolute_path, repo_root)

        assert result == expected
        assert "\\" not in result
        assert not result.startswith("/")

    def test_same_basename_configs_on_different_platforms_differ(self) -> None:
        """Verifies same YAML file names under different platforms stay distinct."""
        bluesky = (
            REPO_ROOT
            / "data_platform"
            / "ingestion"
            / "configs"
            / "bluesky"
            / "mirrorview.yaml"
        )
        twitter = (
            REPO_ROOT
            / "data_platform"
            / "ingestion"
            / "configs"
            / "twitter"
            / "mirrorview.yaml"
        )
        expected_bluesky = "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
        expected_twitter = "data_platform/ingestion/configs/twitter/mirrorview.yaml"

        bluesky_result = to_repo_relative(bluesky, REPO_ROOT)
        twitter_result = to_repo_relative(twitter, REPO_ROOT)

        assert bluesky_result == expected_bluesky
        assert twitter_result == expected_twitter
        assert bluesky_result != twitter_result

    def test_repo_root_returns_dot(self, tmp_path: Path) -> None:
        """Verifies the repo root itself converts to a lone dot."""
        expected = "."

        result = to_repo_relative(tmp_path, tmp_path)

        assert result == expected

    def test_relative_input_raises_value_error(self, tmp_path: Path) -> None:
        """Verifies a non-absolute input is rejected."""
        with pytest.raises(ValueError):
            to_repo_relative(
                "data_platform/ingestion/configs/bluesky/mirrorview.yaml",
                tmp_path,
            )

    def test_path_outside_repo_raises_value_error(self, tmp_path: Path) -> None:
        """Verifies an absolute path outside repo_root is rejected."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        outside = tmp_path / "outside.yaml"

        with pytest.raises(ValueError):
            to_repo_relative(outside, repo_root)
