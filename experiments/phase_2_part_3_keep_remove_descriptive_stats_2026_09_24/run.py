"""Run Part 3 keep/remove descriptive stats and write RESULTS.md.

Run from repo root::

    PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.agreement import (
    build_four_cell_counts,
    build_four_cell_shares,
    build_vote_funnel,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.platform_rates import (
    build_labeled_posts,
    build_platform_crosstab,
    build_platform_toxicity_crosstab,
    column_proportions,
    load_stimuli,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.remove_histogram import (
    HISTOGRAM_FILENAME,
    count_five_label_posts_by_remove_count,
    format_remove_count_section,
    plot_remove_count_histogram,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.votes import (
    build_per_post_votes,
    load_results_full,
)
from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.write_results import (
    format_results_markdown,
    write_results,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent


def _crosstab_to_csv(table: pd.DataFrame) -> pd.DataFrame:
    """Convert a decision-indexed crosstab to a CSV-friendly frame."""
    return table.reset_index(names="decision")


def main() -> None:
    """Load data, compute tables, write results, and print markdown.

    Pipeline order: load results, ``build_per_post_votes``, load stimuli,
    platform crosstabs, four-cell and funnel builders, ``format_results_markdown``,
    ``write_results``.
    """
    raw = load_results_full()
    per_post = build_per_post_votes(raw)
    stimuli = load_stimuli()

    labeled_posts = build_labeled_posts(per_post, stimuli)
    platform_counts = build_platform_crosstab(labeled_posts)
    platform_proportions = column_proportions(platform_counts)
    platform_toxicity_counts = build_platform_toxicity_crosstab(labeled_posts)
    platform_toxicity_proportions = column_proportions(platform_toxicity_counts)

    four_cell_counts = build_four_cell_counts(per_post)
    four_cell_shares = build_four_cell_shares(four_cell_counts)
    funnel = build_vote_funnel(per_post)
    remove_counts = count_five_label_posts_by_remove_count(per_post)
    plot_remove_count_histogram(
        remove_counts, EXPERIMENT_DIR / "outputs" / HISTOGRAM_FILENAME
    )

    markdown = format_results_markdown(
        platform_counts,
        platform_proportions,
        platform_toxicity_proportions,
        four_cell_counts,
        four_cell_shares,
        funnel,
    )
    markdown = f"{markdown}\n\n{format_remove_count_section(remove_counts)}\n"

    csv_bundle = {
        "platform_counts.csv": _crosstab_to_csv(platform_counts),
        "platform_proportions.csv": _crosstab_to_csv(platform_proportions),
        "platform_toxicity_proportions.csv": _crosstab_to_csv(
            platform_toxicity_proportions
        ),
        "four_cell_counts.csv": four_cell_shares,
        "funnel.csv": funnel,
        "five_label_remove_counts.csv": remove_counts,
    }
    results_path = write_results(markdown, csv_bundle, EXPERIMENT_DIR)
    print(markdown, end="")
    print(f"\nWrote {results_path}")


if __name__ == "__main__":
    main()
