"""Smoke tests for upload_to_s3.sh."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1] / "upload_to_s3.sh"
)


@pytest.fixture
def local_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.csv"
    p.write_text("a,b\n", encoding="utf-8")
    return p


def test_dry_run_prints_and_exits_0(local_file: Path) -> None:
    result = subprocess.run(
        [
            str(SCRIPT),
            "--bucket",
            "mirrorview-experimental-artifacts",
            "--key",
            "experiments/demo/a.csv",
            "--local",
            str(local_file),
            "--region",
            "us-east-2",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("DRY-RUN: aws s3 cp ")
    assert "s3://mirrorview-experimental-artifacts/experiments/demo/a.csv" in result.stdout


def test_missing_local_exits_2(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(SCRIPT),
            "--bucket",
            "b",
            "--key",
            "k",
            "--local",
            str(tmp_path / "nope.csv"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Local file not found" in result.stderr


def test_help_exits_0() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Upload a single local file" in result.stdout


def test_missing_required_args_exits_2() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--bucket", "b"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
