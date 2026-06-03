"""Report pipeline handling of toxicity labels and empirical removal rates by party x toxicity.

The export pipeline and downstream loaders reviewed here do **not** drop rows because
``sample_toxicity_type`` is ``sample_middle_toxicity``. The script prints **how often**
participants choose **remove**, broken down by **Democrat vs Republican** and by
``sample_toxicity_type`` (low / middle / high), on the same trial slice as ``summary_stats``.

Toxicity is stored in exports as ``sample_toxicity_type`` (jsPsych / CSV). Some modeling
code renames that to ``sampled_toxicity`` after aggregation — same underlying field.

Run from repo root::

    PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py

Uses the newest ``scripts/mirrorview_pilot_data_*.csv`` (same discovery rule as
``summary_stats.py``).
"""

from __future__ import annotations

import pandas as pd

from experiments.basic_summary_stats_2026_04_27.summary_stats import (
    CONDITION_DISPLAY_MAP,
    find_latest_export_csv,
)

# Observed pilot label for the middle bucket (see also ``public/main.js`` / post assignments).
MIDDLE_TOXICITY_CANONICAL = "sample_middle_toxicity"

TOXICITY_ROW_ORDER = (
    "sample_low_toxicity",
    MIDDLE_TOXICITY_CANONICAL,
    "sample_high_toxicity",
)

PARTY_ORDER = ("democrat", "republican")


def moderation_phase_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Same trial selection style as ``summary_stats.format_phase_table`` (both phases)."""
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
    return trials["sample_toxicity_type"].fillna("").astype(str).str.strip()


def _count_remove(series: pd.Series) -> int:
    return int((series == "remove").sum())


def party_x_toxicity_removal_table(trials: pd.DataFrame) -> pd.DataFrame:
    """One row per (party_group, sample_toxicity_type) with counts and removal rate."""
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
    """Print removal frequency by ``sample_toxicity_type`` for Democrats and Republicans."""
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
    print_pipeline_finding()
    try:
        path = find_latest_export_csv()
    except FileNotFoundError as err:
        print(
            "\nNo export CSV found under scripts/ (run scripts/export_study_results.py). "
            f"Detail: {err}"
        )
        return
    print(f"\nLoaded export: {path}")
    df = pd.read_csv(path, low_memory=False)
    print_empirical(df)


if __name__ == "__main__":
    main()
