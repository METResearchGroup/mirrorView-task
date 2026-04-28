"""Rich table rendering for mirrors content analysis outputs."""

from __future__ import annotations

import math
from typing import Any, Protocol, Sequence

import numpy as np
import pandas as pd
from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from experiments.mirrors_content_analysis_2026_04_24.analysis.analysis_utils import (
    CONDITION_DISPLAY_MAP,
    CONDITION_MARGINAL_ROW,
    CONDITION_ORDER,
    PARTY_CONDITION_TABLE_CAPTION,
    PARTY_MARGINAL_HEADER,
    PARTY_ORDER,
)


class MetricDefinition(Protocol):
    @property
    def name(self) -> str: ...

    def describe(self) -> str: ...


class MetricCalculationLike(Protocol):
    name: str
    by_partition: dict[str, float]


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
    """Infer party / condition axis labels from partition keys."""
    raw_parties = [
        k[: -len("_all")]
        for k in by_partition
        if k.endswith("_all") and not k.startswith("all_")
    ]
    raw_conds = [k[4:] for k in by_partition if k.startswith("all_") and k != "all" and len(k) > 4]
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
            if key == "all" or key.endswith("_all") or key.startswith("all_"):
                continue
            for p in party_list:
                prefix = f"{p}_"
                if key.startswith(prefix) and len(key) > len(prefix):
                    cond_stubs.add(key[len(prefix) :])
        conds = _order_known_first(list(cond_stubs), CONDITION_ORDER)

    return parties, conds


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


PAIRWISE_SAMPLE_LEAD_COLS = [
    "party_group",
    "condition",
    "phase",
    "decision",
    "evaluation_mode",
    "post_id",
    "prolific_id",
]


class TableRenderer:
    """Owns all Rich rendering for length/compression analysis results."""

    def __init__(
        self,
        metrics: Sequence[MetricDefinition],
        *,
        console: Console | None = None,
    ) -> None:
        self.metrics = tuple(metrics)
        self.console = console or Console()

    def render_metric_glossary(self) -> None:
        """Rich table: metric name vs prose definition."""
        self.console.rule("[bold]Metric definitions[/bold]")
        table = Table(
            title="[bold]Length / compression metrics — glossary[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold",
            title_style="bold",
        )
        table.add_column("Metric", style="bold", max_width=28, overflow="ellipsis", no_wrap=True)
        table.add_column("Description (what it measures and how it is calculated)", overflow="fold")
        for metric in self.metrics:
            table.add_row(escape(metric.name), escape(metric.describe()))
        self.console.print(table)
        self.console.print()

    def render_metric_calculations(
        self, section_title: str, metrics: dict[str, MetricCalculationLike]
    ) -> None:
        """Print one Rich table per metric (insertion order of ``metrics`` preserved)."""
        self.console.rule(f"[bold]{section_title}[/bold]")
        for calc in metrics.values():
            self.console.print(self.metric_calculation_table(calc))
            self.console.print()

    def metric_calculation_table(self, calc: MetricCalculationLike) -> Table:
        """Party × condition grid with row/column marginals and grand mean."""
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
        for cond in conds:
            label = CONDITION_DISPLAY_MAP.get(cond, cond.replace("_", "-"))
            table.add_column(label, justify="right", overflow="ellipsis")
        table.add_column(PARTY_MARGINAL_HEADER, justify="right")

        for party in parties:
            row: list[str] = [party]
            for cond in conds:
                row.append(_fmt_partition_cell(by.get(f"{party}_{cond}")))
            row.append(_fmt_partition_cell(by.get(f"{party}_all")))
            table.add_row(*row)

        footer = [CONDITION_MARGINAL_ROW]
        for cond in conds:
            footer.append(_fmt_partition_cell(by.get(f"all_{cond}")))
        footer.append(_fmt_partition_cell(by.get("all")))
        table.add_row(*footer, style="italic dim")
        return table

    def dataframe_table(
        self,
        df: pd.DataFrame,
        *,
        title: str | None = None,
        caption: str | None = None,
        max_rows: int | None = None,
    ) -> Table:
        """Render a DataFrame as a Rich ``Table``."""
        view = df.copy()
        if max_rows is not None:
            view = view.head(int(max_rows))

        table_width: int | None = None
        ncols = len(view.columns)
        if ncols > 12:
            try:
                w = self.console.size.width
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
            table.add_row(*[_fmt_dataframe_cell(row[col]) for col in view.columns])
        return table

    def render_dataframe(
        self,
        df: pd.DataFrame,
        *,
        title: str | None = None,
        caption: str | None = None,
        wide_split_threshold: int = 10,
    ) -> None:
        """Print one or more Rich tables; splits wide keep/remove summaries by metric family."""
        if df.empty:
            self.console.print(self.dataframe_table(df, title=title, caption=caption))
            self.console.print()
            return
        if _looks_like_keep_remove_summary(df) and len(df.columns) > wide_split_threshold:
            chunks = _summary_df_metric_chunks(df)
            for i, (sublabel, subdf) in enumerate(chunks):
                cap = caption if i == 0 else None
                if title:
                    subt = f"{title} — [bold]{sublabel}[/bold]"
                else:
                    subt = f"[bold]{sublabel}[/bold]"
                self.console.print(self.dataframe_table(subdf, title=subt, caption=cap))
            self.console.print()
            return
        self.console.print(self.dataframe_table(df, title=title, caption=caption))
        self.console.print()

    def render_nested_dataframe_mapping(
        self, section_title: str, mapping: dict[str, pd.DataFrame]
    ) -> None:
        """Print a section rule then one Rich table per partition key."""
        self.console.rule(f"[bold]{section_title}[/bold]")
        if not mapping:
            self.console.print("[dim](no partitions)[/dim]")
            self.console.print()
            return
        for key, table_df in mapping.items():
            if isinstance(table_df, pd.DataFrame):
                self.render_dataframe(table_df, title=f"[bold]{key}[/bold]")
            else:
                self.console.print(f"[bold]{key}[/bold]")
                self.console.print("[dim](not a DataFrame)[/dim]")
                self.console.print()

    def render_pairwise_sample(self, pairwise_df: pd.DataFrame) -> None:
        display_cols = pairwise_sample_display_columns(pairwise_df, max_cols=10)
        sample = pairwise_df[display_cols].head(12)
        self.console.rule("[bold]Pairwise — sample rows (first 12; curated columns)[/bold]")
        self.render_dataframe(
            sample,
            caption="[dim]Design columns + ratio_* metrics; omits full original/mirror text.[/dim]",
        )

    def render_keep_remove(self, keep_remove: dict[str, Any]) -> None:
        self.render_nested_dataframe_mapping(
            "Keep / remove — by party × condition × phase",
            keep_remove.get("by_party_condition_phase", {}) or {},
        )
        self.render_nested_dataframe_mapping(
            "Keep / remove — by party × condition (all phases)",
            keep_remove.get("by_party_condition", {}) or {},
        )
        self.render_nested_dataframe_mapping(
            "Keep / remove — by party (all conditions / phases)",
            keep_remove.get("by_party", {}) or {},
        )
        self.render_nested_dataframe_mapping(
            "Keep / remove — by condition (all parties / phases)",
            keep_remove.get("by_condition", {}) or {},
        )
        all_tbl = keep_remove.get("all")
        if isinstance(all_tbl, pd.DataFrame):
            self.console.rule("[bold]Keep / remove — all rows[/bold]")
            self.render_dataframe(all_tbl)


