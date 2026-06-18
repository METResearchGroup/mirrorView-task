from __future__ import annotations

"""
Run from repo root:

PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/get_only_high_toxic_flips.py
"""

from pathlib import Path

import pandas as pd

from experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror import (
    HIGH_TOXICITY,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
GENERATED_FLIPS_DIR = EXPERIMENT_DIR / "generated_flips"


def _pick_latest_flips_csv() -> Path:
    candidates = sorted(
        GENERATED_FLIPS_DIR.glob("*/flips.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No flips CSVs found: {GENERATED_FLIPS_DIR / '*/flips.csv'}"
        )
    return candidates[-1]


def main() -> None:
    flips_csv = _pick_latest_flips_csv()
    out_fp = flips_csv.parent / "high_toxic.csv"

    df = pd.read_csv(flips_csv)
    if "sample_toxicity_type" not in df.columns:
        raise KeyError(f"Missing `sample_toxicity_type` column in {flips_csv}")

    high_toxic = df[df["sample_toxicity_type"] == HIGH_TOXICITY].reset_index(drop=True)
    high_toxic.to_csv(out_fp, index=False)

    print(f"Input:  {flips_csv} ({len(df):,} rows)")
    print(f"Output: {out_fp} ({len(high_toxic):,} high-toxicity rows)")


if __name__ == "__main__":
    main()
