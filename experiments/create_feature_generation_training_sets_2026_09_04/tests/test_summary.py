"""Tests for SUMMARY.md generation."""

from pathlib import Path

import pandas as pd

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
    S3_BUCKET,
    S3_PREFIX,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.summary import (
    FileStat,
    collect_file_stats,
    render_summary_markdown,
    write_summary,
)

RUN_TIMESTAMP = "2026_09_04-12:00:00"


class TestCollectFileStats:
    """Tests for collect_file_stats."""

    def test_collects_row_count_size_and_object_key(self, tmp_path: Path):
        """Verify parquet metadata is read from the local file."""
        output_root = tmp_path / "training_data"
        classifier_dir = output_root / "is_political"
        classifier_dir.mkdir(parents=True)
        parquet_path = classifier_dir / f"ds1_{RUN_TIMESTAMP}.parquet"
        pd.DataFrame(
            {
                "uri": ["a", "b", "c"],
                "text": ["one", "two", "three"],
            }
        ).to_parquet(parquet_path)

        result = collect_file_stats([parquet_path], output_root)

        expected_size_mb = round(parquet_path.stat().st_size / 1_000_000, 2)
        expected = [
            FileStat(
                classifier_name="is_political",
                file=parquet_path.name,
                size_mb=expected_size_mb,
                n_rows=3,
                s3_prefix=(
                    f"{S3_PREFIX}/is_political/{parquet_path.name}"
                ),
            )
        ]
        assert result == expected


class TestRenderSummaryMarkdown:
    """Tests for render_summary_markdown."""

    def test_renders_classifier_headings_and_totals_in_order(self):
        """Verify empty classifiers still appear with zero totals."""
        stats = [
            FileStat(
                classifier_name="is_political",
                file=f"ds1_{RUN_TIMESTAMP}.parquet",
                size_mb=0.01,
                n_rows=10,
                s3_prefix=(
                    f"{S3_PREFIX}/is_political/ds1_{RUN_TIMESTAMP}.parquet"
                ),
            )
        ]

        result = render_summary_markdown(stats)

        assert f"Training parquets were uploaded to S3 bucket `{S3_BUCKET}`." in result
        for classifier_name in CLASSIFIER_NAMES:
            assert f"## {classifier_name}" in result

        assert "| file | size_mb | n_rows | s3_prefix |" in result
        assert (
            f"| ds1_{RUN_TIMESTAMP}.parquet | 0.01 | 10 | "
            f"{S3_PREFIX}/is_political/ds1_{RUN_TIMESTAMP}.parquet |"
        ) in result

        is_likely_spam_heading_index = result.index("## is_likely_spam")
        is_news_heading_index = result.index("## is_news_or_opinion")
        is_likely_spam_section = result[
            is_likely_spam_heading_index:is_news_heading_index
        ]
        assert f"ds1_{RUN_TIMESTAMP}.parquet" not in is_likely_spam_section

        totals_start = result.index("## Totals")
        totals_section = result[totals_start:]
        assert "| category | n_rows |" in totals_section

        totals_rows = [
            line
            for line in totals_section.splitlines()
            if line.startswith("| ") and "category" not in line and "---" not in line
        ]
        expected_totals_rows = [
            f"| {classifier_name} | {10 if classifier_name == 'is_political' else 0} |"
            for classifier_name in CLASSIFIER_NAMES
        ]
        assert totals_rows == expected_totals_rows


class TestWriteSummary:
    """Tests for write_summary."""

    def test_writes_rendered_markdown_to_path(self, tmp_path: Path):
        """Verify write_summary persists markdown to the requested path."""
        stats = [
            FileStat(
                classifier_name="is_political",
                file=f"ds1_{RUN_TIMESTAMP}.parquet",
                size_mb=0.01,
                n_rows=1,
                s3_prefix=(
                    f"{S3_PREFIX}/is_political/ds1_{RUN_TIMESTAMP}.parquet"
                ),
            )
        ]
        summary_path = tmp_path / "SUMMARY.md"

        result = write_summary(stats, summary_path)

        expected = render_summary_markdown(stats)
        assert result == summary_path
        assert summary_path.read_text(encoding="utf-8") == expected
