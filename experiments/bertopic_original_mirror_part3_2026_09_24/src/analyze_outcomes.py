"""Topic keep rates for Part 3, with bootstrap intervals and FDR tests.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_outcomes.py \\
      --topics-run-dir <original run> --joint-topics-run-dir <joint run>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.express as px

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import (
    benjamini_hochberg_topic_tests,
    build_facet_outcome_table,
    cluster_bootstrap_keep_rate_by_topic,
    compute_party_outcomes,
    load_outcome_corpus,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_RESULTS_FULL

MIN_RATERS = 3
N_BOOTSTRAP = 2000
BOOTSTRAP_SEED = 42
FDR_ALPHA = 0.05
FACET_MIN_POSTS = 30
FACETS = ("sampled_stance", "sample_toxicity_type", "platform")
OUTCOME_COLUMNS = [
    "topic",
    "n_posts",
    "keep_rate",
    "ci_low",
    "ci_high",
    "p_value",
    "q_value",
    "significant_bh",
]


def _topic_table(joined: pd.DataFrame, n_bootstrap: int, seed: int) -> pd.DataFrame:
    """Bootstrap keep rates and BH tests for one assignment join."""
    rates = cluster_bootstrap_keep_rate_by_topic(joined, n_bootstrap, seed)
    tests = benjamini_hochberg_topic_tests(
        successes=joined.groupby("topic")["n_keep"].sum().reindex(rates["topic"]).astype(int).tolist(),
        trials=joined.groupby("topic")["n_raters"].sum().reindex(rates["topic"]).astype(int).tolist(),
        corpus_keep_rate=float(joined["keep_rate"].mean()),
        topics=rates["topic"].astype(int).tolist(),
    )
    return rates.merge(tests, on="topic")[OUTCOME_COLUMNS]


def _write_bar(frame: pd.DataFrame, x: str, y: str, path_stem: Path, color: str | None = None) -> None:
    """Write an HTML and PNG bar chart."""
    figure = px.bar(frame, x=x, y=y, color=color)
    figure.write_html(path_stem.with_suffix(".html"))
    figure.write_image(path_stem.with_suffix(".png"))


def run_analyze_outcomes(
    topics_run_dir: Path,
    joint_topics_run_dir: Path,
    n_bootstrap: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
    min_raters: int = MIN_RATERS,
    output_dir: Path | None = None,
) -> Path:
    """Write Q5 tables for the original model and the joint model.

    Returns
    -------
    pathlib.Path
        Outcomes run directory.
    """
    labels = load_outcome_corpus(data_mod.load_keep_remove_posts(), min_raters)
    original = pd.read_parquet(topics_run_dir / "assignments.parquet")
    original = original.loc[original["text_role"] == "original", ["post_id", "topic"]]
    joined = labels.merge(original, on="post_id", how="inner")
    by_topic = _topic_table(joined, n_bootstrap, seed)
    joint_assignments = pd.read_parquet(joint_topics_run_dir / "assignments.parquet")
    joint_original = joint_assignments.loc[
        joint_assignments["text_role"] == "original", ["post_id", "topic"]
    ]
    joint_joined = labels.merge(joint_original, on="post_id", how="inner")
    by_topic_joint = _topic_table(joint_joined, n_bootstrap, seed)
    facet_frames = [build_facet_outcome_table(joined, facet, FACET_MIN_POSTS) for facet in FACETS]
    ratings = _linked_fate_ratings()
    ratings = ratings.merge(original, on="post_id", how="inner")
    ratings = ratings.loc[ratings["post_id"].isin(set(joined["post_id"]))]
    party = compute_party_outcomes(ratings)
    run_dir = output_dir or (paths.analyses_dir() / "outcomes" / paths.new_run_timestamp())
    figures = run_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    by_topic.to_csv(run_dir / "outcomes_by_topic.csv", index=False)
    by_topic_joint.to_csv(run_dir / "outcomes_by_topic_joint.csv", index=False)
    party.to_csv(run_dir / "outcomes_by_topic_party.csv", index=False)
    pd.concat(facet_frames, ignore_index=True).to_csv(run_dir / "outcomes_by_topic_facet.csv", index=False)
    overall = float(joined["keep_rate"].mean())
    (run_dir / "overall_keep_rate.json").write_text(
        json.dumps({"overall_keep_rate": overall}) + "\n", encoding="utf-8"
    )
    metadata = {
        "source_topics_run": str(topics_run_dir),
        "source_joint_topics_run": str(joint_topics_run_dir),
        "min_raters": min_raters,
        "n_bootstrap": n_bootstrap,
        "bootstrap_seed": seed,
        "fdr_alpha": FDR_ALPHA,
        "facet_min_posts": FACET_MIN_POSTS,
        "n_posts_analyzed": int(len(joined)),
        "overall_keep_rate": overall,
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    facet_table = pd.concat(facet_frames, ignore_index=True)
    _write_outcome_figures(figures, by_topic, by_topic_joint, party, facet_table)
    print(f"outcomes_run_dir={run_dir}")
    return run_dir


def _write_outcome_figures(
    figures: Path,
    by_topic: pd.DataFrame,
    by_topic_joint: pd.DataFrame,
    party: pd.DataFrame,
    facet_table: pd.DataFrame,
) -> None:
    """Topic, party, and facet keep-rate charts."""
    _write_bar(by_topic, "topic", "keep_rate", figures / "keep_rate_by_topic_original")
    _write_bar(by_topic_joint, "topic", "keep_rate", figures / "keep_rate_by_topic_joint")
    for party_name, subset in party.groupby("party_group"):
        _write_bar(subset, "topic", "keep_rate", figures / f"keep_rate_by_topic_party_{party_name}")
    for facet in FACETS:
        subset = facet_table.loc[facet_table["facet"] == facet]
        if subset.empty:
            continue
        _write_bar(subset, "topic", "keep_rate", figures / f"keep_rate_facet_{facet}", color="facet_value")


def _linked_fate_ratings() -> pd.DataFrame:
    """Return scored linked-fate ratings with a party group."""
    raw = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)
    mode = raw["evaluation_mode"].astype(str).str.lower().str.strip()
    decision = raw["decision"].astype(str).str.lower().str.strip()
    party = raw["party_group"].astype(str).str.lower().str.strip()
    kept = raw.loc[
        (mode == "linked_fate")
        & decision.isin(["keep", "remove"])
        & party.isin(["democrat", "republican"])
    ].copy()
    kept["post_id"] = kept["post_id"].astype(str).str.strip()
    kept["decision"] = decision.loc[kept.index]
    kept["party_group"] = party.loc[kept.index]
    return kept[["post_id", "decision", "party_group"]]


def main() -> None:
    """CLI entry for Q5."""
    parser = argparse.ArgumentParser(description="Per-topic keep rates for Part 3.")
    parser.add_argument("--topics-run-dir", type=Path, required=True)
    parser.add_argument("--joint-topics-run-dir", type=Path, required=True)
    parser.add_argument("--n-bootstrap", type=int, default=N_BOOTSTRAP)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run_analyze_outcomes(
        args.topics_run_dir,
        args.joint_topics_run_dir,
        args.n_bootstrap,
        args.bootstrap_seed,
        MIN_RATERS,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
