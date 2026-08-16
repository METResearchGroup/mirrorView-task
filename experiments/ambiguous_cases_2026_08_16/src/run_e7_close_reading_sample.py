"""Export stratified close-reading samples (E7).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e7_close_reading_sample.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
E1_SCORES_CSV = EXPERIMENT_ROOT / "outputs" / "e1" / "post_scores.csv"
E2_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "post_effects.csv"
SAMPLE_CSV = EXPERIMENT_ROOT / "outputs" / "e7" / "close_reading_sample.csv"
SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e7" / "summary.json"

_SEED = 42
_TARGET_N = 40


def run_e7() -> tuple[pd.DataFrame, dict]:
    """Export the close-reading sample and summary."""
    posts = pd.read_csv(POST_FRAME_CSV)
    e1 = pd.read_csv(E1_SCORES_CSV)
    e2 = pd.read_csv(E2_EFFECTS_CSV)
    frame = posts.merge(
        e1[["post_id", "ambiguity_score", "four_cell_label"]], on="post_id"
    ).merge(e2[["post_id", "adjusted_ambiguity_score"]], on="post_id")

    samples: list[pd.DataFrame] = []

    ties = frame[frame["is_tie"]].copy()
    ties = ties.sample(n=min(_TARGET_N, len(ties)), random_state=_SEED)
    ties["stratum"] = "tie"
    samples.append(ties)

    multi = frame[frame["n_raters"] >= 6].copy()
    multi = multi.sort_values("adjusted_ambiguity_score", ascending=False).head(
        _TARGET_N
    )
    multi["stratum"] = "high_ambiguity_multi_rater"
    samples.append(multi)

    median_amb = float(frame["ambiguity_score"].median())
    reclass = frame[
        (frame["n_raters"] == 3)
        & (frame["four_cell_label"].isin(["unanimous_keep", "unanimous_remove"]))
        & (frame["ambiguity_score"] > median_amb)
    ].copy()
    reclass = reclass.sample(n=min(_TARGET_N, len(reclass)), random_state=_SEED)
    reclass["stratum"] = "reclassified_unanimous"
    samples.append(reclass)

    sample = pd.concat(samples, ignore_index=True)
    cols = [
        "stratum",
        "post_id",
        "original_text",
        "n_raters",
        "keep_count",
        "remove_count",
        "ambiguity_score",
        "adjusted_ambiguity_score",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    sample = sample[cols].drop_duplicates(subset=["post_id"], keep="first")
    summary = {
        "seed": _SEED,
        "n_total": int(len(sample)),
        "n_by_stratum": sample["stratum"].value_counts().to_dict(),
        "median_ambiguity_score": median_amb,
    }

    SAMPLE_CSV.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(SAMPLE_CSV, index=False)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return sample, summary


def main() -> None:
    """CLI entry for E7."""
    sample, summary = run_e7()
    print(f"Wrote {SAMPLE_CSV}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"n_total {summary['n_total']}")
    print(f"n_by_stratum {summary['n_by_stratum']}")


if __name__ == "__main__":
    main()
