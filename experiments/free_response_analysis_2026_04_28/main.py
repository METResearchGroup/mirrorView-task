"""Phase 1 free-response reflections and influence-rating analysis.

Filters pilot study rows with populated reflection text and influence ratings,
prints party × condition summaries, and writes diagnostic plots.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/free_response_analysis_2026_04_28/main.py
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_1_RESULTS_PILOT


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
FILTERED_CSV = SCRIPT_DIR / "phase1_free_response_filtered.csv"
PLOTS_DIR = SCRIPT_DIR / "plots"

REFLECTION_COL = "phase1_pair_reflection_text"
INFLUENCE_COL = "phase1_pair_influence_rating"
PARTY_ORDER = ["democrat", "republican"]
CONDITION_ORDER = ["training", "training_assisted"]
CONDITION_DISPLAY = {"training": "training", "training_assisted": "training-assisted"}
PARTY_COLORS = {"democrat": "#4C78A8", "republican": "#F58518"}
GROUP_LABELS = {
    (party, condition): f"{party.title()}\n{CONDITION_DISPLAY[condition]}"
    for party in PARTY_ORDER
    for condition in CONDITION_ORDER
}

WORD_RE = re.compile(r"\b[a-z][a-z']+\b", re.IGNORECASE)
SENTENCE_RE = re.compile(r"[.!?]+")

STOPWORDS = {
    "about", "after", "all", "also", "and", "any", "are", "because", "been", "being",
    "both", "but", "can", "could", "did", "does", "for", "from", "had", "has", "have",
    "how", "into", "its", "just", "more", "not", "only", "other", "our", "out", "own",
    "same", "she", "should", "some", "than", "that", "the", "their", "them", "there",
    "these", "they", "this", "those", "too", "was", "were", "what", "when", "whether",
    "which", "who", "with", "would", "you", "your",
}

THEME_PATTERNS = {
    "civility / harm": re.compile(
        r"\b(?:civility|civil|curse|cuss|cussing|hate|hateful|harm|harsh|insult|mean|"
        r"offensive|profane|profanity|rude|threat|threatening|toxic|violence|violent)\b",
        re.IGNORECASE,
    ),
    "evidence / truth": re.compile(
        r"\b(?:accurate|accuracy|evidence|fact|facts|false|lies?|misinformation|misleading|"
        r"truth|true|untrue)\b",
        re.IGNORECASE,
    ),
    "productive discussion": re.compile(
        r"\b(?:conversation|debate|discuss|discussion|productive|respect|respectful|"
        r"viewpoint|viewpoints)\b",
        re.IGNORECASE,
    ),
    "pair comparison": re.compile(
        r"\b(?:both|compared?|comparable|counterpart|mirror|pair|same|similar)\b",
        re.IGNORECASE,
    ),
    "personal agreement": re.compile(
        r"\b(?:agree|agreed|disagree|disagreed|belief|believe|opinion|opinions)\b",
        re.IGNORECASE,
    ),
}

PartyConditionGroup = tuple[tuple[str, str], pd.DataFrame]
PartyConditionGroups = list[PartyConditionGroup]


def normalize_condition(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def normalize_party(value: object) -> str:
    return str(value or "").strip().lower()


def normalize_party_condition_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize ``party_group`` and ``condition`` columns in place."""
    df["party_group"] = df["party_group"].map(normalize_party)
    df["condition"] = df["condition"].map(normalize_condition)
    return df


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if denominator <= 0 else float(numerator) / float(denominator)


