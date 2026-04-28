"""Analysis of word count, post length, etc.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

ID_COLUMNS = [
    "prolific_id",
    "post_id",
    "party_group",
    "decision",
    "evaluation_mode",
    "phase",
    "condition",
]


@dataclass(frozen=True)
class MetricCalculation:
    """One named metric summarized as a mean per analysis partition."""

    name: str
    by_partition: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        return dict(self.by_partition)


class TextMetrics:
    """Per-string length/compression metrics; single interface for all text-derived scalars."""

    PUNCTUATION_RE = re.compile(r"[^\w\s]")
    WORD_RE = re.compile(r"\b\w+\b")
    SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

    @staticmethod
    def safe_divide(numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator / denominator)

    @classmethod
    def char_count(cls, text: str) -> float:
        return float(len(text))

    @classmethod
    def word_count(cls, text: str) -> float:
        return float(len(cls.WORD_RE.findall(text)))

    @classmethod
    def sentence_count(cls, text: str) -> float:
        parts = [part.strip() for part in cls.SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return float(len(parts))

    @classmethod
    def punctuation_count(cls, text: str) -> float:
        return float(len(cls.PUNCTUATION_RE.findall(text)))

    @classmethod
    def avg_sentence_length(cls, text: str) -> float:
        return cls.safe_divide(cls.word_count(text), cls.sentence_count(text))

    @classmethod
    def punctuation_density(cls, text: str) -> float:
        return cls.safe_divide(cls.punctuation_count(text), cls.char_count(text))

    @classmethod
    def metrics_dict(cls, text: str) -> dict[str, float]:
        """All standard text metrics for one string (used by pairwise rows)."""
        char_count = len(text)
        word_count = cls.word_count(text)
        sentence_count = cls.sentence_count(text)
        punctuation_count = cls.punctuation_count(text)
        avg_sentence_length = cls.safe_divide(word_count, sentence_count)
        punctuation_density = cls.safe_divide(punctuation_count, float(char_count) if char_count else 0.0)
        return {
            "char_count": float(char_count),
            "word_count": float(word_count),
            "sentence_count": float(sentence_count),
            "avg_sentence_length": avg_sentence_length,
            "punctuation_count": punctuation_count,
            "punctuation_density": punctuation_density,
        }


class LengthCompressionAnalyzer:
    """Length / compression metrics with design-aware pairwise filter and partition splits."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self._metric_functions: list[tuple[str, Callable[[str], float]]] = [
            ("char_count", TextMetrics.char_count),
            ("word_count", TextMetrics.word_count),
            ("sentence_count", TextMetrics.sentence_count),
            ("avg_sentence_length", TextMetrics.avg_sentence_length),
            ("punctuation_count", TextMetrics.punctuation_count),
            ("punctuation_density", TextMetrics.punctuation_density),
        ]
        self.results: dict[str, Any] = {
            "original_text_analysis": None,
            "mirror_text_analysis": None,
            "pairwise_analysis": None,
            "keep_remove_analysis": None,
        }

    def original_text_analysis(self) -> None:
        """Per-metric means by party×condition, party-only, condition-only, and global."""
        base = self._df_for_partitions(self.df)
        original_text = base["original_text"].map(self._normalize_text)
        self.results["original_text_analysis"] = {
            name: self._metric_calculation(name, original_text.map(fn), base)
            for name, fn in self._metric_functions
        }

    def mirror_text_analysis(self) -> None:
        """Mirror metrics on trials where both posts are shown (same gate as pairwise)."""
        eligible = self._filter_pairwise_eligible(self.df)
        base = self._df_for_partitions(eligible)
        mirror_text = base["mirror_text"].map(self._normalize_text)
        self.results["mirror_text_analysis"] = {
            name: self._metric_calculation(name, mirror_text.map(fn), base)
            for name, fn in self._metric_functions
        }

    def pairwise_analysis(self) -> None:
        """Pairwise rows only when original+mirror text exist and design shows both posts."""
        filtered = self._filter_pairwise_eligible(self.df)
        pairwise_df = self._build_pairwise_dataframe(filtered)
        metric_cols = [
            c
            for c in pairwise_df.columns
            if c.startswith(("delta_", "ratio_"))
            and c not in ("original_text", "mirror_text")
        ]
        part_means: dict[str, MetricCalculation] = {}
        base = self._df_for_partitions(pairwise_df)
        for col in metric_cols:
            part_means[col] = self._metric_calculation(col, pairwise_df[col].astype(float), base)
        self.results["pairwise_analysis"] = {
            "dataframe": pairwise_df,
            "partition_means": part_means,
        }

    def keep_remove_analysis(self) -> None:
        """Keep/remove aggregates by party×condition×phase, plus coarser partition levels."""
        packed = self.results["pairwise_analysis"]
        if not isinstance(packed, dict) or "dataframe" not in packed:
            raise RuntimeError("Run pairwise_analysis before keep_remove_analysis.")
        pairwise_df: pd.DataFrame = packed["dataframe"]
        self.results["keep_remove_analysis"] = self._keep_remove_by_partitions(pairwise_df)

    def show_results(self) -> None:
        """Print analysis outputs as tables."""
        orig = self.results["original_text_analysis"]
        mir = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if orig is not None:
            print("\n=== Original text — mean metric by partition ===")
            print(self._metric_calculations_to_frame(orig).to_string())

        if mir is not None:
            print("\n=== Mirror text — mean metric by partition ===")
            print(self._metric_calculations_to_frame(mir).to_string())

        if isinstance(pairwise, dict):
            pw_df = pairwise.get("dataframe")
            part_means = pairwise.get("partition_means") or {}
            if isinstance(pw_df, pd.DataFrame) and not pw_df.empty:
                text_cols = {"original_text", "mirror_text"}
                display_cols = [c for c in pw_df.columns if c not in text_cols][:18]
                print("\n=== Pairwise — sample rows (truncated columns) ===")
                print(pw_df[display_cols].head(12).to_string(index=True))
            if part_means:
                print("\n=== Pairwise — mean delta/ratio by partition ===")
                print(self._metric_calculations_to_frame(part_means).to_string())

        if isinstance(keep_remove, dict):
            print("\n=== Keep / remove — by party × condition × phase ===")
            self._print_nested_keep_remove(keep_remove.get("by_party_condition_phase", {}))
            print("\n=== Keep / remove — by party × condition (all phases) ===")
            self._print_nested_keep_remove(keep_remove.get("by_party_condition", {}))
            print("\n=== Keep / remove — by party (all conditions / phases) ===")
            self._print_nested_keep_remove(keep_remove.get("by_party", {}))
            print("\n=== Keep / remove — by condition (all parties / phases) ===")
            self._print_nested_keep_remove(keep_remove.get("by_condition", {}))
            print("\n=== Keep / remove — all rows ===")
            all_tbl = keep_remove.get("all")
            if isinstance(all_tbl, pd.DataFrame) and not all_tbl.empty:
                print(all_tbl.to_string(index=False))

    def save_results(self) -> None:
        """Persist results to disk (not implemented)."""
        pass

    # --- private helpers ---

    def _metric_calculation(
        self, metric_name: str, values: pd.Series, base_df: pd.DataFrame
    ) -> MetricCalculation:
        return MetricCalculation(metric_name, self._partition_metric_means(values, base_df))

    def _metric_calculations_to_frame(
        self, metrics: dict[str, MetricCalculation]
    ) -> pd.DataFrame:
        return self._partition_dict_to_frame({k: v.by_partition for k, v in metrics.items()})

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and np.isnan(value):
            return ""
        return str(value)

    def _normalize_party(self, value: Any) -> str:
        t = str(value or "").strip().lower()
        return t if t else ""

    def _normalize_condition(self, value: Any) -> str:
        t = str(value or "").strip().lower().replace("-", "_")
        return t if t else ""

    def _coerce_phase(self, value: Any) -> float | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        try:
            return float(int(float(str(value).strip())))
        except (TypeError, ValueError):
            return None

    def _rows_both_posts_shown(self, df: pd.DataFrame) -> pd.Series:
        """True when the trial shows original + mirror per study design (linked_fate or assisted)."""
        em = df["evaluation_mode"].fillna("").astype(str).str.strip().str.lower()
        return em.isin(["linked_fate", "assisted"])

    def _df_for_partitions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rows with non-empty party_group and condition for core party×condition splits."""
        out = df.copy()
        pg = out["party_group"].fillna("").astype(str).str.strip()
        cond = out["condition"].fillna("").astype(str).str.strip()
        mask = pg.ne("") & cond.ne("")
        return out.loc[mask].copy()

    def _partition_metric_means(self, values: pd.Series, base_df: pd.DataFrame) -> dict[str, float]:
        """Means keyed by party_condition, party_all, all_condition, and all."""
        s = values.astype(float)
        d = base_df.loc[s.index].copy()
        s = s.loc[d.index]
        d["_party"] = d["party_group"].map(self._normalize_party)
        d["_cond"] = d["condition"].map(self._normalize_condition)

        out: dict[str, float] = {}

        for (p, c), grp in d.groupby(["_party", "_cond"], sort=True):
            if not p or not c:
                continue
            out[f"{p}_{c}"] = float(s.loc[grp.index].mean())

        for p, grp in d.groupby("_party", sort=True):
            if not p:
                continue
            out[f"{p}_all"] = float(s.loc[grp.index].mean())

        for c, grp in d.groupby("_cond", sort=True):
            if not c:
                continue
            out[f"all_{c}"] = float(s.loc[grp.index].mean())

        out["all"] = float(s.mean())
        overall = out.pop("all")
        ordered = dict(sorted(out.items(), key=lambda kv: kv[0]))
        ordered["all"] = overall
        return ordered

    def _partition_dict_to_frame(self, metric_to_partitions: dict[str, dict[str, float]]) -> pd.DataFrame:
        all_keys: set[str] = set()
        for part in metric_to_partitions.values():
            all_keys.update(part.keys())
        index = sorted(k for k in all_keys if k != "all")
        if "all" in all_keys:
            index.append("all")
        return pd.DataFrame(
            {
                metric: [partitions.get(k, float("nan")) for k in index]
                for metric, partitions in metric_to_partitions.items()
            },
            index=index,
        )

    def _filter_both_original_and_mirror_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rows where both ``original_text`` and ``mirror_text`` are non-empty after strip."""
        filtered = df.copy()
        orig_ok = filtered["original_text"].fillna("").astype(str).str.strip().ne("")
        mir_ok = filtered["mirror_text"].fillna("").astype(str).str.strip().ne("")
        return filtered.loc[orig_ok & mir_ok].copy()

    def _filter_pairwise_eligible(self, df: pd.DataFrame) -> pd.DataFrame:
        """Both texts non-empty and UI shows both posts (linked_fate or assisted)."""
        both = self._filter_both_original_and_mirror_text(df)
        return both.loc[self._rows_both_posts_shown(both)].copy()

    def _build_pairwise_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        present_id_cols = [col for col in ID_COLUMNS if col in df.columns]

        for _, row in df.iterrows():
            original_text = self._normalize_text(row.get("original_text", ""))
            mirror_text = self._normalize_text(row.get("mirror_text", ""))

            original_metrics = TextMetrics.metrics_dict(original_text)
            mirror_metrics = TextMetrics.metrics_dict(mirror_text)

            record: dict[str, Any] = {}
            for col in present_id_cols:
                record[col] = row[col]

            record["original_text"] = original_text
            record["mirror_text"] = mirror_text

            for metric_name, value in original_metrics.items():
                record[f"original_{metric_name}"] = value
            for metric_name, value in mirror_metrics.items():
                record[f"mirror_{metric_name}"] = value

            for metric_name in original_metrics:
                original_value = float(original_metrics[metric_name])
                mirror_value = float(mirror_metrics[metric_name])
                delta = mirror_value - original_value
                ratio = TextMetrics.safe_divide(mirror_value, original_value)
                record[f"delta_{metric_name}"] = delta
                record[f"ratio_{metric_name}"] = ratio

            rows.append(record)

        pairwise_df = pd.DataFrame(rows)
        return pairwise_df.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    def _aggregate_for_group(
        self, pairwise_df: pd.DataFrame, group_name: str, group_value: str
    ) -> pd.DataFrame:
        metric_columns = [
            col
            for col in pairwise_df.columns
            if col.startswith(("original_", "mirror_", "delta_", "ratio_"))
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
        d["_party"] = d["party_group"].map(self._normalize_party)
        d["_cond"] = d["condition"].map(self._normalize_condition)
        d["_phase"] = d["phase"].map(self._coerce_phase)

        out: dict[str, Any] = {}

        finest: dict[str, pd.DataFrame] = {}
        for (p, c, ph), grp in d.groupby(["_party", "_cond", "_phase"], sort=True):
            if not p or not c or ph is None or (isinstance(ph, float) and np.isnan(ph)):
                continue
            key = f"{p}_{c}_p{int(ph)}"
            finest[key] = self._build_keep_remove_dataframe(grp)
        out["by_party_condition_phase"] = dict(sorted(finest.items(), key=lambda kv: kv[0]))

        by_pc: dict[str, pd.DataFrame] = {}
        for (p, c), grp in d.groupby(["_party", "_cond"], sort=True):
            if not p or not c:
                continue
            by_pc[f"{p}_{c}"] = self._build_keep_remove_dataframe(grp)
        out["by_party_condition"] = dict(sorted(by_pc.items(), key=lambda kv: kv[0]))

        by_p: dict[str, pd.DataFrame] = {}
        for p, grp in d.groupby("_party", sort=True):
            if not p:
                continue
            by_p[f"{p}_all"] = self._build_keep_remove_dataframe(grp)
        out["by_party"] = dict(sorted(by_p.items(), key=lambda kv: kv[0]))

        by_c: dict[str, pd.DataFrame] = {}
        for c, grp in d.groupby("_cond", sort=True):
            if not c:
                continue
            by_c[f"all_{c}"] = self._build_keep_remove_dataframe(grp)
        out["by_condition"] = dict(sorted(by_c.items(), key=lambda kv: kv[0]))

        out["all"] = self._build_keep_remove_dataframe(d)
        return out

    def _print_nested_keep_remove(self, mapping: dict[str, pd.DataFrame]) -> None:
        for key, tbl in mapping.items():
            print(f"\n-- {key} --")
            if isinstance(tbl, pd.DataFrame) and not tbl.empty:
                print(tbl.to_string(index=False))
            else:
                print("(empty)")


def main() -> None:
    dataloader = Dataloader()
    df = dataloader.get_latest_mirrorview_run_data()
    df = dataloader.transform_latest_mirrorview_run_data(df)

    analyzer = LengthCompressionAnalyzer(df)
    analyzer.original_text_analysis()
    analyzer.mirror_text_analysis()
    analyzer.pairwise_analysis()
    analyzer.keep_remove_analysis()

    analyzer.show_results()
    analyzer.save_results()


if __name__ == "__main__":
    main()
