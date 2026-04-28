"""Loads the pilot data and gets the mirrors data."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from lib.timestamp_utils import get_current_timestamp

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.expand_frame_repr", False)


class Dataloader:
    """Locate latest export CSVs and produce the curated trial-level table."""

    EXPERIMENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = EXPERIMENT_DIR.parent.parent
    SCRIPTS_DIR = PROJECT_ROOT / "scripts"

    EXPORT_FILENAME_PATTERN = re.compile(
        r"^mirrorview_pilot_data_(\d{4}_\d{2}_\d{2}-\d{2}:\d{2}:\d{2})\.csv$"
    )
    TIMESTAMP_FORMAT = "%Y_%m_%d-%H:%M:%S"

    def _resolve_latest_export_csv_path(self) -> Path:
        """Path to the newest ``mirrorview_pilot_data_*.csv`` under ``scripts/``."""
        candidates: list[tuple[datetime, Path]] = []
        for path in self.SCRIPTS_DIR.glob("mirrorview_pilot_data_*.csv"):
            match = self.EXPORT_FILENAME_PATTERN.match(path.name)
            if not match:
                continue
            candidates.append(
                (datetime.strptime(match.group(1), self.TIMESTAMP_FORMAT), path)
            )

        if not candidates:
            raise FileNotFoundError(
                f"No timestamped mirrorview_pilot_data_*.csv under {self.SCRIPTS_DIR}. "
                "Run: PYTHONPATH=. uv run python scripts/export_study_results.py"
            )

        _, latest_path = max(candidates, key=lambda item: item[0])
        return latest_path

    @property
    def last_loaded_export_path(self) -> Path | None:
        """Set to the CSV path used by the last ``get_latest_mirrorview_run_data`` call."""
        return getattr(self, "_last_loaded_export_path", None)

    def get_latest_mirrorview_run_data(self) -> pd.DataFrame:
        """Load the newest export CSV under ``scripts/`` as a DataFrame.

        Files are named ``mirrorview_pilot_data_<timestamp>.csv`` by
        ``scripts/export_study_results.py``. The latest file is chosen by the
        timestamp embedded in the filename (same rule as
        ``experiments/basic_summary_stats_2026_04_27/total_attrition.py``).
        """
        latest_path = self._resolve_latest_export_csv_path()
        self._last_loaded_export_path = latest_path
        return pd.read_csv(latest_path)

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
