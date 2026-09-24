"""Run Part 3 keep/remove descriptive stats and write RESULTS.md.

Run from repo root::

    PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
"""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent


def main() -> None:
    """Load data, compute tables, write results, and print markdown.

    Pipeline order: load results, ``build_per_post_votes``, load stimuli,
    platform crosstabs, four-cell and funnel builders, ``format_results_markdown``,
    ``write_results``.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
