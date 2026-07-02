"""Data loading for keep/remove prediction (2026-07-01 run).

This experiment uses a CSV export `keep_remove_results_2026_06_23.csv` containing
linked-fate keep/remove trials.

We provide:
1) `load_trial_dataframe()`: one row per trial (i.e. the raw linked-fate decision rows).
2) `load_training_dataframe()`: one row per `post_id` with modal decision across raters.
   If keep/remove counts are tied, we choose `remove`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


CSV_PATH = Path(__file__).resolve().parent / "keep_remove_results_2026_06_23.csv"


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
        """Return one row per post with modal decision (tie => remove)."""
        trials = self.load_trial_dataframe()

        required_cols = {
            "post_id",
            "original_text",
            "mirror_text",
            "decision",
        }
        missing = required_cols - set(trials.columns)
        if missing:
            raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")

        # Validate that each post_id has a stable text pair (otherwise modal decision alone
        # wouldn't define a unique example).
        text_nunique = (
            trials.groupby("post_id", dropna=False)
            .agg(
                original_text_nunique=("original_text", lambda s: s.fillna("").nunique()),
                mirror_text_nunique=("mirror_text", lambda s: s.fillna("").nunique()),
            )
            .reset_index()
        )
        bad = text_nunique[
            (text_nunique["original_text_nunique"] != 1)
            | (text_nunique["mirror_text_nunique"] != 1)
        ]
        if len(bad):
            example_post = str(bad.iloc[0]["post_id"])
            raise ValueError(
                "Expected stable original/mirror text per post_id, but found conflicts. "
                f"Example problematic post_id={example_post}."
            )

        # Modal decision with explicit tie-breaking: remove wins ties.
        counts = (
            trials.groupby(["post_id", "decision"], dropna=False)
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        # Ensure both columns exist.
        if "keep" not in counts.columns:
            counts["keep"] = 0
        if "remove" not in counts.columns:
            counts["remove"] = 0

        counts["decision"] = counts.apply(
            lambda r: "keep" if int(r["keep"]) > int(r["remove"]) else "remove", axis=1
        )
        counts["keep_remove_label"] = (counts["decision"] == "remove").astype(int)

        # Attach canonical text pair (take first; validated unique above).
        texts = (
            trials.drop_duplicates(subset=["post_id"])[["post_id", "original_text", "mirror_text"]]
        )

        out = counts.merge(texts, on="post_id", how="left")

        # Provide both keys for downstream compatibility.
        out = out.rename(columns={"post_id": "message_id"})
        out = out[["message_id", "original_text", "mirror_text", "decision", "keep_remove_label"]]
        return out


if __name__ == "__main__":
    loader = Dataloader()
    print("Trial rows:", len(loader.load_trial_dataframe()))
    print("Training rows:", len(loader.load_training_dataframe()))

