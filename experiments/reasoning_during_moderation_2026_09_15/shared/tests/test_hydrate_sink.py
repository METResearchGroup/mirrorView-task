"""Tests for full-run resume from S3 traces."""

from __future__ import annotations

from pathlib import Path

from experiments.reasoning_during_moderation_2026_09_15.experiment1.run import (
    _hydrate_sink,
    _remaining_posts,
)


class TestHydrateSink:
    """Tests for _hydrate_sink and remaining-post skip."""

    def test_skips_post_ids_already_in_sink(self, tmp_path: Path) -> None:
        """Verifies a post with a stored row is not generated again."""
        sink = tmp_path / "traces.jsonl"
        sink.write_text('{"post_id": "p1"}\n', encoding="utf-8")
        posts = [{"post_id": "p1"}, {"post_id": "p2"}]
        remaining = _remaining_posts(posts, sink, False)
        assert [post["post_id"] for post in remaining] == ["p2"]

    def test_hydrate_ignores_missing_s3_object(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        """Verifies a missing S3 key leaves a fresh sink empty."""
        sink = tmp_path / "outputs" / "vllm" / "traces_qwen.jsonl"
        monkeypatch.setattr(
            "experiments.reasoning_during_moderation_2026_09_15.experiment1.run.REPO_ROOT",
            tmp_path,
        )

        def _raise(_path: Path, _key: str) -> None:
            raise FileNotFoundError("missing")

        monkeypatch.setattr(
            "experiments.reasoning_during_moderation_2026_09_15.experiment1.run.download_if_missing",
            _raise,
        )
        _hydrate_sink(sink)
        assert not sink.is_file()
