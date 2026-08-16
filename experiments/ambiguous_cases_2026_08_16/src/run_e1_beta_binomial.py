"""Fit beta-binomial ambiguity scores (E1).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e1_beta_binomial.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.ambiguous_cases_2026_08_16.src.beta_binomial import (
    fit_beta_binomial,
    four_cell_label,
    posterior_mean_p,
    posterior_prob_in_band,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
POST_SCORES_CSV = EXPERIMENT_ROOT / "outputs" / "e1" / "post_scores.csv"
SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e1" / "summary.json"

_SEED = 42
_HALF_SPLIT_MIN_RATERS = 6
_BAND_LOWER = 0.25
_BAND_UPPER = 0.75


def _half_split_correlation(
    trials: pd.DataFrame,
    posts: pd.DataFrame,
    seed: int,
) -> tuple[float, int]:
    """Correlate remove shares across random halves on high-rater posts."""
    rng = np.random.default_rng(seed)
    eligible = posts[posts["n_raters"] >= _HALF_SPLIT_MIN_RATERS]["post_id"].tolist()
    shares_a: list[float] = []
    shares_b: list[float] = []
    for post_id in eligible:
        decisions = trials.loc[trials["post_id"] == post_id, "is_remove"].to_numpy()
        if len(decisions) < _HALF_SPLIT_MIN_RATERS:
            continue
        perm = rng.permutation(len(decisions))
        mid = len(decisions) // 2
        left = decisions[perm[:mid]]
        right = decisions[perm[mid : 2 * mid]]
        if len(left) == 0 or len(right) == 0:
            continue
        shares_a.append(float(left.mean()))
        shares_b.append(float(right.mean()))
    if len(shares_a) < 2:
        return float("nan"), 0
    return float(np.corrcoef(shares_a, shares_b)[0, 1]), len(shares_a)


def _contamination_majority_keep_at_3(
    alpha: float,
    beta: float,
    seed: int,
    n_draws: int = 20000,
) -> float:
    """Estimate share of majority-keep@3 assignments with true p below 0.25."""
    rng = np.random.default_rng(seed)
    true_p = rng.beta(alpha, beta, size=n_draws)
    removes = rng.binomial(3, true_p)
    # majority keep at 3 raters means remove_count in {0, 1}
    majority_keep = removes <= 1
    if not bool(majority_keep.any()):
        return float("nan")
    contaminated = majority_keep & (true_p < _BAND_LOWER)
    return float(contaminated.sum() / majority_keep.sum())


def run_e1() -> tuple[pd.DataFrame, dict]:
    """Fit scores and write E1 outputs.

    Returns
    -------
    tuple[pandas.DataFrame, dict]
        Per-post scores and summary dictionary.
    """
    posts = pd.read_csv(POST_FRAME_CSV)
    trials = pd.read_csv(TRIAL_FRAME_CSV)
    alpha_hat, beta_hat = fit_beta_binomial(
        posts["remove_count"].to_numpy(),
        posts["n_raters"].to_numpy(),
    )

    rows = []
    for row in posts.itertuples(index=False):
        rows.append(
            {
                "post_id": row.post_id,
                "n_raters": int(row.n_raters),
                "remove_count": int(row.remove_count),
                "remove_share": float(row.remove_share),
                "alpha_hat": alpha_hat,
                "beta_hat": beta_hat,
                "posterior_mean_p": posterior_mean_p(
                    row.remove_count, row.n_raters, alpha_hat, beta_hat
                ),
                "ambiguity_score": posterior_prob_in_band(
                    row.remove_count,
                    row.n_raters,
                    alpha_hat,
                    beta_hat,
                    lower=_BAND_LOWER,
                    upper=_BAND_UPPER,
                ),
                "four_cell_label": four_cell_label(
                    int(row.keep_count), int(row.remove_count), int(row.n_raters)
                ),
            }
        )
    scores = pd.DataFrame(rows)
    half_r, half_n = _half_split_correlation(trials, posts, _SEED)
    contamination = _contamination_majority_keep_at_3(alpha_hat, beta_hat, _SEED)
    summary = {
        "alpha_hat": alpha_hat,
        "beta_hat": beta_hat,
        "n_posts": int(len(scores)),
        "half_split_pearson_r": half_r,
        "half_split_n_posts": half_n,
        "contamination_majority_keep_at_3": contamination,
        "seed": _SEED,
    }

    POST_SCORES_CSV.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(POST_SCORES_CSV, index=False)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return scores, summary


def main() -> None:
    """CLI entry for E1."""
    scores, summary = run_e1()
    print(f"Wrote {POST_SCORES_CSV}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"alpha_hat {summary['alpha_hat']:.6f}")
    print(f"beta_hat {summary['beta_hat']:.6f}")
    print(f"half_split_pearson_r {summary['half_split_pearson_r']:.6f}")
    print(f"n_posts {len(scores)}")


if __name__ == "__main__":
    main()
