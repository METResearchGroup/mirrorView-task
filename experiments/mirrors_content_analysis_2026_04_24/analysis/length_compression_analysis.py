"""Analysis of word count, post length, etc.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/length_compression_analysis.py
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

# Display / axis ordering (normalized keys match `_normalize_condition`: lower, "-" -> "_")
PARTY_ORDER = ["democrat", "republican"]
CONDITION_ORDER = ["control", "training", "training_assisted"]
CONDITION_DISPLAY_MAP = {
    "control": "control",
    "training": "training",
    "training_assisted": "training-assisted",
}
PARTY_MARGINAL_HEADER = "Party marginal"
CONDITION_MARGINAL_ROW = "Condition marginal"
PARTY_CONDITION_TABLE_CAPTION = (
    "[dim]Cells: party×condition means. Row margin: party pooled. "
    "Footer: condition pooled. Lower-right: overall mean (partition key all).[/dim]"
)

ID_COLUMNS = [
    "prolific_id",
    "post_id",
    "party_group",
    "decision",
    "evaluation_mode",
    "phase",
    "condition",
]


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


_WORD_RE = re.compile(r"\b\w+\b")
_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


class CalculateMetric(ABC):
    """Single-text scalar metric: stable ``name``, prose ``describe()``, and ``calculate()``."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier used in column names (e.g. ``char_count``)."""

    @abstractmethod
    def describe(self) -> str:
        """What the metric measures and exactly how it is computed from the input string."""

    @abstractmethod
    def calculate(self, text: str) -> float:
        """Return the metric value for one normalized post string."""


class CharCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "char_count"

    def describe(self) -> str:
        return (
            "Post length in characters. Counts every codepoint in the string after normalization "
            "(including spaces, punctuation, and line breaks). Formula: float(len(text))."
        )

    def calculate(self, text: str) -> float:
        return float(len(text))


class WordCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "word_count"

    def describe(self) -> str:
        return (
            "Approximate word count via regex tokenization: count how many times the pattern "
            r"\b\w+\b matches (word characters bounded by word boundaries). "
            "Same notion as many simple NLP word counts; not full Unicode word segmentation."
        )

    def calculate(self, text: str) -> float:
        return float(len(_WORD_RE.findall(text)))


class SentenceCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "sentence_count"

    def describe(self) -> str:
        return (
            "Sentence count by splitting on one-or-more occurrences of ., !, or ?. "
            "Non-empty trimmed segments after the split are counted; empty runs are ignored."
        )

    def calculate(self, text: str) -> float:
        parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]
        return float(len(parts))


class AvgSentenceLengthMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "avg_sentence_length"

    def describe(self) -> str:
        return (
            "Mean words per sentence for this post. Computed as word_count / sentence_count "
            "using the same word and sentence definitions as the separate word and sentence metrics; "
            "0 if sentence_count is 0 (avoids division by zero)."
        )

    def calculate(self, text: str) -> float:
        wc = float(len(_WORD_RE.findall(text)))
        parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]
        sc = float(len(parts))
        return safe_divide(wc, sc)


class PunctuationCountMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "punctuation_count"

    def describe(self) -> str:
        return (
            "Count of punctuation-like characters: each match of the regex [^\\w\\s] "
            "(not a word character, not whitespace) counts as one punctuation token."
        )

    def calculate(self, text: str) -> float:
        return float(len(_PUNCTUATION_RE.findall(text)))


class PunctuationDensityMetric(CalculateMetric):
    @property
    def name(self) -> str:
        return "punctuation_density"

    def describe(self) -> str:
        return (
            "Punctuation per character: punctuation_count / char_count for the same string, "
            "using the punctuation and character definitions above. 0 if the string has length 0."
        )

    def calculate(self, text: str) -> float:
        char_count = len(text)
        punct = float(len(_PUNCTUATION_RE.findall(text)))
        return safe_divide(punct, float(char_count) if char_count else 0.0)


DEFAULT_LENGTH_METRICS: tuple[CalculateMetric, ...] = (
    CharCountMetric(),
    WordCountMetric(),
    SentenceCountMetric(),
    AvgSentenceLengthMetric(),
    PunctuationCountMetric(),
    PunctuationDensityMetric(),
)


def metrics_dict_for_text(text: str, metrics: Sequence[CalculateMetric]) -> dict[str, float]:
    """All named scalar metrics for one string (pairwise row construction)."""
    return {m.name: float(m.calculate(text)) for m in metrics}


@dataclass(frozen=True)
class MetricCalculation:
    """One named metric summarized as a mean per analysis partition."""

    name: str
    by_partition: dict[str, float]

    def as_dict(self) -> dict[str, float]:
        return dict(self.by_partition)


