"""Data loading for keep/remove prediction (2026-07-01 run).

Trial-level rows come from the experiment CSV
``keep_remove_results_2026_06_23.csv``. Training labels come from the shared
registry dataset ``STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`` (one modal
keep/remove row per post; ties → remove).

We provide:
1) `load_trial_dataframe()`: one row per trial (slim linked-fate CSV).
2) `load_training_dataframe()`: shared materialized modal labels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = EXPERIMENT_ROOT / "keep_remove_results_2026_06_23.csv"


class Dataloader:
    """Load the keep/remove dataset and shape it for training/metrics."""

    def load_trial_dataframe(self) -> pd.DataFrame:
        """Return decision rows (raw trial rows).

        Current CSV format is expected to already be "linked-fate" keep/remove
        decisions, but this loader defensively supports an `evaluation_mode`
        column if present.
        """
        df = pd.read_csv(CSV_PATH, low_memory=False)

        df = df.copy()
        df["decision"] = df["decision"].astype(str).str.lower().str.strip()

        if "post_id" in df.columns:
            df["post_id"] = df["post_id"].astype(str)
        elif "message_id" in df.columns:
            # In the simplified export, message_id corresponds to the canonical post key.
            df["post_id"] = df["message_id"].astype(str)
        else:
            raise KeyError("Expected `post_id` or `message_id` column in the dataset CSV.")

        if "evaluation_mode" in df.columns:
            df["evaluation_mode"] = df["evaluation_mode"].astype(str).str.lower().str.strip()
            df = df[df["evaluation_mode"] == "linked_fate"].copy()

        df = df[df["decision"].isin(["keep", "remove"])].copy()
        return df

    def load_training_dataframe(self) -> pd.DataFrame:
        """Return one row per post with modal decision from the shared registry."""
        return load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)


if __name__ == "__main__":
    loader = Dataloader()
    print("Trial rows:", len(loader.load_trial_dataframe()))
    print("Training rows:", len(loader.load_training_dataframe()))
