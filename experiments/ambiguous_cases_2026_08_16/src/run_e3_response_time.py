"""Relate response time to ambiguity scores (E3).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e3_response_time.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
E1_SCORES_CSV = EXPERIMENT_ROOT / "outputs" / "e1" / "post_scores.csv"
E2_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "post_effects.csv"
MODEL_SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e3" / "model_summary.json"
CONTRASTS_CSV = EXPERIMENT_ROOT / "outputs" / "e3" / "contrasts.csv"


def _within_rater_demean(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Subtract within-rater means from the named columns."""
    out = frame.copy()
    means = out.groupby("participant_id")[columns].transform("mean")
    out[columns] = out[columns] - means
    return out


def _fit_ambiguity_model(
    frame: pd.DataFrame,
    ambiguity_col: str,
) -> tuple[float, float]:
    """Fit demeaned log-RT on ambiguity, length, and trial index."""
    cols = [ambiguity_col, "char_count", "trial_index", "log_rt"]
    demeaned = _within_rater_demean(frame, cols)
    y = demeaned["log_rt"].to_numpy()
    x = demeaned[[ambiguity_col, "char_count", "trial_index"]].to_numpy()
    if len(y) < 5:
        return float("nan"), float("nan")
    x_design = np.column_stack([np.ones(len(x)), x])
    coef, _, _, _ = np.linalg.lstsq(x_design, y, rcond=None)
    residual = y - x_design @ coef
    return float(coef[1]), float(np.var(residual, ddof=x_design.shape[1]))


def _contrast_row(
    name: str,
    group_a: str,
    group_b: str,
    values_a: np.ndarray,
    values_b: np.ndarray,
) -> dict:
    """Build one contrast summary row."""
    return {
        "contrast_name": name,
        "group_a": group_a,
        "group_b": group_b,
        "mean_log_rt_a": float(np.mean(values_a)) if len(values_a) else float("nan"),
        "mean_log_rt_b": float(np.mean(values_b)) if len(values_b) else float("nan"),
        "diff_a_minus_b": (
            float(np.mean(values_a) - np.mean(values_b))
            if len(values_a) and len(values_b)
            else float("nan")
        ),
        "n_a": int(len(values_a)),
        "n_b": int(len(values_b)),
    }


def run_e3() -> tuple[dict, pd.DataFrame]:
    """Fit E3 models and write outputs."""
    trials = pd.read_csv(TRIAL_FRAME_CSV)
    posts = pd.read_csv(POST_FRAME_CSV)
    e1 = pd.read_csv(E1_SCORES_CSV)[["post_id", "ambiguity_score", "four_cell_label"]]
    e2 = pd.read_csv(E2_EFFECTS_CSV)[["post_id", "adjusted_ambiguity_score"]]

    frame = trials.merge(
        posts[["post_id", "is_tie", "keep_count", "remove_count"]], on="post_id"
    )
    frame = frame.merge(e1, on="post_id")
    frame = frame.merge(e2, on="post_id")
    frame = frame[frame["response_time_ms"] > 0].copy()
    frame["log_rt"] = np.log(frame["response_time_ms"].astype(float))

    e1_slope, e1_resid = _fit_ambiguity_model(frame, "ambiguity_score")
    e2_slope, e2_resid = _fit_ambiguity_model(frame, "adjusted_ambiguity_score")

    split_posts = frame[
        (~frame["is_tie"]) & (frame["keep_count"] > 0) & (frame["remove_count"] > 0)
    ].copy()
    modal_remove = split_posts["remove_count"] > split_posts["keep_count"]
    is_minority = ((split_posts["is_remove"] == 1) & (~modal_remove)) | (
        (split_posts["is_remove"] == 0) & modal_remove
    )
    minority_vals = split_posts.loc[is_minority, "log_rt"].to_numpy()
    majority_vals = split_posts.loc[~is_minority, "log_rt"].to_numpy()

    tie_vals = frame.loc[frame["is_tie"], "log_rt"].to_numpy()
    unan_vals = frame.loc[
        frame["four_cell_label"].isin(["unanimous_keep", "unanimous_remove"]),
        "log_rt",
    ].to_numpy()

    q_hi = frame["adjusted_ambiguity_score"].quantile(0.75)
    q_lo = frame["adjusted_ambiguity_score"].quantile(0.25)
    top_vals = frame.loc[frame["adjusted_ambiguity_score"] >= q_hi, "log_rt"].to_numpy()
    bot_vals = frame.loc[frame["adjusted_ambiguity_score"] <= q_lo, "log_rt"].to_numpy()

    contrasts = pd.DataFrame(
        [
            _contrast_row(
                "minority_vs_majority_on_splits",
                "minority",
                "majority",
                minority_vals,
                majority_vals,
            ),
            _contrast_row("tie_vs_unanimous", "tie", "unanimous", tie_vals, unan_vals),
            _contrast_row(
                "top_vs_bottom_e2_ambiguity_quartile",
                "top_quartile",
                "bottom_quartile",
                top_vals,
                bot_vals,
            ),
        ]
    )

    summary = {
        "e1_ambiguity_slope": e1_slope,
        "e1_residual_variance": e1_resid,
        "e2_ambiguity_slope": e2_slope,
        "e2_residual_variance": e2_resid,
        "n_trials": int(len(frame)),
    }
    MODEL_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    MODEL_SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    contrasts.to_csv(CONTRASTS_CSV, index=False)
    return summary, contrasts


def main() -> None:
    """CLI entry for E3."""
    summary, contrasts = run_e3()
    print(f"Wrote {MODEL_SUMMARY_JSON}")
    print(f"Wrote {CONTRASTS_CSV}")
    print(f"e1_ambiguity_slope {summary['e1_ambiguity_slope']:.6f}")
    print(f"e2_ambiguity_slope {summary['e2_ambiguity_slope']:.6f}")
    print(f"n_contrasts {len(contrasts)}")


if __name__ == "__main__":
    main()
