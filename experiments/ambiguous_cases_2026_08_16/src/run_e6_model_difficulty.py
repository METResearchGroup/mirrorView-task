"""Model difficulty bands and abstention curves (E6).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e6_model_difficulty.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
E1_SCORES_CSV = EXPERIMENT_ROOT / "outputs" / "e1" / "post_scores.csv"
E2_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "post_effects.csv"
ERROR_BY_BAND_CSV = EXPERIMENT_ROOT / "outputs" / "e6" / "error_by_band.csv"
ABSTENTION_CSV = EXPERIMENT_ROOT / "outputs" / "e6" / "abstention_curves.csv"
SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e6" / "summary.json"

_MODEL_LABELS_CSV = (
    Path(__file__).resolve().parents[2]
    / "model_errors_analysis_2026_07_15"
    / "outputs"
    / "base_model_llm_labels.csv"
)
_ABSTAIN_FRACTIONS = (0.0, 0.1, 0.2, 0.3, 0.5)
_SCORE_NAMES = (
    "minority_share",
    "ambiguity_score",
    "adjusted_ambiguity_score",
)


def _band(minority_share: float) -> str:
    """Assign unanimous, lopsided, or close band."""
    if minority_share <= 0.0:
        return "unanimous"
    if minority_share <= 0.25:
        return "lopsided"
    return "close"


def run_e6() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Join model labels and write E6 outputs."""
    posts = pd.read_csv(POST_FRAME_CSV)
    e1 = pd.read_csv(E1_SCORES_CSV)[["post_id", "ambiguity_score"]]
    e2 = pd.read_csv(E2_EFFECTS_CSV)[["post_id", "adjusted_ambiguity_score"]]
    labels = pd.read_csv(_MODEL_LABELS_CSV)
    labels["post_id"] = labels["post_id"].astype(str)

    frame = posts.merge(e1, on="post_id").merge(e2, on="post_id")
    frame = frame.merge(labels[["post_id", "is_correct"]], on="post_id", how="left")
    n_join = int(frame["is_correct"].notna().sum())
    if n_join != len(frame):
        missing = int(frame["is_correct"].isna().sum())
        raise ValueError(f"Model label join missing {missing} of {len(frame)} posts")

    frame["is_error"] = 1 - frame["is_correct"].astype(int)
    frame["band"] = frame["minority_share"].map(_band)
    error_by_band = (
        frame.groupby("band")
        .agg(n=("post_id", "size"), error_rate=("is_error", "mean"))
        .reindex(["unanimous", "lopsided", "close"])
        .reset_index()
    )

    nontie = frame[~frame["is_tie"]].copy()
    nontie["human_remove"] = (nontie["remove_count"] > nontie["keep_count"]).astype(int)
    # Existing labels: is_correct compares model to modal human label already.
    base_accuracy = float(nontie["is_correct"].mean())

    curve_rows = []
    for score_name in _SCORE_NAMES:
        ranked = nontie.sort_values(score_name, ascending=True)
        for abstain in _ABSTAIN_FRACTIONS:
            coverage = 1.0 - abstain
            n_keep = max(1, int(round(len(ranked) * coverage)))
            kept = ranked.iloc[:n_keep]
            curve_rows.append(
                {
                    "score_name": score_name,
                    "abstain_fraction": abstain,
                    "coverage": coverage,
                    "n_evaluated": int(len(kept)),
                    "accuracy": float(kept["is_correct"].mean()),
                }
            )
    curves = pd.DataFrame(curve_rows)

    at_30 = curves[np.isclose(curves["abstain_fraction"], 0.3)]
    best_row = at_30.loc[at_30["accuracy"].idxmax()]
    summary = {
        "base_accuracy_ge3_nontie": base_accuracy,
        "best_score_at_30pct_abstain": str(best_row["score_name"]),
        "best_accuracy_at_30pct_abstain": float(best_row["accuracy"]),
        "error_rate_unanimous": float(
            error_by_band.loc[error_by_band["band"] == "unanimous", "error_rate"].iloc[0]
        ),
        "error_rate_close": float(
            error_by_band.loc[error_by_band["band"] == "close", "error_rate"].iloc[0]
        ),
        "n_posts_joined": n_join,
    }

    ERROR_BY_BAND_CSV.parent.mkdir(parents=True, exist_ok=True)
    error_by_band.to_csv(ERROR_BY_BAND_CSV, index=False)
    curves.to_csv(ABSTENTION_CSV, index=False)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return error_by_band, curves, summary


def main() -> None:
    """CLI entry for E6."""
    error_by_band, curves, summary = run_e6()
    print(f"Wrote {ERROR_BY_BAND_CSV}")
    print(f"Wrote {ABSTENTION_CSV}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"base_accuracy_ge3_nontie {summary['base_accuracy_ge3_nontie']:.6f}")
    print(f"best_score_at_30pct_abstain {summary['best_score_at_30pct_abstain']}")
    print(f"n_bands {len(error_by_band)}")
    print(f"n_curve_rows {len(curves)}")


if __name__ == "__main__":
    main()
