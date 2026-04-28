"""Aggregation and DataFrame shaping for metric-based text analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np
import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import (
    ID_COLUMNS,
    coerce_phase,
    normalize_condition,
    normalize_party,
    normalize_text,
    rows_both_posts_shown,
    safe_divide,
)


class TextMetric(Protocol):
    @property
    def name(self) -> str: ...

    def calculate(self, text: str) -> float: ...


@dataclass(frozen=True)
class MetricCalculation:
    """One named metric summarized as a mean per analysis partition."""

    name: str
    by_partition: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        return dict(self.by_partition)


@dataclass(frozen=True)
class PairwiseAnalysisResult:
    """Pairwise row-level metrics plus partitioned means for ratio metrics."""

    dataframe: pd.DataFrame
    partition_means: dict[str, MetricCalculation]


@dataclass(frozen=True)
class LengthCompressionResults:
    """All result objects produced by the length/compression analysis."""

    original_text: dict[str, MetricCalculation]
    mirror_text: dict[str, MetricCalculation]
    pairwise: PairwiseAnalysisResult
    keep_remove: dict[str, Any]


def metrics_dict_for_text(text: str, metrics: Sequence[TextMetric]) -> dict[str, float]:
    """All named scalar metrics for one string (pairwise row construction)."""
    return {m.name: float(m.calculate(text)) for m in metrics}


class MetricAggregator:
    """Compute metric summaries and row-level pairwise outputs."""

    def __init__(self, df: pd.DataFrame, metrics: Sequence[TextMetric]) -> None:
        self.df = df
        self.metrics = tuple(metrics)

    def original_text_analysis(self) -> dict[str, MetricCalculation]:
        """Per-metric means by party×condition, party-only, condition-only, and global."""
        base = self._df_for_partitions(self.df)
        original_text = base["original_text"].map(normalize_text)
        return {
            metric.name: self._metric_calculation(
                metric.name, original_text.map(metric.calculate), base
            )
            for metric in self.metrics
        }

    def mirror_text_analysis(self) -> dict[str, MetricCalculation]:
        """Mirror metrics on trials where both posts are shown (same gate as pairwise)."""
        eligible = self._filter_pairwise_eligible(self.df)
        base = self._df_for_partitions(eligible)
        mirror_text = base["mirror_text"].map(normalize_text)
        return {
            metric.name: self._metric_calculation(
                metric.name, mirror_text.map(metric.calculate), base
            )
            for metric in self.metrics
        }

    def pairwise_analysis(self) -> PairwiseAnalysisResult:
        """Pairwise rows only when original+mirror text exist and design shows both posts."""
        filtered = self._filter_pairwise_eligible(self.df)
        pairwise_df = self._build_pairwise_dataframe(filtered)
        metric_cols = [
            col
            for col in pairwise_df.columns
            if col.startswith("ratio_") and col not in ("original_text", "mirror_text")
        ]
        partition_means: dict[str, MetricCalculation] = {}
        base = self._df_for_partitions(pairwise_df)
        for col in metric_cols:
            partition_means[col] = self._metric_calculation(
                col, pairwise_df[col].astype(float), base
            )
        return PairwiseAnalysisResult(dataframe=pairwise_df, partition_means=partition_means)

    def keep_remove_analysis(self, pairwise_df: pd.DataFrame) -> dict[str, Any]:
        """Keep/remove aggregates by party×condition×phase, plus coarser partition levels."""
        return self._keep_remove_by_partitions(pairwise_df)

    def run_all(self) -> LengthCompressionResults:
        """Run the full aggregation pipeline and return typed results."""
        original_text = self.original_text_analysis()
        mirror_text = self.mirror_text_analysis()
        pairwise = self.pairwise_analysis()
        keep_remove = self.keep_remove_analysis(pairwise.dataframe)
        return LengthCompressionResults(
            original_text=original_text,
            mirror_text=mirror_text,
            pairwise=pairwise,
            keep_remove=keep_remove,
        )

    def _metric_calculation(
        self, metric_name: str, values: pd.Series, base_df: pd.DataFrame
    ) -> MetricCalculation:
        return MetricCalculation(metric_name, self._partition_metric_means(values, base_df))

    def _df_for_partitions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rows with non-empty party_group and condition for core party×condition splits."""
        out = df.copy()
        party_group = out["party_group"].fillna("").astype(str).str.strip()
        condition = out["condition"].fillna("").astype(str).str.strip()
        mask = party_group.ne("") & condition.ne("")
        return out.loc[mask].copy()

    def _partition_metric_means(self, values: pd.Series, base_df: pd.DataFrame) -> dict[str, float]:
        """Means keyed by party_condition, party_all, all_condition, and all."""
        s = values.astype(float)
        d = base_df.loc[s.index].copy()
        s = s.loc[d.index]
        d["_party"] = d["party_group"].map(normalize_party)
        d["_cond"] = d["condition"].map(normalize_condition)

        out: dict[str, float] = {}

        for (party, condition), grp in d.groupby(["_party", "_cond"], sort=True):
            if not party or not condition:
                continue
            out[f"{party}_{condition}"] = float(s.loc[grp.index].mean())

        for party, grp in d.groupby("_party", sort=True):
            if not party:
                continue
            out[f"{party}_all"] = float(s.loc[grp.index].mean())

        for condition, grp in d.groupby("_cond", sort=True):
            if not condition:
                continue
            out[f"all_{condition}"] = float(s.loc[grp.index].mean())

        out["all"] = float(s.mean())
        overall = out.pop("all")
        ordered = dict(sorted(out.items(), key=lambda kv: kv[0]))
        ordered["all"] = overall
        return ordered

    def _filter_both_original_and_mirror_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rows where both ``original_text`` and ``mirror_text`` are non-empty after strip."""
        filtered = df.copy()
        orig_ok = filtered["original_text"].fillna("").astype(str).str.strip().ne("")
        mir_ok = filtered["mirror_text"].fillna("").astype(str).str.strip().ne("")
        return filtered.loc[orig_ok & mir_ok].copy()

    def _filter_pairwise_eligible(self, df: pd.DataFrame) -> pd.DataFrame:
        """Both texts non-empty and UI shows both posts (linked_fate or assisted)."""
        both = self._filter_both_original_and_mirror_text(df)
        return both.loc[rows_both_posts_shown(both)].copy()

    def _build_pairwise_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        present_id_cols = [col for col in ID_COLUMNS if col in df.columns]

        for _, row in df.iterrows():
            original_text = normalize_text(row.get("original_text", ""))
            mirror_text = normalize_text(row.get("mirror_text", ""))

            original_metrics = metrics_dict_for_text(original_text, self.metrics)
            mirror_metrics = metrics_dict_for_text(mirror_text, self.metrics)

            record: dict[str, Any] = {}
            for col in present_id_cols:
                record[col] = row[col]

            record["original_text"] = original_text
            record["mirror_text"] = mirror_text

            for metric_name, value in original_metrics.items():
                record[f"original_{metric_name}"] = value
            for metric_name, value in mirror_metrics.items():
                record[f"mirror_{metric_name}"] = value

            for metric in self.metrics:
                metric_name = metric.name
                original_value = float(original_metrics[metric_name])
                mirror_value = float(mirror_metrics[metric_name])
                record[f"ratio_{metric_name}"] = safe_divide(mirror_value, original_value)

            rows.append(record)

        pairwise_df = pd.DataFrame(rows)
        return pairwise_df.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    def _aggregate_for_group(
        self, pairwise_df: pd.DataFrame, group_name: str, group_value: str
    ) -> pd.DataFrame:
        metric_columns = [
            col
            for col in pairwise_df.columns
            if col.startswith(("original_", "mirror_", "ratio_"))
            and col not in ("original_text", "mirror_text")
        ]
        summary = pairwise_df[metric_columns].mean(numeric_only=True).to_frame().T
        summary.insert(0, "group_name", group_name)
        summary.insert(1, "group_value", str(group_value))
        summary.insert(2, "pair_count", int(len(pairwise_df)))
        return summary

    def _build_keep_remove_dataframe(self, pairwise_df: pd.DataFrame) -> pd.DataFrame:
        if "decision" not in pairwise_df.columns:
            return self._aggregate_for_group(pairwise_df, "decision", "missing")

        keep_remove = pairwise_df[
            pairwise_df["decision"].astype(str).str.lower().isin(["keep", "remove"])
        ].copy()
        if keep_remove.empty:
            return self._aggregate_for_group(pairwise_df, "decision", "no_keep_remove_rows")

        frames = []
        for decision_value, group_df in keep_remove.groupby(
            keep_remove["decision"].astype(str).str.lower(), sort=False
        ):
            frames.append(self._aggregate_for_group(group_df, "decision", decision_value))
        return pd.concat(frames, ignore_index=True)

    def _keep_remove_by_partitions(self, pairwise_df: pd.DataFrame) -> dict[str, Any]:
        d = pairwise_df.copy()
        d["_party"] = d["party_group"].map(normalize_party)
        d["_cond"] = d["condition"].map(normalize_condition)
        d["_phase"] = d["phase"].map(coerce_phase)

        out: dict[str, Any] = {}

        finest: dict[str, pd.DataFrame] = {}
        for (party, condition, phase), grp in d.groupby(["_party", "_cond", "_phase"], sort=True):
            if not party or not condition or phase is None or (isinstance(phase, float) and np.isnan(phase)):
                continue
            key = f"{party}_{condition}_p{int(phase)}"
            finest[key] = self._build_keep_remove_dataframe(grp)
        out["by_party_condition_phase"] = dict(sorted(finest.items(), key=lambda kv: kv[0]))

        by_pc: dict[str, pd.DataFrame] = {}
        for (party, condition), grp in d.groupby(["_party", "_cond"], sort=True):
            if not party or not condition:
                continue
            by_pc[f"{party}_{condition}"] = self._build_keep_remove_dataframe(grp)
        out["by_party_condition"] = dict(sorted(by_pc.items(), key=lambda kv: kv[0]))

        by_p: dict[str, pd.DataFrame] = {}
        for party, grp in d.groupby("_party", sort=True):
            if not party:
                continue
            by_p[f"{party}_all"] = self._build_keep_remove_dataframe(grp)
        out["by_party"] = dict(sorted(by_p.items(), key=lambda kv: kv[0]))

        by_c: dict[str, pd.DataFrame] = {}
        for condition, grp in d.groupby("_cond", sort=True):
            if not condition:
                continue
            by_c[f"all_{condition}"] = self._build_keep_remove_dataframe(grp)
        out["by_condition"] = dict(sorted(by_c.items(), key=lambda kv: kv[0]))

        out["all"] = self._build_keep_remove_dataframe(d)
        return out
