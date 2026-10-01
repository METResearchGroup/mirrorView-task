"""Preliminary numbers that ground PROPOSAL.md.

Computes, on the combined Part 2 and Part 3 linked-fate export:

1. Remove-vote distribution on five-rater posts.
2. A beta-binomial noise ceiling: the best majority-label accuracy any model can
   reach at each observed vote count, even if it knew each post's population
   remove probability exactly.
3. Whether raters differ beyond post difficulty: split-half reliability of a
   rater's leniency residual, cross-toxicity-band consistency of that residual,
   and residual by party and attention-check status.
4. Reference points for distribution prediction: agreement between two
   independent five-rater panels, count NLL of an oracle and of a post-agnostic
   prior, and the stored Jev A1 probabilities (raw and isotonic-recalibrated).

Run from the repo root::

    PYTHONPATH=. uv run python experiments/ensemble_keep_remove_2026_09_26/preliminary_analysis.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import boto3
import numpy as np
import pandas as pd
from scipy import optimize, stats
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

from experiments.compare_jev_human_uncertainty_2026_09_25.human_counts import (
    aggregate_remove_counts,
    dedupe_labeler_post,
    posts_with_labeler_count,
    select_scored_trials,
)
from shared.data.dataloader import load_dataset

N_RATERS = 5
MAJORITY = 3
SEED = 20260926
N_SPLITS = 200
N_NULL_SIMS = 200
OUTPUT_PATH = Path(__file__).parent / "outputs" / "preliminary_analysis.json"
RATER_COLUMNS = ("prolific_id", "party_group", "attention_check_passed")
EPS = 1e-4
ARTIFACT_BUCKET = "mirrorview-experimental-artifacts"
JEV_JOINED_KEY = (
    "experiments/compare_jev_human_uncertainty_2026_09_25/outputs/joined.parquet"
)


def fit_beta_binomial(counts: np.ndarray, n: int) -> tuple[float, float]:
    """Return the MLE (alpha, beta) of a beta-binomial on ``counts`` out of ``n``."""

    def neg_log_lik(log_params: np.ndarray) -> float:
        a, b = np.exp(log_params)
        return -stats.betabinom.logpmf(counts, n, a, b).sum()

    result = optimize.minimize(neg_log_lik, x0=np.log([1.0, 2.0]), method="Nelder-Mead")
    a, b = np.exp(result.x)
    return float(a), float(b)


def noise_ceiling_by_count(a: float, b: float, n: int) -> dict[int, float]:
    """Return P(observed majority matches sign(p - 0.5) | k removes) under the fit.

    This is the accuracy of an oracle that knows each post's population remove
    probability p and predicts remove iff p > 0.5, scored against the observed
    five-rater majority.
    """
    ceiling = {}
    for k in range(n + 1):
        p_above_half = stats.beta.sf(0.5, a + k, b + n - k)
        ceiling[k] = float(p_above_half if k >= MAJORITY else 1.0 - p_above_half)
    return ceiling


def add_leave_one_out_rate(trials: pd.DataFrame) -> pd.DataFrame:
    """Add each trial's leave-one-out post remove rate and residual."""
    out = trials.copy()
    out["y"] = out["decision"].eq("remove").astype(float)
    grouped = out.groupby("post_id")["y"]
    n = grouped.transform("size")
    total = grouped.transform("sum")
    out = out.loc[n >= 2].copy()
    n, total = n.loc[out.index], total.loc[out.index]
    out["p_loo"] = (total - out["y"]) / (n - 1)
    out["resid"] = out["y"] - out["p_loo"]
    return out


def _one_split(trials: pd.DataFrame, rng: np.random.Generator) -> float:
    """Spearman-Brown split-half reliability of per-rater mean residual, one random split."""
    half = rng.random(len(trials)) < 0.5
    a = trials.loc[half].groupby("prolific_id")["resid"].mean()
    b = trials.loc[~half].groupby("prolific_id")["resid"].mean()
    joined = pd.concat([a, b], axis=1, join="inner").dropna()
    r = np.corrcoef(joined.iloc[:, 0], joined.iloc[:, 1])[0, 1]
    return float(2 * r / (1 + r))


def split_half_reliability(trials: pd.DataFrame, rng: np.random.Generator) -> float:
    """Mean split-half reliability of per-rater mean residual over ``N_SPLITS`` splits."""
    return float(np.mean([_one_split(trials, rng) for _ in range(N_SPLITS)]))


