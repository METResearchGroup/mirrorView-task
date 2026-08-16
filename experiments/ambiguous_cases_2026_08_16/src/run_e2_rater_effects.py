"""Fit crossed post and rater effects for adjusted ambiguity (E2).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e2_rater_effects.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
POST_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "post_effects.csv"
RATER_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "rater_effects.csv"
SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e2" / "summary.json"

_SEED = 42
_LOGREG_C = 1.0


def _party_matches_stance(party_group: str, sampled_stance: str) -> bool:
    """Return True when democrat aligns with left or republican with right."""
    party = str(party_group).lower().strip()
    stance = str(sampled_stance).lower().strip()
    if party == "democrat" and stance == "left":
        return True
    if party == "republican" and stance == "right":
        return True
    return False


def _fit_crossed_effects(
    trials: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, LogisticRegression, OneHotEncoder]:
    """Fit logistic post and rater fixed effects."""
    encoder = OneHotEncoder(handle_unknown="error", sparse_output=True)
    design = encoder.fit_transform(
        trials[["post_id", "participant_id"]].astype(str)
    )
    model = LogisticRegression(
        C=_LOGREG_C,
        fit_intercept=False,
        solver="lbfgs",
        max_iter=1000,
        random_state=_SEED,
    )
    model.fit(design, trials["is_remove"].to_numpy())

    post_categories = list(encoder.categories_[0])
    rater_categories = list(encoder.categories_[1])
    coefs = model.coef_.ravel()
    n_posts = len(post_categories)
    post_effects = coefs[:n_posts]
    rater_effects = coefs[n_posts:]

    # Mean-center rater effects so post effect is at average rater.
    rater_mean = float(np.mean(rater_effects))
    rater_effects = rater_effects - rater_mean
    post_effects = post_effects + rater_mean

    post_df = pd.DataFrame(
        {
            "post_id": post_categories,
            "post_effect": post_effects,
        }
    )
    post_df["adjusted_p"] = expit(post_df["post_effect"])
    post_df["adjusted_ambiguity_score"] = 1.0 - 2.0 * (
        post_df["adjusted_p"] - 0.5
    ).abs()

    rater_df = pd.DataFrame(
        {
            "participant_id": rater_categories,
            "rater_effect": rater_effects,
        }
    )
    rates = (
        trials.groupby("participant_id")
        .agg(
            n_trials=("is_remove", "size"),
            empirical_remove_rate=("is_remove", "mean"),
        )
        .reset_index()
    )
    rater_df = rater_df.merge(rates, on="participant_id", how="left")
    return post_df, rater_df, model, encoder


def _party_stance_mismatch_coef(trials: pd.DataFrame, posts: pd.DataFrame) -> float:
    """Fit an additive mismatch coefficient on top of post and rater ids."""
    merged = trials.merge(
        posts[["post_id", "sampled_stance"]],
        on="post_id",
        how="inner",
    )
    merged = merged[
        merged["party_group"].astype(str).str.lower().isin(["democrat", "republican"])
    ].copy()
    if merged.empty:
        return float("nan")
    merged["mismatch"] = [
        0 if _party_matches_stance(p, s) else 1
        for p, s in zip(merged["party_group"], merged["sampled_stance"], strict=True)
    ]
    encoder = OneHotEncoder(handle_unknown="error", sparse_output=True)
    id_design = encoder.fit_transform(
        merged[["post_id", "participant_id"]].astype(str)
    )
    mismatch = merged[["mismatch"]].to_numpy(dtype=float)
    # hstack sparse + dense
    from scipy import sparse

    design = sparse.hstack([id_design, sparse.csr_matrix(mismatch)])
    model = LogisticRegression(
        C=_LOGREG_C,
        fit_intercept=False,
        solver="lbfgs",
        max_iter=1000,
        random_state=_SEED,
    )
    model.fit(design, merged["is_remove"].to_numpy())
    return float(model.coef_.ravel()[-1])


def run_e2() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Fit E2 effects and write outputs."""
    trials = pd.read_csv(TRIAL_FRAME_CSV)
    posts = pd.read_csv(POST_FRAME_CSV)
    eligible_posts = set(posts["post_id"].astype(str))
    fit_trials = trials[trials["post_id"].astype(str).isin(eligible_posts)].copy()
    post_df, rater_df, _, _ = _fit_crossed_effects(fit_trials)

    # Keep only posts in the post frame (encoder may match exactly).
    post_df = post_df[post_df["post_id"].isin(eligible_posts)].copy()
    if len(post_df) != len(posts):
        missing = eligible_posts - set(post_df["post_id"].astype(str))
        raise ValueError(
            f"E2 post effects missing {len(missing)} posts. Example={next(iter(missing))}"
        )

    var_post = float(np.var(post_df["post_effect"].to_numpy(), ddof=1))
    var_rater = float(np.var(rater_df["rater_effect"].to_numpy(), ddof=1))
    total = var_post + var_rater
    mismatch_coef = _party_stance_mismatch_coef(fit_trials, posts)
    summary = {
        "var_post_effects": var_post,
        "var_rater_effects": var_rater,
        "share_var_post": float(var_post / total) if total > 0 else float("nan"),
        "share_var_rater": float(var_rater / total) if total > 0 else float("nan"),
        "party_stance_mismatch_coef": mismatch_coef,
        "n_trials_fit": int(len(fit_trials)),
        "n_posts": int(len(post_df)),
        "n_raters": int(len(rater_df)),
        "seed": _SEED,
    }

    POST_EFFECTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    post_df.to_csv(POST_EFFECTS_CSV, index=False)
    rater_df.to_csv(RATER_EFFECTS_CSV, index=False)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return post_df, rater_df, summary


def main() -> None:
    """CLI entry for E2."""
    post_df, rater_df, summary = run_e2()
    print(f"Wrote {POST_EFFECTS_CSV}")
    print(f"Wrote {RATER_EFFECTS_CSV}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"n_posts {len(post_df)}")
    print(f"n_raters {len(rater_df)}")
    print(f"share_var_post {summary['share_var_post']:.4f}")
    print(f"party_stance_mismatch_coef {summary['party_stance_mismatch_coef']:.6f}")


if __name__ == "__main__":
    main()
