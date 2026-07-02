"""Loads the pilot data and gets the mirrors data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib.timestamp_utils import get_current_timestamp

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.expand_frame_repr", False)


class Dataloader:
    """Load a pinned export CSV and produce the curated trial-level table."""

    EXPERIMENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = EXPERIMENT_DIR.parent.parent
    SCRIPTS_DIR = PROJECT_ROOT / "scripts"

    # Pinned export used for reproducible analysis across experiments.
    PINNED_EXPORT_FILENAME = "mirrorview_pilot_data_2026_04_28-16:31:47.csv"
    PINNED_EXPORT_PATH = EXPERIMENT_DIR / PINNED_EXPORT_FILENAME

    @property
    def last_loaded_export_path(self) -> Path | None:
        """Set to the CSV path used by the last ``get_latest_mirrorview_run_data`` call."""
        return getattr(self, "_last_loaded_export_path", None)

    def get_latest_mirrorview_run_data(self) -> pd.DataFrame:
        """Load the pinned export CSV as a DataFrame."""
        if not self.PINNED_EXPORT_PATH.exists():
            raise FileNotFoundError(
                f"Pinned export CSV not found at {self.PINNED_EXPORT_PATH}. "
                "If you intended to use a different export, update PINNED_EXPORT_FILENAME "
                "and ensure the file is present."
            )
        self._last_loaded_export_path = self.PINNED_EXPORT_PATH
        return pd.read_csv(self.PINNED_EXPORT_PATH, low_memory=False)

    def transform_latest_mirrorview_run_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter and reshape the raw export frame into the trial-level mirrors table."""
        # get the moderation trial data.
        filtered_df = df[df["trial_type"] == "moderation-trial"].copy()

        # Keep only analytic phases (>0): excludes phase 0 tutorial rows and missing phase rows.
        phase_num = pd.to_numeric(filtered_df["phase"], errors="coerce")
        filtered_df = filtered_df.loc[phase_num.gt(0)].copy()

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
        return filtered_df[first_columns + remaining_columns]


timestamp = get_current_timestamp()
export_filename = f"mirrorview_pilot_trial_data_{timestamp}.csv"
export_fp = Dataloader.EXPERIMENT_DIR / export_filename


def main() -> None:
    loader = Dataloader()
    df = loader.get_latest_mirrorview_run_data()
    transformed_df = loader.transform_latest_mirrorview_run_data(df)
    transformed_df.to_csv(export_fp, index=False)
    print(f"Source export: {loader.last_loaded_export_path}")
    print(f"Exported filtered data to {export_fp}")
    print(transformed_df.head(10))


if __name__ == "__main__":
    main()
