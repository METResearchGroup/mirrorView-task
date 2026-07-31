"""Compute basic mirror-view summary tables from the shared Part 1 pilot results.

This script loads ``STUDY_PHASE_2_PART_1_RESULTS_PILOT`` via the shared registry
and prints three tables:
- User counts by political party x condition
- Phase 1 keep/remove counts (and proportions within each party x condition) by cell
- Phase 2 keep/remove counts (and proportions within each party x condition) by cell
"""

from __future__ import annotations

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_1_RESULTS_PILOT

CONDITION_DISPLAY_MAP = {
    "control": "control",
    "training": "training",
    "training_assisted": "training-assisted",
}
CONDITION_ORDER = ["control", "training", "training-assisted"]
PARTY_ORDER = ["democrat", "republican"]
DECISION_ORDER = ["keep", "remove"]


def first_non_empty(series: pd.Series) -> str | None:
    """Return first non-empty string value, if present."""
    for value in series:
        if pd.isna(value):
            continue
        text = str(value).strip().lower()
        if text:
            return text
    return None


def get_user_level_frame(data_df: pd.DataFrame) -> pd.DataFrame:
    """Build one row per participant with party and condition labels using prolific_id."""
    user_df = (
        data_df.groupby("prolific_id", as_index=False)
        .agg(
            party_group=("party_group", first_non_empty),
            condition=("condition", first_non_empty),
        )
        .dropna(subset=["party_group", "condition"])
        .copy()
    )
    user_df["condition"] = user_df["condition"].map(CONDITION_DISPLAY_MAP)
    user_df = user_df.dropna(subset=["condition"])
    return user_df


def format_user_table(user_df: pd.DataFrame) -> pd.DataFrame:
    """Create user count table indexed by party and condition."""
    table = (
        user_df.groupby(["party_group", "condition"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(index=PARTY_ORDER, columns=CONDITION_ORDER, fill_value=0)
    )
    table["total"] = table.sum(axis=1)
    table.loc["total"] = table.sum(axis=0)
    return table


def format_phase_table(data_df: pd.DataFrame, phase_number: int) -> pd.DataFrame:
    """Create keep/remove count table for a single phase."""
    decisions = data_df.copy()
    decisions["phase_num"] = pd.to_numeric(decisions["phase"], errors="coerce")
    decisions["decision"] = decisions["decision"].astype(str).str.strip().str.lower()
    decisions["condition"] = decisions["condition"].astype(str).str.strip().str.lower()
    decisions["party_group"] = decisions["party_group"].astype(str).str.strip().str.lower()

    decisions = decisions[
        (decisions["phase_num"] == phase_number)
        & (decisions["decision"].isin(DECISION_ORDER))
        & (decisions["condition"].isin(CONDITION_DISPLAY_MAP))
        & (decisions["party_group"].isin(PARTY_ORDER))
    ].copy()
    decisions["condition"] = decisions["condition"].map(CONDITION_DISPLAY_MAP)

    table = (
        decisions.groupby(["party_group", "condition", "decision"], dropna=False)
        .size()
        .unstack("decision", fill_value=0)
        .reindex(DECISION_ORDER, axis=1, fill_value=0)
    )
    table = table.reindex(
        pd.MultiIndex.from_product([PARTY_ORDER, CONDITION_ORDER]),
        fill_value=0,
    )
    table["total"] = table["keep"] + table["remove"]
    denom = table["total"].astype(float)
    table["prop_keep"] = (table["keep"] / denom).where(denom > 0).round(4)
    table["prop_remove"] = (table["remove"] / denom).where(denom > 0).round(4)
    return table


def print_table(title: str, table: pd.DataFrame) -> None:
    print(f"\n{title}")
    print(table.to_string())


def main() -> None:
    df = load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)
    print(
        f"Loaded {STUDY_PHASE_2_PART_1_RESULTS_PILOT}: "
        f"{len(df):,} rows, {df['prolific_id'].nunique()} distinct prolific_id(s)"
    )

    user_df = get_user_level_frame(df)
    users_table = format_user_table(user_df)
    phase1_table = format_phase_table(df, phase_number=1)
    phase2_table = format_phase_table(df, phase_number=2)

    print_table("Table 1 - Users by political party x condition", users_table)
    print_table(
        "Table 2 - Phase 1 keep/remove (counts + proportion of each within party x condition)",
        phase1_table,
    )
    print_table(
        "Table 3 - Phase 2 keep/remove (counts + proportion of each within party x condition)",
        phase2_table,
    )


if __name__ == "__main__":
    main()
