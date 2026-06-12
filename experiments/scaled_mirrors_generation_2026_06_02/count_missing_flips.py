"""Count data records whose IDs are missing from a flips CSV, per integration."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror import (
    normalize_mirrorview_df,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
DATA_ROOT = EXPERIMENT_DIR / "data"
FLIPS_CSV = EXPERIMENT_DIR / "generated_flips/2026_06_03-03:23:24/flips.csv"
INTEGRATIONS = ("twitter", "bluesky", "reddit")


def load_data_records() -> pd.DataFrame:
    metadata_fps = sorted(DATA_ROOT.glob("*/*/curated/*/metadata.json"))
    if not metadata_fps:
        raise RuntimeError(f"No metadata.json files found under `{DATA_ROOT}`.")

    frames: list[pd.DataFrame] = []

    for metadata_fp in metadata_fps:
        integration = metadata_fp.relative_to(DATA_ROOT).parts[0]
        if integration not in INTEGRATIONS:
            continue

        metadata = json.loads(metadata_fp.read_text(encoding="utf-8"))
        export_fp = metadata_fp.parent / metadata["files"]["export"]
        if not export_fp.exists():
            raise RuntimeError(f"Missing export for `{metadata_fp}` (expected `{export_fp}`).")

        df = normalize_mirrorview_df(pd.read_csv(export_fp), integration=integration)
        frames.append(df[["post_id", "integration"]])

    return pd.concat(frames, ignore_index=True)


def load_flips() -> pd.DataFrame:
    return pd.read_csv(FLIPS_CSV, dtype={"ID": str})


def main() -> None:
    data_df = load_data_records()
    flips_df = load_flips()
    flip_ids = set(flips_df["ID"].astype(str))

    print(f"Data root: {DATA_ROOT}")
    print(f"Flips CSV: {FLIPS_CSV}")
    print()

    for integration in INTEGRATIONS:
        subset = data_df[data_df["integration"] == integration]
        flip_subset = flips_df[flips_df["ID"].str.startswith(f"{integration}_")]

        missing_mask = ~subset["post_id"].isin(flip_ids)
        missing_records = subset[missing_mask]
        missing_unique_ids = set(missing_records["post_id"])

        print(f"=== {integration} ===")
        print(f"data records:           {len(subset):,}")
        print(f"unique data IDs:          {subset['post_id'].nunique():,}")
        print(f"flip rows:                {len(flip_subset):,}")
        print(f"unique flip IDs:          {flip_subset['ID'].nunique():,}")
        print(f"missing data records:     {len(missing_records):,}")
        print(f"missing unique data IDs:  {len(missing_unique_ids):,}")
        print()


if __name__ == "__main__":
    main()
