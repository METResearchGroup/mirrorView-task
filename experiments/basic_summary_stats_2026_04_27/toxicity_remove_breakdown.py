"""Removal rates by party × sampled toxicity for Part 1 full results.

Loads ``STUDY_PHASE_2_PART_1_RESULTS_FULL`` and reports how often participants
choose remove across ``sample_toxicity_type`` buckets, using the same party /
condition / phase filters as :mod:`summary_stats`. Also notes that middle-
toxicity trials are not dropped by the export or reviewed loaders.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py
"""

from __future__ import annotations

import pandas as pd

from experiments.basic_summary_stats_2026_04_27.summary_stats import CONDITION_DISPLAY_MAP
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_1_RESULTS_FULL

# Canonical middle-bucket label in exports / stimulus sampling.
MIDDLE_TOXICITY_CANONICAL = "sample_middle_toxicity"

TOXICITY_ROW_ORDER = (
    "sample_low_toxicity",
    MIDDLE_TOXICITY_CANONICAL,
    "sample_high_toxicity",
)

PARTY_ORDER = ("democrat", "republican")


def moderation_phase_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return keep/remove trial rows in phases 1–2 with known party and condition.

    Aligns with the cell filters used by :func:`summary_stats.format_phase_table`,
    but keeps both phases.
    """
    d = df.copy()
    d["phase_num"] = pd.to_numeric(d["phase"], errors="coerce")
    d["decision"] = d["decision"].astype(str).str.strip().str.lower()
    d["condition"] = d["condition"].astype(str).str.strip().str.lower()
    d["party_group"] = d["party_group"].astype(str).str.strip().str.lower()
    return d[
        d["phase_num"].isin([1, 2])
        & d["decision"].isin(["keep", "remove"])
        & (d["condition"].isin(CONDITION_DISPLAY_MAP))
        & (d["party_group"].isin(["democrat", "republican"]))
    ].copy()


def print_pipeline_finding() -> None:
    """Print that reviewed loaders do not drop middle-toxicity rows."""
    print("\n--- Pipeline / code finding ---")
    print(
        "No reviewed step removes or excludes posts solely because "
        f"{MIDDLE_TOXICITY_CANONICAL!r} was sampled:\n"
        "  - scripts/export_study_results.py — filters prolific_id / manual-test only.\n"
        "  - experiments/mirrors_content_analysis_2026_04_24/dataloader.py — "
        "moderation-trial, phase > 0; no toxicity filter.\n"
        "  - experiments/predict_keep_remove_2026_05_07/dataloader.py — adds "
        "evaluation_mode == 'linked_fate' and keep/remove; still no toxicity filter."
    )


def _toxicity_series(trials: pd.DataFrame) -> pd.Series:
    """Normalize ``sample_toxicity_type`` to stripped strings (NA → empty)."""
    return trials["sample_toxicity_type"].fillna("").astype(str).str.strip()


def _count_remove(series: pd.Series) -> int:
    """Count values equal to ``remove``."""
    return int((series == "remove").sum())


def party_x_toxicity_removal_table(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trial counts and removal rates by party × toxicity label.

    Parameters
    ----------
    trials : pandas.DataFrame
        Filtered moderation trials with ``party_group``, ``decision``, and
        ``sample_toxicity_type``.

    Returns
    -------
    pandas.DataFrame
        Columns ``party_group``, ``sample_toxicity_type``, ``n_trials``,
        ``n_remove``, ``prop_remove``.
    """
    t = trials.copy()
    t["_tox"] = _toxicity_series(t)
    agg = (
        t.groupby(["party_group", "_tox"], observed=True)
        .agg(
            n_trials=("decision", "size"),
            n_remove=("decision", _count_remove),
        )
        .reset_index()
        .rename(columns={"_tox": "sample_toxicity_type"})
    )
    agg["prop_remove"] = (agg["n_remove"] / agg["n_trials"]).where(agg["n_trials"] > 0)
    return agg


def print_party_x_toxicity_removal(trials: pd.DataFrame) -> None:
    """Print long and wide removal-rate tables by party × toxicity."""
    full = party_x_toxicity_removal_table(trials)
    print("\n--- Removal by political party x sampled toxicity ---")
    for party in PARTY_ORDER:
        sub = full[full["party_group"] == party].copy()
        if sub.empty:
            print(f"\n{party}: (no rows)")
            continue
        sub = sub.set_index("sample_toxicity_type").reindex(TOXICITY_ROW_ORDER).reset_index()
        print(f"\n{party}")
        display = sub[
            ["sample_toxicity_type", "n_trials", "n_remove", "prop_remove"]
        ].copy()
        display["prop_remove"] = display["prop_remove"].round(4)
        print(display.to_string(index=False))

    wide = full.pivot_table(
        index="sample_toxicity_type",
        columns="party_group",
        values="prop_remove",
        observed=True,
    )
    wide = wide.reindex(list(TOXICITY_ROW_ORDER))
    party_cols = [c for c in PARTY_ORDER if c in wide.columns]
    if party_cols:
        wide = wide[party_cols]
    print("\nprop_remove (wide — compare parties side by side):")
    print(wide.round(4).to_string())

    counts_wide = full.pivot_table(
        index="sample_toxicity_type",
        columns="party_group",
        values="n_trials",
        aggfunc="sum",
        observed=True,
    )
    counts_wide = counts_wide.reindex(list(TOXICITY_ROW_ORDER))
    if party_cols:
        counts_wide = counts_wide[[c for c in party_cols if c in counts_wide.columns]]
    print("\nn_trials (wide):")
    print(counts_wide.fillna(0).astype(int).to_string())


def print_empirical(df: pd.DataFrame) -> None:
    """Print toxicity value counts, decision crosstabs, and party breakdowns.

    No-ops with a message if ``sample_toxicity_type`` is missing.
    """
    if "sample_toxicity_type" not in df.columns:
        print("\nEmpirical: column 'sample_toxicity_type' missing; skip breakdown.")
        return

    mt = moderation_phase_frame(df)
    trials = mt[mt["trial_type"].astype(str) == "moderation-trial"].copy()
    tox = _toxicity_series(trials)

    print(
        "\n--- Empirical (moderation trials, phases 1–2, party/condition filters "
        "aligned with summary_stats phase tables) ---"
    )
    print(f"Rows in slice: {len(trials):,}")
    print("\nsample_toxicity_type value counts (trial rows):")
    print(tox.value_counts(dropna=False).sort_index())

    ct = pd.crosstab(
        tox,
        trials["decision"],
        margins=True,
    )
    print("\nDecision x sample_toxicity_type (rows = toxicity label, all parties):")
    print(ct.to_string())

    print_party_x_toxicity_removal(trials)


def main() -> None:
    """Print the pipeline note and empirical toxicity removal breakdown."""
    print_pipeline_finding()
    df = load_dataset(STUDY_PHASE_2_PART_1_RESULTS_FULL, low_memory=False)
    print(f"\nLoaded dataset: {STUDY_PHASE_2_PART_1_RESULTS_FULL}")
    print_empirical(df)


if __name__ == "__main__":
    main()
