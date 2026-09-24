"""Tests for the S3 key and upload manifest helpers."""

from __future__ import annotations

from experiments.bertopic_original_mirror_part3_2026_09_24.src.upload_outputs import (
    build_s3_key,
    collect_output_files,
    upload_outputs,
)


class TestBuildS3Key:
    """Tests for build_s3_key."""

    def test_build_s3_key_prefix(self) -> None:
        """The key keeps the experiment path from ``experiments/`` downward."""
        local = (
            "experiments/bertopic_original_mirror_part3_2026_09_24/"
            "outputs/topics/original/TS/assignments.parquet"
        )

        assert build_s3_key(local) == local


class TestCollectOutputFiles:
    """Tests for collect_output_files."""

    def test_collect_files_excludes_nothing_by_default(self, tmp_path) -> None:
        """Every file under the outputs root is collected."""
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "b.txt").write_text("b", encoding="utf-8")

        assert len(collect_output_files(tmp_path)) == 2

    def test_collect_files_skips_identity_cache(self, tmp_path) -> None:
        """Identity-cache scratch files are not experiment outputs."""
        cache = tmp_path / ".identity_disk_cache" / "embeddings"
        cache.mkdir(parents=True)
        (cache / "vector.npy").write_bytes(b"x")
        (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")

        collected = collect_output_files(tmp_path)

        assert [path.name for path in collected] == ["keep.txt"]


class RecordingClient:
    """Records put_object calls."""

    def __init__(self) -> None:
        self.calls = []

    def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:
        self.calls.append((Bucket, Key, Body))


class TestUploadManifest:
    """Tests for upload_outputs."""

    def test_upload_manifest_counts(self, tmp_path) -> None:
        """The manifest file count matches the number of puts."""
        (tmp_path / "one.txt").write_text("one", encoding="utf-8")
        (tmp_path / "two.txt").write_text("two", encoding="utf-8")
        client = RecordingClient()

        manifest = upload_outputs(tmp_path, bucket="bucket", prefix="prefix", dry_run=False, client=client)

        assert manifest["n_files"] == len(client.calls) == 2