def null_split_half(trials: pd.DataFrame, rng: np.random.Generator) -> float:
    """Split-half reliability when decisions are redrawn from p_loo (no rater effect)."""
    values = []
    for _ in range(N_NULL_SIMS // 10):
        sim = trials.copy()
        sim["resid"] = (rng.random(len(sim)) < sim["p_loo"]).astype(float) - sim[
            "p_loo"
        ]
        values.append(_one_split(sim, rng))
    return float(np.mean(values))


def cross_band_correlation(trials: pd.DataFrame) -> dict[str, float]:
    """Correlate per-rater residual on low- vs high-toxicity posts."""
    by_band = trials.pivot_table(
        index="prolific_id",
        columns="sample_toxicity_type",
        values="resid",
        aggfunc="mean",
    )
    pairs = {
        "low_vs_high": ("sample_low_toxicity", "sample_high_toxicity"),
        "low_vs_middle": ("sample_low_toxicity", "sample_middle_toxicity"),
        "middle_vs_high": ("sample_middle_toxicity", "sample_high_toxicity"),
    }
    out = {}
    for name, (left, right) in pairs.items():
        joined = by_band[[left, right]].dropna()
        out[name] = float(np.corrcoef(joined[left], joined[right])[0, 1])
        out[f"{name}_n_raters"] = len(joined)
    return out


def within_band_split_half(
    trials: pd.DataFrame, rng: np.random.Generator
) -> dict[str, float]:
    """Split-half reliability of residual within each toxicity band (for disattenuation)."""
    out = {}
    for band, frame in trials.groupby("sample_toxicity_type"):
        out[band] = float(
            np.mean([_one_split(frame, rng) for _ in range(N_SPLITS // 4)])
        )
    return out


def load_jev_joined() -> pd.DataFrame:
    """Download the stored Jev-vs-human join (``post_id``, ``n_remove``, ``p_remove``)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "joined.parquet"
        boto3.client("s3").download_file(ARTIFACT_BUCKET, JEV_JOINED_KEY, str(path))
        return pd.read_parquet(path, columns=["post_id", "n_remove", "p_remove"])


def score_jev(joined: pd.DataFrame, rng_seed: int) -> dict[str, float]:
    """Count NLL, Spearman, and split AUROC for raw and cross-fitted isotonic Jev p."""
    k = joined["n_remove"].to_numpy()
    p_raw = joined["p_remove"].to_numpy().clip(EPS, 1 - EPS)
    p_cal = np.empty_like(p_raw)
    folds = KFold(n_splits=5, shuffle=True, random_state=rng_seed)
    for train_idx, test_idx in folds.split(p_raw):
        iso = IsotonicRegression(y_min=EPS, y_max=1 - EPS, out_of_bounds="clip")
        iso.fit(p_raw[train_idx], k[train_idx] / N_RATERS)
        p_cal[test_idx] = iso.predict(p_raw[test_idx])
    is_split = (k > 0) & (k < N_RATERS)
    out = {"n_posts": len(k)}
    for name, p in (("raw", p_raw), ("isotonic", p_cal)):
        p_split = 1 - p**N_RATERS - (1 - p) ** N_RATERS
        out[f"count_nll_{name}"] = float(-stats.binom.logpmf(k, N_RATERS, p).mean())
        out[f"spearman_{name}"] = float(stats.spearmanr(p, k).statistic)
        out[f"split_auroc_{name}"] = float(roc_auc_score(is_split, p_split))
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    raw = load_dataset("STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL")
    trials = dedupe_labeler_post(select_scored_trials(raw))
    counts = aggregate_remove_counts(trials)
    five = posts_with_labeler_count(counts, N_RATERS)
    k = five["n_remove"].to_numpy()

    a, b = fit_beta_binomial(k, N_RATERS)
    observed = np.bincount(k, minlength=N_RATERS + 1)
    expected = stats.betabinom.pmf(np.arange(N_RATERS + 1), N_RATERS, a, b) * len(k)
    ceiling = noise_ceiling_by_count(a, b, N_RATERS)
    overall_ceiling = float(
        sum(ceiling[i] * observed[i] for i in ceiling) / observed.sum()
    )

    grid = np.linspace(0, 1, 100_001)
    prior = stats.beta.pdf(grid, a, b)
    prior /= prior.sum()
    p_unanimous = grid**N_RATERS + (1 - grid) ** N_RATERS
    share_in_band = float(prior[(grid > 0.2) & (grid < 0.8)].sum())
    share_confident = float(prior[p_unanimous >= 0.8].sum())

    q_majority = stats.binom.sf(MAJORITY - 1, N_RATERS, grid)
    panel_same_majority = float((prior * (q_majority**2 + (1 - q_majority) ** 2)).sum())
    count_pmf = np.stack(
        [stats.binom.pmf(i, N_RATERS, grid) for i in range(N_RATERS + 1)]
    )
    panel_same_count = float((prior * (count_pmf**2).sum(axis=0)).sum())
    entropy = -(count_pmf * np.log(np.clip(count_pmf, 1e-300, None))).sum(axis=0)
    nll_oracle = float((prior * entropy).sum())
    nll_prior_only = float(-stats.betabinom.logpmf(k, N_RATERS, a, b).mean())
    p_sim = rng.beta(a, b, size=200_000)
    k_sim = rng.binomial(N_RATERS, p_sim)
    oracle_split_auroc = float(
        roc_auc_score(
            (k_sim > 0) & (k_sim < N_RATERS),
            1 - p_sim**N_RATERS - (1 - p_sim) ** N_RATERS,
        )
    )

    rater_meta = (
        raw.loc[raw["trial_type"].eq("moderation-trial"), list(RATER_COLUMNS)]
        .dropna(subset=["prolific_id"])
        .groupby("prolific_id")
        .first()
    )
    raw_mod = raw.loc[
        raw["trial_type"].eq("moderation-trial"),
        ["prolific_id", "post_id", "sample_toxicity_type"],
    ]
    raw_mod = raw_mod.assign(
        post_id=raw_mod["post_id"].astype(str).str.strip()
    ).drop_duplicates(["prolific_id", "post_id"])
    loo = add_leave_one_out_rate(trials[["prolific_id", "post_id", "decision"]])
    loo = loo.merge(raw_mod, on=["prolific_id", "post_id"], how="left")

    rater_resid = (
        loo.groupby("prolific_id")["resid"].agg(["mean", "size"]).join(rater_meta)
    )
    rater_rate = loo.groupby("prolific_id")["y"].mean()

    by_party = rater_resid.groupby("party_group")["mean"].agg(["mean", "std", "size"])
    by_attention = rater_resid.groupby("attention_check_passed", dropna=False)[
        "mean"
    ].agg(["mean", "std", "size"])
    party_test = stats.ttest_ind(
        rater_resid.loc[rater_resid["party_group"].eq("democrat"), "mean"],
        rater_resid.loc[rater_resid["party_group"].eq("republican"), "mean"],
        equal_var=False,
    )

    summary = {
        "n_scored_trials": len(trials),
        "n_raters": int(trials["prolific_id"].nunique()),
        "n_posts": len(counts),
        "median_posts_per_rater": float(trials.groupby("prolific_id").size().median()),
        "five_rater_posts": len(five),
        "remove_vote_counts": observed.tolist(),
        "unanimous_share": float((observed[0] + observed[N_RATERS]) / observed.sum()),
        "beta_binomial": {
            "alpha": a,
            "beta": b,
            "expected_counts": expected.round(1).tolist(),
        },
        "noise_ceiling_accuracy_by_remove_votes": ceiling,
        "noise_ceiling_accuracy_overall": overall_ceiling,
        "two_panel_same_majority": panel_same_majority,
        "two_panel_same_count": panel_same_count,
        "count_nll_oracle_knows_p": nll_oracle,
        "count_nll_prior_only": nll_prior_only,
        "split_auroc_oracle_knows_p": oracle_split_auroc,
        "prior_share_p_between_0.2_and_0.8": share_in_band,
        "prior_share_p_unanimous_at_least_0.8": share_confident,
        "p_split_at_p": {
            str(p): float(1 - p**5 - (1 - p) ** 5) for p in (0.05, 0.1, 0.2, 0.3, 0.5)
        },
        "rater_remove_rate_quantiles": rater_rate.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
        .round(3)
        .to_dict(),
        "rater_share_removing_zero": float(rater_rate.eq(0).mean()),
        "split_half_reliability_resid": split_half_reliability(loo, rng),
        "null_split_half_reliability_resid": null_split_half(loo, rng),
        "within_band_split_half": within_band_split_half(loo, rng),
        "cross_band_resid_correlation": cross_band_correlation(loo),
        "resid_by_party": by_party.round(4).to_dict(orient="index"),
        "party_welch_t": {
            "t": float(party_test.statistic),
            "p": float(party_test.pvalue),
        },
        "jev_a1_pair": score_jev(load_jev_joined(), SEED),
        "resid_by_attention_check": {
            str(key): value
            for key, value in by_attention.round(4).to_dict(orient="index").items()
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, default=float) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