def _fmt_partition_cell(value: float | None) -> str:
    if value is None:
        return "—"
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        return "—"
    return f"{v:.4g}"


def _order_known_first(values: list[str], preferred: list[str]) -> list[str]:
    uniq = list(dict.fromkeys(values))
    known = [x for x in preferred if x in uniq]
    tail = sorted(x for x in uniq if x not in known)
    return known + tail


def _axes_for_partition_table(by_partition: dict[str, float]) -> tuple[list[str], list[str]]:
    """Infer party / condition axis labels from keys produced by ``_partition_metric_means``."""
    raw_parties = [
        k[: -len("_all")]
        for k in by_partition
        if k.endswith("_all") and not k.startswith("all_")
    ]
    raw_conds = [k[4:] for k in by_partition if k.startswith("all_") and k not in ("all",) and len(k) > 4]
    parties = _order_known_first(raw_parties, PARTY_ORDER)
    conds = _order_known_first(raw_conds, CONDITION_ORDER)

    if not parties:
        for p in PARTY_ORDER:
            prefix = f"{p}_"
            if any(
                k.startswith(prefix)
                and not k.startswith("all_")
                and not k.endswith("_all")
                and k != "all"
                for k in by_partition
            ):
                parties.append(p)
        parties = _order_known_first(parties, PARTY_ORDER)

    if not conds:
        cond_stubs: set[str] = set()
        party_list = parties or list(PARTY_ORDER)
        for key in by_partition:
            if key in ("all",) or key.endswith("_all") or key.startswith("all_"):
                continue
            for p in party_list:
                prefix = f"{p}_"
                if key.startswith(prefix) and len(key) > len(prefix):
                    cond_stubs.add(key[len(prefix) :])
        conds = _order_known_first(list(cond_stubs), CONDITION_ORDER)

    return parties, conds


def rich_table_for_metric_calculation(calc: MetricCalculation) -> Table:
    """Party × condition grid with row/column marginals and grand mean from ``by_partition`` keys."""
    by = calc.by_partition
    parties, conds = _axes_for_partition_table(by)
    table = Table(
        title=f"[bold]{calc.name}[/bold] — mean",
        caption=PARTY_CONDITION_TABLE_CAPTION,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        title_style="bold",
    )

    if not parties or not conds:
        table.add_column("Note")
        table.add_row("Not enough party×condition partition keys to build a grid for this metric.")
        return table

    table.add_column("Party \\ condition", style="bold")
    for c in conds:
        label = CONDITION_DISPLAY_MAP.get(c, c.replace("_", "-"))
        table.add_column(label, justify="right", overflow="ellipsis")
    table.add_column(PARTY_MARGINAL_HEADER, justify="right")

    for p in parties:
        row: list[str] = [p]
        for c in conds:
            row.append(_fmt_partition_cell(by.get(f"{p}_{c}")))
        row.append(_fmt_partition_cell(by.get(f"{p}_all")))
        table.add_row(*row)

    footer = [CONDITION_MARGINAL_ROW]
    for c in conds:
        footer.append(_fmt_partition_cell(by.get(f"all_{c}")))
    footer.append(_fmt_partition_cell(by.get("all")))
    table.add_row(*footer, style="italic dim")
    return table


def print_metric_calculations_rich(
    console: Console, section_title: str, metrics: dict[str, MetricCalculation]
) -> None:
    """Print one Rich table per metric (insertion order of ``metrics`` preserved)."""
    console.rule(f"[bold]{section_title}[/bold]")
    for calc in metrics.values():
        console.print(rich_table_for_metric_calculation(calc))
        console.print()


def print_metric_glossary_rich(console: Console, metrics: Sequence[CalculateMetric]) -> None:
    """Rich table: metric name vs prose definition (printed first in ``show_results``)."""
    console.rule("[bold]Metric definitions[/bold]")
    table = Table(
        title="[bold]Length / compression metrics — glossary[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        title_style="bold",
    )
    table.add_column("Metric", style="bold", max_width=28, overflow="ellipsis", no_wrap=True)
    table.add_column("Description (what it measures and how it is calculated)", overflow="fold")
    for m in metrics:
        table.add_row(escape(m.name), escape(m.describe()))
    console.print(table)
    console.print()


def _fmt_dataframe_cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (float, np.floating)):
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "—"
        return f"{v:.4g}"
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (np.bool_, bool)):
        return str(bool(value))
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass
    return str(value)


