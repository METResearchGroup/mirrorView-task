"""Analysis of word count, post length, and compression metrics.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis/main.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.analysis.interfaces import CalculateMetric
from experiments.mirrors_content_analysis_2026_04_24.analysis.length_compression_analysis.metrics import (
    DEFAULT_LENGTH_METRICS,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.metric_aggregator import (
    MetricAggregator,
    PairwiseAnalysisResult,
    metrics_dict_for_text,
)
from experiments.mirrors_content_analysis_2026_04_24.analysis.table_renderer import TableRenderer
from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader
from lib.timestamp_utils import get_current_timestamp

LENGTH_COMPRESSION_ANALYSIS_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = LENGTH_COMPRESSION_ANALYSIS_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = LENGTH_COMPRESSION_ANALYSIS_DIR / "labels_mirrors.csv"


def _all_mirrors_claude_path() -> Path:
    return Dataloader.PROJECT_ROOT / "img" / "all_mirrors_claude.csv"


class LengthCompressionAnalyzer:
    """Length/compression metrics with design-aware pairwise filter and partition splits."""

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        metrics: Sequence[CalculateMetric] | None = None,
    ) -> None:
        self.df = df
        self._metrics: tuple[CalculateMetric, ...] = (
            tuple(metrics) if metrics is not None else DEFAULT_LENGTH_METRICS
        )
        self._aggregator = MetricAggregator(df=self.df, metrics=self._metrics)
        self.timestamp = get_current_timestamp()
        self.output_dir = LENGTH_COMPRESSION_ANALYSIS_DIR / "outputs" / self.timestamp
        self.results: dict[str, Any] = {
            "original_text_analysis": None,
            "mirror_text_analysis": None,
            "pairwise_analysis": None,
            "keep_remove_analysis": None,
        }

    def original_text_analysis(self) -> None:
        self.results["original_text_analysis"] = self._aggregator.original_text_analysis()

    def mirror_text_analysis(self) -> None:
        self.results["mirror_text_analysis"] = self._aggregator.mirror_text_analysis()

    def pairwise_analysis(self) -> None:
        self.results["pairwise_analysis"] = self._aggregator.pairwise_analysis()

    def keep_remove_analysis(self) -> None:
        packed = self.results["pairwise_analysis"]
        if not isinstance(packed, PairwiseAnalysisResult):
            raise RuntimeError("Run pairwise_analysis before keep_remove_analysis.")
        self.results["keep_remove_analysis"] = self._aggregator.keep_remove_analysis(packed.dataframe)

    def show_results(self) -> None:
        renderer = TableRenderer(self._metrics)
        renderer.render_metric_glossary()
        orig = self.results["original_text_analysis"]
        mir = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if orig is not None:
            renderer.render_metric_calculations(
                "Original text - means by party x condition (+ marginals)",
                orig,
            )

        if mir is not None:
            renderer.render_metric_calculations(
                "Mirror text - means by party x condition (+ marginals)",
                mir,
            )

        if isinstance(pairwise, PairwiseAnalysisResult):
            if not pairwise.dataframe.empty:
                renderer.render_pairwise_sample(pairwise.dataframe)
            if pairwise.partition_means:
                renderer.render_metric_calculations(
                    "Pairwise - mean ratio by party x condition (+ marginals)",
                    pairwise.partition_means,
                )

        if isinstance(keep_remove, dict):
            renderer.render_keep_remove(keep_remove)

    def export_metric_labels(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Export per-post metric labels for original and mirrored texts."""
        raw_path = _all_mirrors_claude_path()
        raw = pd.read_csv(raw_path)
        for col in ("post_primary_key", "original_text", "claude_mirror"):
            if col not in raw.columns:
                raise KeyError(f"Expected column {col!r} in {raw_path}")

        post_texts = (
            raw[["post_primary_key", "original_text", "claude_mirror"]]
            .dropna(subset=["post_primary_key"])
            .copy()
        )
        post_texts["post_primary_key"] = post_texts["post_primary_key"].astype(str)
        post_texts = post_texts.drop_duplicates(subset=["post_primary_key"], keep="first")

        labels_original = post_texts[["post_primary_key"]].copy()
        labels_mirrors = post_texts[["post_primary_key"]].copy()

        labels_original_records = [
            metrics_dict_for_text(str(text or ""), self._metrics)
            for text in post_texts["original_text"]
        ]
        labels_mirror_records = [
            metrics_dict_for_text(str(text or ""), self._metrics)
            for text in post_texts["claude_mirror"]
        ]

        labels_original = pd.concat(
            [labels_original.reset_index(drop=True), pd.DataFrame(labels_original_records)],
            axis=1,
        )
        labels_mirrors = pd.concat(
            [labels_mirrors.reset_index(drop=True), pd.DataFrame(labels_mirror_records)],
            axis=1,
        )

        labels_original.to_csv(LABELS_ORIGINAL_PATH, index=False)
        labels_mirrors.to_csv(LABELS_MIRRORS_PATH, index=False)
        return labels_original, labels_mirrors

    def save_results(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        original = self.results["original_text_analysis"]
        mirror = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if isinstance(original, dict):
            pd.DataFrame(
                [
                    {
                        "metric_name": metric_name,
                        "partition": partition,
                        "value": value,
                    }
                    for metric_name, calc in original.items()
                    for partition, value in calc.as_dict().items()
                ]
            ).to_csv(self.output_dir / "analysis_original_text.csv", index=False)

        if isinstance(mirror, dict):
            pd.DataFrame(
                [
                    {
                        "metric_name": metric_name,
                        "partition": partition,
                        "value": value,
                    }
                    for metric_name, calc in mirror.items()
                    for partition, value in calc.as_dict().items()
                ]
            ).to_csv(self.output_dir / "analysis_mirrors.csv", index=False)

        if isinstance(pairwise, PairwiseAnalysisResult):
            pairwise.dataframe.to_csv(self.output_dir / "analysis_pairwise.csv", index=False)

        if isinstance(keep_remove, dict):
            rows: list[pd.DataFrame] = []
            for level, bucket in keep_remove.items():
                if isinstance(bucket, dict):
                    for key, df in bucket.items():
                        level_df = df.copy()
                        level_df.insert(0, "partition_key", key)
                        level_df.insert(0, "partition_level", level)
                        rows.append(level_df)
                elif isinstance(bucket, pd.DataFrame):
                    level_df = bucket.copy()
                    level_df.insert(0, "partition_key", "all")
                    level_df.insert(0, "partition_level", level)
                    rows.append(level_df)
            if rows:
                pd.concat(rows, ignore_index=True).to_csv(
                    self.output_dir / "analysis_keep_remove.csv",
                    index=False,
                )


def main() -> None:
    dataloader = Dataloader()
    df = dataloader.get_latest_mirrorview_run_data()
    df = dataloader.transform_latest_mirrorview_run_data(df)

    analyzer = LengthCompressionAnalyzer(df)
    analyzer.export_metric_labels()
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()
    analyzer.show_results()
    analyzer.save_results()


if __name__ == "__main__":
    main()
