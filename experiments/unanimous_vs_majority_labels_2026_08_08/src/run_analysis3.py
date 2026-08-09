"""Analysis 3: stance by cell within each toxicity stratum.

Run from repo root::

    PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/run_analysis3.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.unanimous_vs_majority_labels_2026_08_08.src.build_cohort import (
    COHORT_CSV,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS3_DIR = EXPERIMENT_ROOT / "outputs" / "analysis3"

_CELL_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_STANCE_ORDER = ("left", "right")
_STRATA = (
    ("low", "sample_low_toxicity", "stance_by_cell_low_toxicity.csv"),
    ("middle", "sample_middle_toxicity", "stance_by_cell_middle_toxicity.csv"),
    ("high", "sample_high_toxicity", "stance_by_cell_high_toxicity.csv"),
)
_REQUIRED_COLUMNS = ("cell", "sample_toxicity_type", "sampled_stance")
_ALL_STRATA_CSV = "stance_by_cell_all_strata.csv"


def _load_cohort(path: Path) -> pd.DataFrame:
    """Load the cohort and validate Analysis 3 columns.

    Parameters
    ----------
    path
        Path to ``four_cell_cohort.csv``.

    Returns
    -------
    pandas.DataFrame
        Cohort frame.

    Raises
    ------
    FileNotFoundError
        When the cohort file is missing.
    KeyError
        When required columns are absent.
    """
    if not path.is_file():
        raise FileNotFoundError(path.resolve())
    cohort = pd.read_csv(path)
    missing = [c for c in _REQUIRED_COLUMNS if c not in cohort.columns]
    if missing:
        raise KeyError(f"Cohort missing required columns: {missing}")
    return cohort


def _counts_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Build a left/right by cell count table with frozen order.

    Parameters
    ----------
    frame
        Rows for one toxicity stratum.

    Returns
    -------
    pandas.DataFrame
        Wide count table with stance rows and cell columns.
    """
    counts = (
        frame.groupby(["sampled_stance", "cell"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )
    for cell in _CELL_ORDER:
        if cell not in counts.columns:
            counts[cell] = 0
    counts = counts.reindex(index=list(_STANCE_ORDER), columns=list(_CELL_ORDER), fill_value=0)
    counts.index.name = "sampled_stance"
    return counts.astype(int)


def _long_rows(stratum_key: str, wide: pd.DataFrame) -> list[dict[str, object]]:
    """Convert one wide stratum table into long-form count rows.

    Parameters
    ----------
    stratum_key
        Toxicity stratum label (low, middle, high).
    wide
        Wide stance-by-cell counts.

    Returns
    -------
    list[dict[str, object]]
        Long-form records with ``toxicity_stratum``, ``sampled_stance``, ``cell``, ``n``.
    """
    rows: list[dict[str, object]] = []
    for stance in _STANCE_ORDER:
        for cell in _CELL_ORDER:
            rows.append(
                {
                    "toxicity_stratum": stratum_key,
                    "sampled_stance": stance,
                    "cell": cell,
                    "n": int(wide.loc[stance, cell]),
                }
            )
    return rows


def run_analysis3(cohort_path: Path = COHORT_CSV) -> pd.DataFrame:
    """Build stance-by-cell tables for each toxicity stratum.

    Parameters
    ----------
    cohort_path
        Path to the four-cell cohort CSV.

    Returns
    -------
    pandas.DataFrame
        Combined long-form stance counts across strata.
    """
    cohort = _load_cohort(cohort_path)
    ANALYSIS3_DIR.mkdir(parents=True, exist_ok=True)
    long_rows: list[dict[str, object]] = []
    for stratum_key, toxicity_value, filename in _STRATA:
        subset = cohort[cohort["sample_toxicity_type"] == toxicity_value]
        wide = _counts_table(subset)
        wide.to_csv(ANALYSIS3_DIR / filename)
        print(f"Wrote {ANALYSIS3_DIR / filename}")
        print(wide.to_string())
        long_rows.extend(_long_rows(stratum_key, wide))
    long_frame = pd.DataFrame(long_rows)
    long_path = ANALYSIS3_DIR / _ALL_STRATA_CSV
    long_frame.to_csv(long_path, index=False)
    print(f"Wrote {long_path} total_n={int(long_frame['n'].sum())}")
    return long_frame


def main() -> None:
    """CLI entry: write Analysis 3 stance tables."""
    run_analysis3(COHORT_CSV)


if __name__ == "__main__":
    main()