def rich_table_from_dataframe(
    df: pd.DataFrame,
    *,
    title: str | None = None,
    caption: str | None = None,
    max_rows: int | None = None,
    console: Console | None = None,
) -> Table:
    """Render a DataFrame as a Rich ``Table`` (rounded box, bold headers).

    When ``console`` is set, the table gets an explicit ``width`` so Rich does
    not assign one-character columns on wide frames (which looks broken).
    """
    view = df.copy()
    if max_rows is not None:
        view = view.head(int(max_rows))

    table_width: int | None = None
    ncols = len(view.columns)
    if console is not None and ncols > 12:
        try:
            w = console.size.width
            table_width = max(72, min(220, w - 2))
        except Exception:
            table_width = 120

    table = Table(
        title=title,
        caption=caption,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        title_style="bold",
        width=table_width,
    )

    if view.empty:
        table.add_column(" ")
        table.add_row("[dim](empty)[/dim]")
        return table

    col_kwargs: dict[str, Any] = {"overflow": "ellipsis", "no_wrap": True}
    if ncols <= 14:
        col_kwargs["min_width"] = max(10, min(18, 120 // max(ncols, 1)))

    for col in view.columns:
        table.add_column(str(col), **col_kwargs)
    for _, row in view.iterrows():
        table.add_row(*[_fmt_dataframe_cell(row[c]) for c in view.columns])
    return table


PAIRWISE_SAMPLE_LEAD_COLS = [
    "party_group",
    "condition",
    "phase",
    "decision",
    "evaluation_mode",
    "post_id",
    "prolific_id",
]


def pairwise_sample_display_columns(df: pd.DataFrame, *, max_cols: int = 10) -> list[str]:
    """Columns for pairwise preview: design fields first, then ratio_* metrics, then the rest."""
    text_cols = {"original_text", "mirror_text"}
    lead = [c for c in PAIRWISE_SAMPLE_LEAD_COLS if c in df.columns]
    rest = [c for c in df.columns if c not in text_cols and c not in lead]
    metrics_first = [c for c in rest if c.startswith("ratio_")]
    other = [c for c in rest if c not in metrics_first]
    ordered = lead + metrics_first + other
    return ordered[:max_cols]


def _looks_like_keep_remove_summary(df: pd.DataFrame) -> bool:
    return "group_name" in df.columns and "group_value" in df.columns


def _summary_df_metric_chunks(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Split wide keep/remove summary frames into readable blocks (shared ID columns)."""
    base_cols = [c for c in ("group_name", "group_value", "pair_count") if c in df.columns]
    specs: list[tuple[str, list[str]]] = [
        ("Original metrics", [c for c in df.columns if c.startswith("original_")]),
        ("Mirror metrics", [c for c in df.columns if c.startswith("mirror_")]),
        ("Ratio metrics", [c for c in df.columns if c.startswith("ratio_")]),
    ]
    out: list[tuple[str, pd.DataFrame]] = []
    used: set[str] = set(base_cols)
    for label, mcols in specs:
        if not mcols:
            continue
        used.update(mcols)
        out.append((label, df.loc[:, base_cols + mcols]))
    rest = [c for c in df.columns if c not in used]
    if rest:
        out.append(("Other columns", df.loc[:, base_cols + rest]))
    if not out:
        out.append(("Summary", df))
    return out


def print_dataframe_rich(
    console: Console,
    df: pd.DataFrame,
    *,
    title: str | None = None,
    caption: str | None = None,
    wide_split_threshold: int = 10,
) -> None:
    """Print one or more Rich tables; splits wide keep/remove summaries by metric family."""
    if df.empty:
        console.print(rich_table_from_dataframe(df, title=title, caption=caption, console=console))
        console.print()
        return
    if _looks_like_keep_remove_summary(df) and len(df.columns) > wide_split_threshold:
        chunks = _summary_df_metric_chunks(df)
        for i, (sublabel, subdf) in enumerate(chunks):
            cap = caption if i == 0 else None
            if title:
                subt = f"{title} — [bold]{sublabel}[/bold]"
            else:
                subt = f"[bold]{sublabel}[/bold]"
            console.print(rich_table_from_dataframe(subdf, title=subt, caption=cap, console=console))
        console.print()
        return
    console.print(rich_table_from_dataframe(df, title=title, caption=caption, console=console))
    console.print()


def print_nested_dataframe_mapping_rich(
    console: Console, section_title: str, mapping: dict[str, pd.DataFrame]
) -> None:
    """Print a section rule then one Rich table per partition key (keep/remove style)."""
    console.rule(f"[bold]{section_title}[/bold]")
    if not mapping:
        console.print("[dim](no partitions)[/dim]")
        console.print()
        return
    for key, tbl in mapping.items():
        if isinstance(tbl, pd.DataFrame):
            print_dataframe_rich(console, tbl, title=f"[bold]{key}[/bold]")
        else:
            console.print(f"[bold]{key}[/bold]")
            console.print("[dim](not a DataFrame)[/dim]")
            console.print()


class LengthCompressionAnalyzer:
    """Length / compression metrics with design-aware pairwise filter and partition splits."""

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
            m.name: self._metric_calculation(m.name, original_text.map(m.calculate), base)
            for m in self._metrics
        }

    def mirror_text_analysis(self) -> None:
        """Mirror metrics on trials where both posts are shown (same gate as pairwise)."""
        eligible = self._filter_pairwise_eligible(self.df)
        base = self._df_for_partitions(eligible)
        mirror_text = base["mirror_text"].map(self._normalize_text)
        self.results["mirror_text_analysis"] = {
            m.name: self._metric_calculation(m.name, mirror_text.map(m.calculate), base)
            for m in self._metrics
        }

    def pairwise_analysis(self) -> None:
        """Pairwise rows only when original+mirror text exist and design shows both posts."""
        filtered = self._filter_pairwise_eligible(self.df)
        pairwise_df = self._build_pairwise_dataframe(filtered)
        metric_cols = [
            c
            for c in pairwise_df.columns
            if c.startswith("ratio_") and c not in ("original_text", "mirror_text")
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
        console = Console()
        print_metric_glossary_rich(console, self._metrics)
        orig = self.results["original_text_analysis"]
        mir = self.results["mirror_text_analysis"]
        pairwise = self.results["pairwise_analysis"]
        keep_remove = self.results["keep_remove_analysis"]

        if orig is not None:
            print_metric_calculations_rich(
                console,
                "Original text — means by party × condition (+ marginals)",
                orig,
            )

        if mir is not None:
            print_metric_calculations_rich(
                console,
                "Mirror text — means by party × condition (+ marginals)",
                mir,
            )

        if isinstance(pairwise, dict):
            pw_df = pairwise.get("dataframe")
            part_means = pairwise.get("partition_means") or {}
            if isinstance(pw_df, pd.DataFrame) and not pw_df.empty:
                display_cols = pairwise_sample_display_columns(pw_df, max_cols=10)
                sample = pw_df[display_cols].head(12)
                console.rule("[bold]Pairwise — sample rows (first 12; curated columns)[/bold]")
                print_dataframe_rich(
                    console,
                    sample,
                    caption="[dim]Design columns + ratio_* metrics; omits full original/mirror text.[/dim]",
                )
            if part_means:
                print_metric_calculations_rich(
                    console,
                    "Pairwise — mean ratio by party × condition (+ marginals)",
                    part_means,
                )

        if isinstance(keep_remove, dict):
            print_nested_dataframe_mapping_rich(
                console,
                "Keep / remove — by party × condition × phase",
                keep_remove.get("by_party_condition_phase", {}) or {},
            )
            print_nested_dataframe_mapping_rich(
                console,
                "Keep / remove — by party × condition (all phases)",
                keep_remove.get("by_party_condition", {}) or {},
            )
            print_nested_dataframe_mapping_rich(
                console,
                "Keep / remove — by party (all conditions / phases)",
                keep_remove.get("by_party", {}) or {},
            )
            print_nested_dataframe_mapping_rich(
                console,
                "Keep / remove — by condition (all parties / phases)",
                keep_remove.get("by_condition", {}) or {},
            )
            all_tbl = keep_remove.get("all")
            if isinstance(all_tbl, pd.DataFrame):
                console.rule("[bold]Keep / remove — all rows[/bold]")
                print_dataframe_rich(console, all_tbl)

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

            original_metrics = metrics_dict_for_text(original_text, self._metrics)
            mirror_metrics = metrics_dict_for_text(mirror_text, self._metrics)

            record: dict[str, Any] = {}
            for col in present_id_cols:
                record[col] = row[col]

            record["original_text"] = original_text
            record["mirror_text"] = mirror_text

            for metric_name, value in original_metrics.items():
                record[f"original_{metric_name}"] = value
            for metric_name, value in mirror_metrics.items():
                record[f"mirror_{metric_name}"] = value

            for m in self._metrics:
                metric_name = m.name
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


def run_analysis(
    df: pd.DataFrame,
    output_dir: Path,
    run_timestamp: str,
    dataset_path: str,
    formats: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Write length-compression artifacts for the mirrors CLI (delegates to v1 I/O)."""
    from .v1_length_compression_analysis import run_analysis as run_analysis_v1

    return run_analysis_v1(df, output_dir, run_timestamp, dataset_path, formats)


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
