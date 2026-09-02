from __future__ import annotations

from pathlib import Path

import pytest

import data_platform.constants as constants_mod
from data_platform.constants import (
    COMMENTS_FILENAME,
    METADATA_FILENAME,
    PACKAGE_ROOT,
    POSTS_FILENAME,
)
from data_platform.utils.paths import resolve_package_path, to_package_relative


class TestPackageConstants:
    """Tests for production file-name constants and PACKAGE_ROOT."""

    def test_posts_filename_is_full_csv_name(self) -> None:
        """Verifies POSTS_FILENAME is the full posts.csv name."""
        expected = "posts.csv"
        result = POSTS_FILENAME
        assert result == expected

    def test_comments_filename_is_full_csv_name(self) -> None:
        """Verifies COMMENTS_FILENAME is the full comments.csv name."""
        expected = "comments.csv"
        result = COMMENTS_FILENAME
        assert result == expected

    def test_metadata_filename_is_full_json_name(self) -> None:
        """Verifies METADATA_FILENAME is the full metadata.json name."""
        expected = "metadata.json"
        result = METADATA_FILENAME
        assert result == expected

    def test_package_root_is_data_platform_directory(self) -> None:
        """Verifies PACKAGE_ROOT is the directory that contains constants.py."""
        expected = Path(constants_mod.__file__).resolve().parent
        result = PACKAGE_ROOT
        assert result == expected
        assert result.name == "data_platform"
        assert (result / "constants.py").is_file()


class TestResolvePackagePath:
    """Tests for resolve_package_path()."""

    def test_joins_relative_string_under_package_root(self) -> None:
        """Verifies a nested relative string resolves under PACKAGE_ROOT."""
        relative_path = "data/bluesky/example/posts.csv"
        expected = (PACKAGE_ROOT / "data" / "bluesky" / "example" / "posts.csv").resolve()

        result = resolve_package_path(relative_path)

        assert result == expected
        assert result == result.resolve()

    def test_accepts_path_input(self) -> None:
        """Verifies a pathlib Path relative input is accepted."""
        relative_path = Path("data/x/posts.csv")
        expected = (PACKAGE_ROOT / "data" / "x" / "posts.csv").resolve()

        result = resolve_package_path(relative_path)

        assert result == expected

    def test_dot_resolves_to_package_root(self) -> None:
        """Verifies a lone dot resolves to PACKAGE_ROOT."""
        expected = PACKAGE_ROOT.resolve()

        result = resolve_package_path(".")

        assert result == expected

    def test_empty_string_raises_value_error(self) -> None:
        """Verifies an empty relative path is rejected."""
        with pytest.raises(ValueError):
            resolve_package_path("")

    def test_absolute_path_raises_value_error(self) -> None:
        """Verifies an absolute path is rejected."""
        absolute = Path("/tmp/posts.csv")

        with pytest.raises(ValueError):
            resolve_package_path(absolute)

    def test_parent_segment_inside_package_raises_value_error(self) -> None:
        """Verifies .. is rejected even when the result would stay in the package."""
        with pytest.raises(ValueError):
            resolve_package_path("data/../secrets.txt")

    def test_parent_segment_leaving_package_raises_value_error(self) -> None:
        """Verifies a relative path that walks out of the package is rejected."""
        with pytest.raises(ValueError):
            resolve_package_path("../README.md")


class TestToPackageRelative:
    """Tests for to_package_relative()."""

    def test_absolute_path_under_package_returns_posix_relative(self) -> None:
        """Verifies an absolute path under PACKAGE_ROOT becomes a POSIX relative string."""
        absolute_path = PACKAGE_ROOT / "data" / "posts.csv"
        expected = "data/posts.csv"

        result = to_package_relative(absolute_path)

        assert result == expected
        assert "\\" not in result
        assert not result.startswith("/")

    def test_package_root_returns_dot(self) -> None:
        """Verifies the package root itself converts to a lone dot."""
        expected = "."

        result = to_package_relative(PACKAGE_ROOT)

        assert result == expected

    def test_relative_input_raises_value_error(self) -> None:
        """Verifies a non-absolute input is rejected."""
        with pytest.raises(ValueError):
            to_package_relative("data/posts.csv")

    def test_path_outside_package_raises_value_error(self, tmp_path: Path) -> None:
        """Verifies an absolute path outside PACKAGE_ROOT is rejected."""
        outside = tmp_path / "outside.csv"
        outside.write_text("x", encoding="utf-8")

        with pytest.raises(ValueError):
            to_package_relative(outside)

    def test_round_trip_relative_path(self) -> None:
        """Verifies resolve then convert-back returns the original POSIX relative path."""
        relative_path = "data/run/posts.csv"
        expected = "data/run/posts.csv"

        result = to_package_relative(resolve_package_path(relative_path))

        assert result == expected
