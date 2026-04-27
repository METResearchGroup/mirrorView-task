"""Loads the pilot data and gets the mirrors data."""

from __future__ import annotations

import pandas as pd
from pathlib import Path

from lib.timestamp_utils import get_current_timestamp

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.expand_frame_repr", False)

timestamp = get_current_timestamp()
export_filename = f"mirrorview_pilot_trial_data_{timestamp}.csv"

current_dir = Path(__file__).resolve().parent
export_fp = current_dir / export_filename


def main() -> None:
    csv_path = (
        "experiments/2026-04-24_mirrors_content_analysis/"
        "mirrorview_pilot_data_2026-04-15.csv"
    )
    df = pd.read_csv(csv_path)

    # get the moderation trial data.
    filtered_df = df[df["trial_type"] == "moderation-trial"].copy()

    # Drop attitude columns (these will be not)
    attitude_columns = [
        col for col in filtered_df.columns if col.startswith("attitude_")
    ]
    filtered_df = filtered_df.drop(columns=attitude_columns)

    # drop all NaN columns.
    filtered_df = filtered_df.dropna(axis=1, how="all")

    # move the key identifier columns to the front.
    first_columns = ["prolific_id", "party_group", "condition"]
    remaining_columns = [col for col in filtered_df.columns if col not in first_columns]
    filtered_df = filtered_df[first_columns + remaining_columns]

    filtered_df.to_csv(export_fp, index=False)
    print(f"Exported filtered data to {export_fp}")
    print(filtered_df.head(10))


if __name__ == "__main__":
    main()
