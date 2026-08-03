"""Histogram of Phase 2 Part 2 pair-influence Likert ratings (1–7).

To run:

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_1_histogram/plot.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = SCRIPT_DIR / "plot.png"
RATING_COL = "phase1_pair_influence_rating"
LIKERT_MIN = 1
LIKERT_MAX = 7


def main() -> None:
    df = load_dataset(STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK, low_memory=False)
    ratings = df[RATING_COL].dropna().astype(int)

    bins = [edge - 0.5 for edge in range(LIKERT_MIN, LIKERT_MAX + 2)]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(ratings, bins=bins, edgecolor="black", color="steelblue")
    ax.set_xticks(range(LIKERT_MIN, LIKERT_MAX + 1))
    ax.set_xlabel("Pair influence rating (1 = Not at all, 7 = Very much)")
    ax.set_ylabel("Count")
    ax.set_title("How much did seeing the pair of posts affect your decision?")
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)

    counts = ratings.value_counts().sort_index()
    print(f"n={len(ratings)}")
    print(counts.to_string())
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