def pairwise_sample_display_columns(df: pd.DataFrame, *, max_cols: int = 10) -> list[str]:
    """Columns for pairwise preview: design fields first, then ratio_* metrics, then the rest."""
    text_cols = {"original_text", "mirror_text"}
    lead = [col for col in PAIRWISE_SAMPLE_LEAD_COLS if col in df.columns]
    rest = [col for col in df.columns if col not in text_cols and col not in lead]
    metrics_first = [col for col in rest if col.startswith("ratio_")]
    other = [col for col in rest if col not in metrics_first]
    ordered = lead + metrics_first + other
    return ordered[:max_cols]


def _looks_like_keep_remove_summary(df: pd.DataFrame) -> bool:
    return "group_name" in df.columns and "group_value" in df.columns


def _summary_df_metric_chunks(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Split wide keep/remove summary frames into readable blocks (shared ID columns)."""
    base_cols = [col for col in ("group_name", "group_value", "pair_count") if col in df.columns]
    specs: list[tuple[str, list[str]]] = [
        ("Original metrics", [col for col in df.columns if col.startswith("original_")]),
        ("Mirror metrics", [col for col in df.columns if col.startswith("mirror_")]),
        ("Ratio metrics", [col for col in df.columns if col.startswith("ratio_")]),
    ]
    out: list[tuple[str, pd.DataFrame]] = []
    used: set[str] = set(base_cols)
    for label, metric_cols in specs:
        if not metric_cols:
            continue
        used.update(metric_cols)
        out.append((label, df.loc[:, base_cols + metric_cols]))
    rest = [col for col in df.columns if col not in used]
    if rest:
        out.append(("Other columns", df.loc[:, base_cols + rest]))
    if not out:
        out.append(("Summary", df))
    return out
