"""Analyze phase 1 free-response reflections and influence ratings.

To run:

PYTHONPATH=. uv run python experiments/free_response_analysis_2026_04_28/main.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SOURCE_CSV = PROJECT_ROOT / "scripts" / "mirrorview_pilot_data_2026_04_28-16:31:47.csv"
FILTERED_CSV = SCRIPT_DIR / "phase1_free_response_filtered.csv"
PLOTS_DIR = SCRIPT_DIR / "plots"

REFLECTION_COL = "phase1_pair_reflection_text"
INFLUENCE_COL = "phase1_pair_influence_rating"
PARTY_ORDER = ["democrat", "republican"]
CONDITION_ORDER = ["training", "training_assisted"]
CONDITION_DISPLAY = {"training": "training", "training_assisted": "training-assisted"}
GROUP_LABELS = {
    ("democrat", "training"): "Democrat\ntraining",
    ("democrat", "training_assisted"): "Democrat\ntraining-assisted",
    ("republican", "training"): "Republican\ntraining",
    ("republican", "training_assisted"): "Republican\ntraining-assisted",
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


def normalize_condition(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def normalize_party(value: object) -> str:
    return str(value or "").strip().lower()


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if denominator <= 0 else float(numerator) / float(denominator)


def generate_filtered_dataframe(
    source_csv: Path = SOURCE_CSV,
    *,
    export_csv: Path = FILTERED_CSV,
) -> pd.DataFrame:
    """Create and export rows with populated phase 1 reflection text and influence rating."""
    if not source_csv.exists():
        raise FileNotFoundError(f"Source CSV not found: {source_csv}")

    df = pd.read_csv(source_csv, low_memory=False)
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

    filtered["party_group"] = filtered["party_group"].map(normalize_party)
    filtered["condition"] = filtered["condition"].map(normalize_condition)
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
    """Read the cached filtered CSV, creating it from the raw export if needed."""
    if FILTERED_CSV.exists():
        console.print(f"[dim]Using cached filtered data: {FILTERED_CSV}[/dim]")
        return pd.read_csv(FILTERED_CSV)

    console.print(f"[dim]Creating filtered data: {FILTERED_CSV}[/dim]")
    return generate_filtered_dataframe()


def add_text_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    text = out[REFLECTION_COL].fillna("").astype(str)
    tokens = text.map(lambda value: WORD_RE.findall(value.lower()))
    sentence_counts = text.map(lambda value: len([s for s in SENTENCE_RE.split(value) if s.strip()]))

    out["char_count"] = text.str.len()
    out["word_count"] = tokens.map(len)
    out["sentence_count"] = sentence_counts
    out["avg_sentence_words"] = [
        safe_divide(words, sentences)
        for words, sentences in zip(out["word_count"], out["sentence_count"], strict=True)
    ]
    out["question_mark_count"] = text.str.count(r"\?")
    out["exclamation_mark_count"] = text.str.count("!")
    out["token_list"] = tokens

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


def party_condition_groups(df: pd.DataFrame) -> Iterable[tuple[tuple[str, str], pd.DataFrame]]:
    ordered = df.copy()
    ordered["party_group"] = pd.Categorical(
        ordered["party_group"], categories=PARTY_ORDER, ordered=True
    )
    ordered["condition"] = pd.Categorical(
        ordered["condition"], categories=CONDITION_ORDER, ordered=True
    )
    ordered = ordered.sort_values(["party_group", "condition"])
    yield from ordered.groupby(["party_group", "condition"], observed=True, sort=False)


def make_table(title: str) -> Table:
    return Table(title=f"[bold]{title}[/bold]", box=box.ROUNDED, header_style="bold")


def render_overview(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Overview")
    table.add_column("Measure")
    table.add_column("Value", justify="right")
    table.add_row("Source CSV", SOURCE_CSV.name)
    table.add_row("Filtered CSV", str(FILTERED_CSV.relative_to(PROJECT_ROOT)))
    table.add_row("Filtered rows", f"{len(df):,}")
    table.add_row("Distinct users", f"{df['prolific_id'].nunique():,}")
    table.add_row("Party x condition cells", str(df.groupby(["party_group", "condition"]).ngroups))
    table.add_row("Mean influence rating", fmt(df[INFLUENCE_COL].mean()))
    table.add_row("Median influence rating", fmt(df[INFLUENCE_COL].median()))
    table.add_row("Mean words per reflection", fmt(df["word_count"].mean()))
    console.print(table)
    console.print()


def render_counts(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Rows and users by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Rows", justify="right")
    table.add_column("Users", justify="right")
    table.add_column("Share of rows", justify="right")

    for (party, condition), group in party_condition_groups(df):
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            f"{len(group):,}",
            f"{group['prolific_id'].nunique():,}",
            fmt(safe_divide(len(group), len(df))),
        )
    console.print(table)
    console.print()


def render_rating_summary(console: Console, df: pd.DataFrame) -> None:
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

    for (party, condition), group in party_condition_groups(df):
        ratings = group[INFLUENCE_COL]
        n = len(group)
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
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


def render_rating_distribution(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Influence rating distribution by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    for rating in range(1, 8):
        table.add_column(str(rating), justify="right")

    for (party, condition), group in party_condition_groups(df):
        counts = group[INFLUENCE_COL].round().astype(int).value_counts()
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            *[f"{int(counts.get(rating, 0)):,}" for rating in range(1, 8)],
        )
    console.print(table)
    console.print()


def render_text_summary(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Reflection text summary by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Mean words", justify="right")
    table.add_column("Median words", justify="right")
    table.add_column("P75 words", justify="right")
    table.add_column("Mean chars", justify="right")
    table.add_column("Mean sentences", justify="right")
    table.add_column("Mean words / sentence", justify="right")

    for (party, condition), group in party_condition_groups(df):
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            fmt(group["word_count"].mean()),
            fmt(group["word_count"].median()),
            fmt(group["word_count"].quantile(0.75)),
            fmt(group["char_count"].mean()),
            fmt(group["sentence_count"].mean()),
            fmt(group["avg_sentence_words"].mean()),
        )
    console.print(table)
    console.print()


def render_theme_summary(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Cursory theme mentions by party x condition")
    table.caption = "Cells are proportions of reflections whose text matched a simple keyword pattern."
    table.add_column("Party")
    table.add_column("Condition")
    for theme in THEME_PATTERNS:
        table.add_column(theme, justify="right")

    for (party, condition), group in party_condition_groups(df):
        n = len(group)
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            *[fmt(safe_divide(int(group[f"theme__{theme}"].sum()), n)) for theme in THEME_PATTERNS],
        )
    console.print(table)
    console.print()


def top_terms(group: pd.DataFrame, *, limit: int = 8) -> str:
    counts: dict[str, int] = {}
    for tokens in group["token_list"]:
        for token in tokens:
            if token in STOPWORDS or len(token) < 3:
                continue
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{token} ({count})" for token, count in ranked)


def render_top_terms(console: Console, df: pd.DataFrame) -> None:
    table = make_table("Top non-stopword terms by party x condition")
    table.add_column("Party")
    table.add_column("Condition")
    table.add_column("Top terms")

    for (party, condition), group in party_condition_groups(df):
        table.add_row(
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            top_terms(group),
        )
    console.print(table)
    console.print()


def truncate(text: str, *, max_chars: int = 115) -> str:
    one_line = " ".join(str(text).split())
    if len(one_line) <= max_chars:
        return one_line
    return one_line[: max_chars - 1].rstrip() + "..."


def render_examples(console: Console, df: pd.DataFrame) -> None:
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

    for (party, condition), group in party_condition_groups(df):
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
            str(party),
            CONDITION_DISPLAY.get(str(condition), str(condition)),
            fmt(float(row[INFLUENCE_COL]), digits=0),
            str(int(row["word_count"])),
            truncate(str(row[REFLECTION_COL])),
        )
    console.print(table)
    console.print()


def ordered_group_keys(df: pd.DataFrame) -> list[tuple[str, str]]:
    present = {
        (str(party), str(condition))
        for party, condition in df[["party_group", "condition"]].drop_duplicates().itertuples(index=False)
    }
    return [(party, condition) for party in PARTY_ORDER for condition in CONDITION_ORDER if (party, condition) in present]


def group_label(key: tuple[str, str]) -> str:
    return GROUP_LABELS.get(key, f"{key[0]}\n{CONDITION_DISPLAY.get(key[1], key[1])}")


def save_mean_influence_plot(df: pd.DataFrame) -> Path:
    keys = ordered_group_keys(df)
    means = [
        df.loc[(df["party_group"] == party) & (df["condition"] == condition), INFLUENCE_COL].mean()
        for party, condition in keys
    ]
    colors = ["#4C78A8" if party == "democrat" else "#F58518" for party, _ in keys]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bars = ax.bar(range(len(keys)), means, color=colors)
    ax.set_title("Mean Phase 1 Pair-Reflection Influence Rating")
    ax.set_ylabel("Mean rating (1-7)")
    ax.set_ylim(0, 7)
    ax.set_xticks(range(len(keys)), [group_label(key) for key in keys])
    ax.grid(axis="y", alpha=0.25)
    for bar, mean in zip(bars, means, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, mean + 0.08, f"{mean:.2f}", ha="center", va="bottom")
    fig.tight_layout()

    path = PLOTS_DIR / "mean_influence_by_party_condition.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_rating_distribution_plot(df: pd.DataFrame) -> Path:
    keys = ordered_group_keys(df)
    ratings = list(range(1, 8))

    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    for key in keys:
        party, condition = key
        group = df.loc[(df["party_group"] == party) & (df["condition"] == condition)]
        proportions = group[INFLUENCE_COL].round().astype(int).value_counts(normalize=True)
        y = [float(proportions.get(rating, 0.0)) for rating in ratings]
        ax.plot(ratings, y, marker="o", linewidth=2, label=group_label(key).replace("\n", " "))

    ax.set_title("Influence Rating Distribution by Party x Condition")
    ax.set_xlabel("Influence rating")
    ax.set_ylabel("Proportion of responses")
    ax.set_xticks(ratings)
    ax.set_ylim(0, 0.32)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()

    path = PLOTS_DIR / "influence_rating_distribution.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_word_count_boxplot(df: pd.DataFrame) -> Path:
    keys = ordered_group_keys(df)
    values = [
        df.loc[(df["party_group"] == party) & (df["condition"] == condition), "word_count"].to_numpy()
        for party, condition in keys
    ]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    boxplot = ax.boxplot(
        values,
        tick_labels=[group_label(key) for key in keys],
        showfliers=False,
        patch_artist=True,
    )
    for box, key in zip(boxplot["boxes"], keys, strict=True):
        box.set_facecolor("#4C78A8" if key[0] == "democrat" else "#F58518")
        box.set_alpha(0.55)
    ax.set_title("Reflection Length Distribution")
    ax.set_ylabel("Words per reflection")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    path = PLOTS_DIR / "reflection_word_count_boxplot.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_theme_heatmap(df: pd.DataFrame) -> Path:
    keys = ordered_group_keys(df)
    themes = list(THEME_PATTERNS)
    matrix: list[list[float]] = []
    for party, condition in keys:
        group = df.loc[(df["party_group"] == party) & (df["condition"] == condition)]
        matrix.append([safe_divide(int(group[f"theme__{theme}"].sum()), len(group)) for theme in themes])

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(max(row) for row in matrix) + 0.05)
    ax.set_title("Keyword-Coded Theme Mention Proportions")
    ax.set_xticks(range(len(themes)), themes, rotation=25, ha="right")
    ax.set_yticks(range(len(keys)), [group_label(key).replace("\n", " ") for key in keys])
    for row_idx, row in enumerate(matrix):
        for col_idx, value in enumerate(row):
            ax.text(col_idx, row_idx, f"{value:.2f}", ha="center", va="center", color="#111827")
    fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02, label="Proportion")
    fig.tight_layout()

    path = PLOTS_DIR / "theme_mentions_heatmap.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_plots(console: Console, df: pd.DataFrame) -> list[Path]:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_paths = [
        save_mean_influence_plot(df),
        save_rating_distribution_plot(df),
        save_word_count_boxplot(df),
        save_theme_heatmap(df),
    ]
    console.print("[bold]Saved plots[/bold]")
    for path in plot_paths:
        console.print(f"[dim]- {path.relative_to(PROJECT_ROOT)}[/dim]")
    console.print()
    return plot_paths


def main() -> None:
    console = Console()
    df = load_filtered_dataframe(console)
    df[INFLUENCE_COL] = pd.to_numeric(df[INFLUENCE_COL], errors="coerce")
    df["party_group"] = df["party_group"].map(normalize_party)
    df["condition"] = df["condition"].map(normalize_condition)
    df = add_text_features(df)

    console.rule("[bold]Phase 1 Free-Response Analysis[/bold]")
    render_overview(console, df)
    render_counts(console, df)
    render_rating_summary(console, df)
    render_rating_distribution(console, df)
    render_text_summary(console, df)
    render_theme_summary(console, df)
    render_top_terms(console, df)
    render_examples(console, df)
    save_plots(console, df)


if __name__ == "__main__":
    main()
