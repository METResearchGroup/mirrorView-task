"""Count and plot remove votes for posts that have five labels.

Run from repo root::

    PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

FIVE_LABELS = 5
REMOVE_COUNT_BINS = tuple(range(FIVE_LABELS + 1))
HISTOGRAM_FILENAME = "five_label_remove_histogram.png"


def count_five_label_posts_by_remove_count(per_post: pd.DataFrame) -> pd.DataFrame:
    """Count posts with five labels by how many of those labels are remove.

    Parameters
    ----------
    per_post
        Per-post vote frame with ``n_raters`` and ``remove_count``.

    Returns
    -------
    pandas.DataFrame
        One row for each remove count from 0 through 5, with columns
        ``remove_count`` and ``n_posts``.

    Raises
    ------
    ValueError
        When a five-label post has a remove count outside 0 through 5.
    """
    five_label_posts = per_post.loc[per_post["n_raters"] == FIVE_LABELS]
    remove_counts = five_label_posts["remove_count"].astype(int)
    unexpected = sorted(set(remove_counts) - set(REMOVE_COUNT_BINS))
    if unexpected:
        raise ValueError(
            "Five-label posts have remove counts outside 0 through 5: "
            f"{unexpected}"
        )
    observed = remove_counts.value_counts()
    return pd.DataFrame(
        {
            "remove_count": list(REMOVE_COUNT_BINS),
            "n_posts": [int(observed.get(count, 0)) for count in REMOVE_COUNT_BINS],
        }
    )


def plot_remove_count_histogram(counts: pd.DataFrame, path: Path) -> Path:
    """Save a histogram of five-label posts by remove-vote count.

    Parameters
    ----------
    counts
        Frame from ``count_five_label_posts_by_remove_count``.
    path
        PNG path to write.

    Returns
    -------
    pathlib.Path
        The written PNG path.
    """
    remove_counts = counts["remove_count"].astype(int).tolist()
    n_posts = counts["n_posts"].astype(int).tolist()
    total = sum(n_posts)
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    bars = ax.bar(
        remove_counts,
        n_posts,
        width=0.8,
        color="#4C78A8",
        edgecolor="white",
    )
    ax.set_title(f"Posts with 5 labels, by number of remove votes (n={total:,})")
    ax.set_xlabel("Remove votes")
    ax.set_ylabel("Number of posts")
    ax.set_xticks(list(REMOVE_COUNT_BINS))
    ax.set_ylim(0, max(n_posts) * 1.12 if n_posts else 1)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for bar, count in zip(bars, n_posts, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{count:,}",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def format_remove_count_section(counts: pd.DataFrame) -> str:
    """Render the five-label remove-count table and histogram link.

    Parameters
    ----------
    counts
        Frame from ``count_five_label_posts_by_remove_count``.

    Returns
    -------
    str
        Markdown section with the count table and a relative image link.
    """
    lines = [
        "## Remove votes on posts with 5 labels",
        "",
        "Each post in this table has exactly five cleaned labels. "
        "The count is how many of those five labels are remove.",
        "",
        "| remove votes | posts |",
        "|---:|---:|",
    ]
    for _, row in counts.iterrows():
        lines.append(f"| {int(row['remove_count'])} | {int(row['n_posts'])} |")
    lines.extend(
        [
            "",
            "![Posts with 5 labels by number of remove votes]"
            f"(outputs/{HISTOGRAM_FILENAME})",
        ]
    )
    return "\n".join(lines)
