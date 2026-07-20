"""Unit tests for file discovery."""

from __future__ import annotations

from pathlib import Path

from experiments.migrate_local_artifacts_to_s3_2026_07_20.file_discovery import (
    discover_files,
)
from experiments.migrate_local_artifacts_to_s3_2026_07_20.migration_tracker import (
    MigrationStatus,
)


def test_allowlist_and_suffix_filter(tmp_path: Path) -> None:
    root = tmp_path
    exp = root / "experiments" / "demo_exp"
    exp.mkdir(parents=True)
    (exp / "keep.csv").write_text("a,b\n", encoding="utf-8")
    (exp / "keep.json").write_text("{}", encoding="utf-8")
    (exp / "skip.txt").write_text("nope", encoding="utf-8")
    (exp / "nested").mkdir()
    (exp / "nested" / "more.csv").write_text("x\n", encoding="utf-8")

    files = discover_files(
        repo_root=root,
        allowlist=("experiments/demo_exp",),
        compute_sha256=True,
    )
    paths = {f.local_path for f in files}
    assert paths == {
        "experiments/demo_exp/keep.csv",
        "experiments/demo_exp/keep.json",
        "experiments/demo_exp/nested/more.csv",
    }
    assert all(f.s3_key == f.local_path for f in files)


def test_exclude_migration_folder(tmp_path: Path) -> None:
    root = tmp_path
    mig = root / "experiments" / "migrate_local_artifacts_to_s3_2026_07_20"
    mig.mkdir(parents=True)
    (mig / "should_skip.csv").write_text("x\n", encoding="utf-8")
    other = root / "experiments" / "demo_exp"
    other.mkdir(parents=True)
    (other / "ok.csv").write_text("y\n", encoding="utf-8")

    files = discover_files(
        repo_root=root,
        allowlist=(
            "experiments/demo_exp",
            "experiments/migrate_local_artifacts_to_s3_2026_07_20",
        ),
        exclude_substrings=("experiments/migrate_local_artifacts_to_s3_2026_07_20/",),
        compute_sha256=False,
    )
    assert [f.local_path for f in files] == ["experiments/demo_exp/ok.csv"]


def test_empty_file_skipped(tmp_path: Path) -> None:
    root = tmp_path
    exp = root / "experiments" / "demo_exp"
    exp.mkdir(parents=True)
    (exp / "empty.csv").write_text("", encoding="utf-8")
    (exp / "full.csv").write_text("a\n", encoding="utf-8")

    files = discover_files(
        repo_root=root,
        allowlist=("experiments/demo_exp",),
        compute_sha256=False,
    )
    by_path = {f.local_path: f for f in files}
    assert by_path["experiments/demo_exp/empty.csv"].status == MigrationStatus.SKIPPED
    assert by_path["experiments/demo_exp/full.csv"].status == MigrationStatus.PENDING


def test_colon_paths_preserved(tmp_path: Path) -> None:
    root = tmp_path
    exp = root / "experiments" / "demo_exp"
    stamped = exp / "outputs" / "2026_05_07-02:33:53"
    stamped.mkdir(parents=True)
    target = stamped / "analysis_mirrors.csv"
    target.write_text("a,b\n", encoding="utf-8")

    files = discover_files(
        repo_root=root,
        allowlist=("experiments/demo_exp",),
        compute_sha256=False,
    )
    assert len(files) == 1
    assert ":" in files[0].local_path
    assert files[0].s3_key == files[0].local_path
    assert files[0].local_path.endswith("2026_05_07-02:33:53/analysis_mirrors.csv")
