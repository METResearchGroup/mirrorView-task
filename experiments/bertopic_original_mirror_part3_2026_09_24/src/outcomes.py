"""Pure helpers for Part 3 topic outcome tables.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import cluster_bootstrap_keep_rate_by_topic"
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import apply_bh_fdr

CI_LOW_PERCENTILE = 2.5
CI_HIGH_PERCENTILE = 97.5
FDR_Q = 0.05
NOISE_TOPIC_ID = -1


def cluster_bootstrap_keep_rate_by_topic(
    frame: pd.DataFrame,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    """Bootstrap per-topic keep rates by resampling posts.

    Parameters
    ----------
    frame
        One row per post with ``topic`` and ``keep_rate``.
    n_bootstrap
        Number of resamples.
    seed
        NumPy Generator seed.

    Returns
    -------
    pandas.DataFrame
        ``topic``, ``n_posts``, ``keep_rate``, ``ci_low``, ``ci_high``.
    """
    topics = frame["topic"].to_numpy()
    rates = frame["keep_rate"].to_numpy(dtype=np.float64)
    unique_topics = sorted(int(topic) for topic in pd.unique(topics))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(frame), size=(n_bootstrap, len(frame)))
    drawn_topics = topics[draws]
    drawn_rates = rates[draws]
    rows = []
    for topic in unique_topics:
        member = topics == topic
        point = float(rates[member].mean())
        selected = drawn_topics == topic
        counts = selected.sum(axis=1)
        sums = (drawn_rates * selected).sum(axis=1)
        boot_rates = np.divide(sums, counts, out=np.full(n_bootstrap, np.nan), where=counts > 0)
        finite = boot_rates[np.isfinite(boot_rates)]
        rows.append(
            {
                "topic": topic,
                "n_posts": int(member.sum()),
                "keep_rate": point,
                "ci_low": float(np.percentile(finite, CI_LOW_PERCENTILE)),
                "ci_high": float(np.percentile(finite, CI_HIGH_PERCENTILE)),
            }
        )
    return pd.DataFrame(rows)


def benjamini_hochberg_topic_tests(
    successes: list[int],
    trials: list[int],
    corpus_keep_rate: float,
    topics: list[int],
) -> pd.DataFrame:
    """Two-sided binomial tests of each topic against the corpus keep rate."""
    pvalues = [
        float(binomtest(success, trial, corpus_keep_rate).pvalue)
        for success, trial in zip(successes, trials)
    ]
    q_values = apply_bh_fdr(pvalues)
    return pd.DataFrame(
        {
            "topic": topics,
            "p_value": pvalues,
            "q_value": q_values,
            "significant_bh": q_values < FDR_Q,
        }
    )


def build_facet_outcome_table(frame: pd.DataFrame, facet: str, facet_min_posts: int) -> pd.DataFrame:
    """Keep topic-facet cells with at least ``facet_min_posts`` posts."""
    grouped = (
        frame.groupby([facet, "topic"], dropna=False)
        .agg(n_posts=("post_id", "size"), keep_rate=("keep_rate", "mean"))
        .reset_index()
    )
    kept = grouped.loc[grouped["n_posts"] >= facet_min_posts].copy()
    kept["facet"] = facet
    kept["facet_value"] = kept[facet]
    kept["ci_low"] = np.nan
    kept["ci_high"] = np.nan
    return kept[["facet", "facet_value", "topic", "n_posts", "keep_rate", "ci_low", "ci_high"]]


def summarize_outcomes_by_topic(frame: pd.DataFrame) -> pd.DataFrame:
    """Mean keep rate per topic, including the noise topic."""
    return (
        frame.groupby("topic", dropna=False)
        .agg(n_posts=("post_id", "size"), keep_rate=("keep_rate", "mean"))
        .reset_index()
    )


def load_outcome_corpus(labels: pd.DataFrame, min_raters: int) -> pd.DataFrame:
    """Keep rated posts with at least ``min_raters`` linked-fate raters."""
    enough = labels["n_raters"] >= min_raters
    labeled = labels["decision"].isin(["keep", "remove"])
    return labels.loc[enough & labeled].reset_index(drop=True)


def compute_party_outcomes(ratings: pd.DataFrame) -> pd.DataFrame:
    """Keep rate per topic and rater party from rating rows.

    Parameters
    ----------
    ratings
        Columns ``topic``, ``party_group``, ``decision``.

    Returns
    -------
    pandas.DataFrame
        ``topic``, ``party_group``, ``n_ratings``, ``keep_rate``.
    """
    frame = ratings.copy()
    frame["is_keep"] = (frame["decision"] == "keep").astype(int)
    grouped = (
        frame.groupby(["topic", "party_group"])
        .agg(n_ratings=("is_keep", "size"), n_keep=("is_keep", "sum"))
        .reset_index()
    )
    grouped["keep_rate"] = grouped["n_keep"] / grouped["n_ratings"]
    return grouped