def generate_filtered_dataframe(
    *,
    export_csv: Path = FILTERED_CSV,
) -> pd.DataFrame:
    """Build and export phase-1 rows with reflection text and influence ratings.

    Parameters
    ----------
    export_csv : Path, optional
        Destination for the filtered CSV (created if missing).

    Returns
    -------
    pandas.DataFrame
        Sorted subset with party, condition, reflection, and rating columns.

    Raises
    ------
    ValueError
        If the source dataset is missing required columns.
    """
    df = load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT, low_memory=False)
    required = {
        "prolific_id",
        "party_group",
        "condition",
        "phase",
        "trial_type",
        REFLECTION_COL,
        INFLUENCE_COL,
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Source CSV is missing required column(s): {', '.join(missing)}")

    phase = pd.to_numeric(df["phase"], errors="coerce")
    rating = pd.to_numeric(df[INFLUENCE_COL], errors="coerce")
    reflection = df[REFLECTION_COL].astype("string")
    filtered = df.loc[
        phase.eq(1) & reflection.notna() & reflection.str.strip().ne("") & rating.notna()
    ].copy()

    normalize_party_condition_columns(filtered)
    filtered[REFLECTION_COL] = filtered[REFLECTION_COL].astype(str).str.strip()
    filtered[INFLUENCE_COL] = pd.to_numeric(filtered[INFLUENCE_COL], errors="coerce")

    keep_cols = [
        "prolific_id",
        "party_group",
        "condition",
        "trial_type",
        "phase",
        REFLECTION_COL,
        INFLUENCE_COL,
    ]
    filtered = filtered.loc[:, keep_cols].sort_values(
        ["party_group", "condition", "prolific_id"], kind="stable"
    )
    export_csv.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(export_csv, index=False)
    return filtered


def load_filtered_dataframe(console: Console) -> pd.DataFrame:
    """Return cached filtered rows, generating the CSV from the registry if needed."""
    if FILTERED_CSV.exists():
        console.print(f"[dim]Using cached filtered data: {FILTERED_CSV}[/dim]")
        return pd.read_csv(FILTERED_CSV)

    console.print(f"[dim]Creating filtered data: {FILTERED_CSV}[/dim]")
    return generate_filtered_dataframe()


def add_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """Attach length, sentence, and keyword-theme columns for analysis tables and plots.

    Returns a copy; the input frame is not modified.
    """
    out = df.copy()
    text = out[REFLECTION_COL].fillna("").astype(str)
    tokens = text.map(lambda value: WORD_RE.findall(value.lower()))
    sentence_counts = text.map(
        lambda value: sum(1 for s in SENTENCE_RE.split(value) if s.strip())
    )

    out["char_count"] = text.str.len()
    out["word_count"] = tokens.map(len)
    out["sentence_count"] = sentence_counts
    denom = out["sentence_count"].where(out["sentence_count"] > 0)
    out["avg_sentence_words"] = (out["word_count"] / denom).fillna(0.0)

    for theme, pattern in THEME_PATTERNS.items():
        out[f"theme__{theme}"] = text.str.contains(pattern, regex=True)

    return out


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "-"
        return f"{value:.{digits}f}"
    return str(value)


def party_condition_cells(party: object, condition: object) -> tuple[str, str]:
    """Return display labels for a party × condition table row."""
    party_s = str(party)
    condition_s = str(condition)
    return party_s, CONDITION_DISPLAY.get(condition_s, condition_s)


def party_condition_groups(df: pd.DataFrame) -> PartyConditionGroups:
    """Split rows into party × condition groups in canonical display order."""
    ordered = df.copy()
    ordered["party_group"] = pd.Categorical(
        ordered["party_group"], categories=PARTY_ORDER, ordered=True
    )
    ordered["condition"] = pd.Categorical(
        ordered["condition"], categories=CONDITION_ORDER, ordered=True
    )
    ordered = ordered.sort_values(["party_group", "condition"])
    return [
        ((str(party), str(condition)), group)
        for (party, condition), group in ordered.groupby(
            ["party_group", "condition"], observed=True, sort=False
        )
    ]


def make_table(title: str) -> Table:
    return Table(title=f"[bold]{title}[/bold]", box=box.ROUNDED, header_style="bold")


def render_overview(console: Console, df: pd.DataFrame) -> None:
    """Print global counts and mean/median influence and word-length stats."""
    table = make_table("Overview")
    table.add_column("Measure")
    table.add_column("Value", justify="right")
    table.add_row("Source dataset", STUDY_PHASE_2_PART_1_RESULTS_PILOT)
    table.add_row("Filtered CSV", str(FILTERED_CSV.relative_to(PROJECT_ROOT)))
    table.add_row("Filtered rows", f"{len(df):,}")
    table.add_row("Distinct users", f"{df['prolific_id'].nunique():,}")
    table.add_row("Party x condition cells", str(df.groupby(["party_group", "condition"]).ngroups))
    table.add_row("Mean influence rating", fmt(df[INFLUENCE_COL].mean()))
    table.add_row("Median influence rating", fmt(df[INFLUENCE_COL].median()))
    table.add_row("Mean words per reflection", fmt(df["word_count"].mean()))
    console.print(table)
    console.print()


def render_counts(console: Console, groups: PartyConditionGroups, n_rows: int) -> None:
    """Print row and user counts per party × condition cell."""
    table = make_table("Rows and users by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Rows", justify="right")
    table.add_column("Users", justify="right")
    table.add_column("Share of rows", justify="right")

    for (party, condition), group in groups:
        table.add_row(
            *party_condition_cells(party, condition),
            f"{len(group):,}",
            f"{group['prolific_id'].nunique():,}",
            fmt(safe_divide(len(group), n_rows)),
        )
    console.print(table)
    console.print()


def render_rating_summary(console: Console, groups: PartyConditionGroups) -> None:
    """Print mean/median/SD and low/mid/high share of influence ratings."""
    table = make_table("Influence rating summary by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("n", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("SD", justify="right")
    table.add_column("Low (1-3)", justify="right")
    table.add_column("Mid (4)", justify="right")
    table.add_column("High (5-7)", justify="right")

    for (party, condition), group in groups:
        ratings = group[INFLUENCE_COL]
        n = len(group)
        table.add_row(
            *party_condition_cells(party, condition),
            f"{n:,}",
            fmt(ratings.mean()),
            fmt(ratings.median()),
            fmt(ratings.std()),
            fmt(safe_divide(int(ratings.between(1, 3).sum()), n)),
            fmt(safe_divide(int(ratings.eq(4).sum()), n)),
            fmt(safe_divide(int(ratings.between(5, 7).sum()), n)),
        )
    console.print(table)
    console.print()


def render_rating_distribution(console: Console, groups: PartyConditionGroups) -> None:
    """Print raw counts for each influence rating value 1–7."""
    table = make_table("Influence rating distribution by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    for rating in range(1, 8):
        table.add_column(str(rating), justify="right")

    for (party, condition), group in groups:
        counts = group[INFLUENCE_COL].round().astype(int).value_counts()
        table.add_row(
            *party_condition_cells(party, condition),
            *[f"{int(counts.get(rating, 0)):,}" for rating in range(1, 8)],
        )
    console.print(table)
    console.print()


def render_text_summary(console: Console, groups: PartyConditionGroups) -> None:
    """Print reflection length statistics per party × condition cell."""
    table = make_table("Reflection text summary by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Mean words", justify="right")
    table.add_column("Median words", justify="right")
    table.add_column("P75 words", justify="right")
    table.add_column("Mean chars", justify="right")
    table.add_column("Mean sentences", justify="right")
    table.add_column("Mean words / sentence", justify="right")

    for (party, condition), group in groups:
        table.add_row(
            *party_condition_cells(party, condition),
            fmt(group["word_count"].mean()),
            fmt(group["word_count"].median()),
            fmt(group["word_count"].quantile(0.75)),
            fmt(group["char_count"].mean()),
            fmt(group["sentence_count"].mean()),
            fmt(group["avg_sentence_words"].mean()),
        )
    console.print(table)
    console.print()


def render_theme_summary(console: Console, groups: PartyConditionGroups) -> None:
    """Print keyword-theme hit rates per party × condition cell."""
    table = make_table("Cursory theme mentions by party x condition")
    table.caption = "Cells are proportions of reflections whose text matched a simple keyword pattern."
    table.add_column("Party")
    table.add_column("Condition")
    for theme in THEME_PATTERNS:
        table.add_column(theme, justify="right")

    for (party, condition), group in groups:
        n = len(group)
        table.add_row(
            *party_condition_cells(party, condition),
            *[fmt(safe_divide(int(group[f"theme__{theme}"].sum()), n)) for theme in THEME_PATTERNS],
        )
    console.print(table)
    console.print()


def top_terms(group: pd.DataFrame, *, limit: int = 8) -> str:
    """Return the most frequent non-stopword tokens for a group, with counts."""
    counts: Counter[str] = Counter()
    for text in group[REFLECTION_COL].fillna("").astype(str):
        for token in WORD_RE.findall(text.lower()):
            if token in STOPWORDS or len(token) < 3:
                continue
            counts[token] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{token} ({count})" for token, count in ranked)


def render_top_terms(console: Console, groups: PartyConditionGroups) -> None:
    """Print frequent content words per party × condition cell."""
    table = make_table("Top non-stopword terms by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Top terms")

    for (party, condition), group in groups:
        table.add_row(
            *party_condition_cells(party, condition),
            top_terms(group),
        )
    console.print(table)
    console.print()


def truncate(text: str, *, max_chars: int = 115) -> str:
    one_line = " ".join(str(text).split())
    if len(one_line) <= max_chars:
        return one_line
    return one_line[: max_chars - 1].rstrip() + "..."


def render_examples(console: Console, groups: PartyConditionGroups) -> None:
    """Print one high-influence reflection per cell, nearest the group's median length."""
    table = make_table("Representative higher-influence examples")
    table.caption = (
        "One high-rating response per party x condition, selected nearest to the group's "
        "median word count."
    )
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Rating", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Reflection")

    for (party, condition), group in groups:
        median_words = group["word_count"].median()
        sample = (
            group.loc[group[INFLUENCE_COL].ge(5)]
            .assign(word_distance=lambda x: (x["word_count"] - median_words).abs())
            .sort_values([INFLUENCE_COL, "word_distance"], ascending=[False, True])
            .head(1)
        )
        if sample.empty:
            sample = (
                group.assign(word_distance=lambda x: (x["word_count"] - median_words).abs())
                .sort_values("word_distance")
                .head(1)
            )

        row = sample.iloc[0]
        table.add_row(
            *party_condition_cells(party, condition),
            fmt(float(row[INFLUENCE_COL]), digits=0),
            str(int(row["word_count"])),
            truncate(str(row[REFLECTION_COL])),
        )
    console.print(table)
    console.print()


def group_label(key: tuple[str, str]) -> str:
    return GROUP_LABELS.get(key, f"{key[0]}\n{CONDITION_DISPLAY.get(key[1], key[1])}")


def party_color(party: str) -> str:
    return PARTY_COLORS.get(party, "#9CA3AF")


def _save_fig(fig: plt.Figure, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_mean_influence_plot(groups: PartyConditionGroups) -> Path:
    """Save a bar chart of mean influence ratings with 95% CI whiskers."""
    keys = [key for key, _ in groups]
    means: list[float] = []
    ci95_half_widths: list[float] = []
    for _, group in groups:
        values = group[INFLUENCE_COL]
        means.append(float(values.mean()))
        std = float(values.std(ddof=1))
        n = int(values.shape[0])
        se = safe_divide(std, math.sqrt(n))
        ci95_half_widths.append(1.96 * se)
    colors = [party_color(party) for party, _ in keys]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bars = ax.bar(
        range(len(keys)),
        means,
        yerr=ci95_half_widths,
        capsize=6,
        ecolor="#374151",
        color=colors,
    )
    ax.set_title("Mean Phase 1 Pair-Reflection Influence Rating")
    ax.set_ylabel("Mean rating (1-7)")
    ax.set_ylim(0, 7)
    ax.set_xticks(range(len(keys)), [group_label(key) for key in keys])
    ax.grid(axis="y", alpha=0.25)
    for bar, mean in zip(bars, means, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, mean + 0.08, f"{mean:.2f}", ha="center", va="bottom")

    return _save_fig(fig, PLOTS_DIR / "mean_influence_by_party_condition.png")


def _save_group_boxplot(
    groups: PartyConditionGroups,
    column: str,
    *,
    title: str,
    ylabel: str,
    path: Path,
    ylim: tuple[float, float] | None = None,
    figsize: tuple[float, float] = (8.5, 5.2),
) -> Path:
    keys = [key for key, _ in groups]
    values = [group[column].to_numpy() for _, group in groups]

    fig, ax = plt.subplots(figsize=figsize)
    boxplot = ax.boxplot(
        values,
        tick_labels=[group_label(key) for key in keys],
        showfliers=False,
        patch_artist=True,
    )
    for box, key in zip(boxplot["boxes"], keys, strict=True):
        box.set_facecolor(party_color(key[0]))
        box.set_alpha(0.55)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    ax.grid(axis="y", alpha=0.25)
    return _save_fig(fig, path)


def save_rating_distribution_plot(groups: PartyConditionGroups) -> Path:
    """Save a party-colored boxplot of influence ratings."""
    return _save_group_boxplot(
        groups,
        INFLUENCE_COL,
        title="Rating Distribution (Box-and-Whisker)",
        ylabel="Influence rating (1-7)",
        path=PLOTS_DIR / "influence_rating_distribution.png",
        ylim=(1, 7),
        figsize=(9.5, 5.4),
    )


def save_word_count_boxplot(groups: PartyConditionGroups) -> Path:
    """Save a party-colored boxplot of reflection word counts."""
    return _save_group_boxplot(
        groups,
        "word_count",
        title="Reflection Length Distribution",
        ylabel="Words per reflection",
        path=PLOTS_DIR / "reflection_word_count_boxplot.png",
    )


def save_theme_heatmap(groups: PartyConditionGroups) -> Path:
    """Save a heatmap of within-row theme-share across party × condition cells."""
    keys = [key for key, _ in groups]
    themes = list(THEME_PATTERNS)
    matrix: list[list[float]] = []
    for _, group in groups:
        theme_counts = [int(group[f"theme__{theme}"].sum()) for theme in themes]
        total_mentions = sum(theme_counts)
        if total_mentions <= 0:
            matrix.append([0.0 for _ in themes])
        else:
            matrix.append([count / total_mentions for count in theme_counts])

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(max(row) for row in matrix) + 0.05)
    ax.set_title("Theme Share by Party x Condition")
    ax.set_xticks(range(len(themes)), themes, rotation=25, ha="right")
    ax.set_yticks(range(len(keys)), [group_label(key).replace("\n", " ") for key in keys])
    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", color="#111827")
    fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02, label="Row share")

    return _save_fig(fig, PLOTS_DIR / "theme_mentions_heatmap.png")


def save_plots(console: Console, groups: PartyConditionGroups) -> list[Path]:
    """Write all diagnostic plots under ``PLOTS_DIR`` and print their paths."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_paths = [
        save_mean_influence_plot(groups),
        save_rating_distribution_plot(groups),
        save_word_count_boxplot(groups),
        save_theme_heatmap(groups),
    ]
    console.print("[bold]Saved plots[/bold]")
    for path in plot_paths:
        console.print(f"[dim]- {path.relative_to(PROJECT_ROOT)}[/dim]")
    console.print()
    return plot_paths


def main() -> None:
    """Load filtered phase-1 responses, print summaries, and save diagnostic plots."""
    console = Console()
    df = load_filtered_dataframe(console)
    df[INFLUENCE_COL] = pd.to_numeric(df[INFLUENCE_COL], errors="coerce")
    normalize_party_condition_columns(df)
    df = add_text_features(df)
    groups = party_condition_groups(df)

    console.rule("[bold]Phase 1 Free-Response Analysis[/bold]")
    render_overview(console, df)
    render_counts(console, groups, len(df))
    render_rating_summary(console, groups)
    render_rating_distribution(console, groups)
    render_text_summary(console, groups)
    render_theme_summary(console, groups)
    render_top_terms(console, groups)
    render_examples(console, groups)
    save_plots(console, groups)


if __name__ == "__main__":
    main()
