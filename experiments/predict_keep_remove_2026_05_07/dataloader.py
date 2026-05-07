"""Loads the data + features for the keep/remove prediction problem.

To run:

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/dataloader.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import (
    Dataloader as MirrorViewPilotDataloader,
)


class Dataloader:
    """Load pilot trial rows and join all analysis label features."""

    EXPERIMENT_DIR = Path(__file__).resolve().parent
    MIRROR_ANALYSIS_DIR = (
        EXPERIMENT_DIR.parent / "mirrors_content_analysis_2026_04_24" / "analysis"
    )

    # Label tables produced by analysis modules.
    INTERGROUP_DIR = MIRROR_ANALYSIS_DIR / "intergroup_classifier"
    PRIME_DIR = MIRROR_ANALYSIS_DIR / "prime_classifier"
    VALENCE_DIR = MIRROR_ANALYSIS_DIR / "valence_classifier"
    LENGTH_DIR = MIRROR_ANALYSIS_DIR / "length_compression_analysis"
    READABILITY_DIR = MIRROR_ANALYSIS_DIR / "readability_complexity_analysis"

    ORIGINAL_LABELS_FILENAME = "labels_original_text.csv"
    MIRRORS_LABELS_FILENAME = "labels_mirrors.csv"
    TARGET_COLUMN = "keep_remove_label"

    def load_training_dataframe(self) -> pd.DataFrame:
        """Return one row per moderated pair with text, target, and joined labels."""
        pilot_loader = MirrorViewPilotDataloader()
        raw = pilot_loader.get_latest_mirrorview_run_data()
        trials = pilot_loader.transform_latest_mirrorview_run_data(raw)

        required_trial_cols = {
            "post_id",
            "original_text",
            "mirror_text",
            "decision",
            "evaluation_mode",
            "sample_toxicity_type",
            "sampled_stance",
        }
        missing = required_trial_cols - set(trials.columns)
        if missing:
            raise KeyError(
                "Pilot data is missing required columns for training data: "
                f"{sorted(missing)}"
            )

        base = trials[
            [
                "prolific_id",
                "party_group",
                "condition",
                "phase",
                "evaluation_mode",
                "sample_toxicity_type",
                "sampled_stance",
                "post_id",
                "original_text",
                "mirror_text",
                "decision",
            ]
        ].copy()
        base["post_id"] = base["post_id"].astype(str)
        base["evaluation_mode"] = base["evaluation_mode"].astype(str).str.lower().str.strip()
        base = base[base["evaluation_mode"] == "linked_fate"].copy()
        base["decision"] = base["decision"].astype(str).str.lower().str.strip()
        base = base[base["decision"].isin(["keep", "remove"])].copy()
        base["keep_remove_label"] = (base["decision"] == "keep").astype(int)

        # Keep one canonical text row per post_id for the feature joins.
        text_keys = (
            base[["post_id", "original_text", "mirror_text"]]
            .drop_duplicates(subset=["post_id"], keep="first")
            .copy()
        )

        joined = text_keys.copy()
        joined = self._merge_label_pair(
            joined,
            labels_dir=self.INTERGROUP_DIR,
            dataset_prefix="intergroup_clf",
        )
        joined = self._merge_label_pair(
            joined,
            labels_dir=self.PRIME_DIR,
            dataset_prefix="prime_clf",
        )
        joined = self._merge_label_pair(
            joined,
            labels_dir=self.VALENCE_DIR,
            dataset_prefix="valence_clf",
        )
        joined = self._merge_label_pair(
            joined,
            labels_dir=self.LENGTH_DIR,
            dataset_prefix="length_compression",
        )
        joined = self._merge_label_pair(
            joined,
            labels_dir=self.READABILITY_DIR,
            dataset_prefix="readability_complexity",
        )

        out = base.merge(joined, on=["post_id", "original_text", "mirror_text"], how="left")
        return out

    def generate_train_test_split(
        self,
        *,
        train_split: float = 0.8,
        random_state: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split the labeled training dataframe into train/test sets."""
        if not 0 < train_split < 1:
            raise ValueError(f"train_split must be in (0, 1). Got: {train_split}")

        df = self.load_training_dataframe()
        shuffled = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
        train_count = int(len(shuffled) * train_split)

        train_df = shuffled.iloc[:train_count].copy()
        test_df = shuffled.iloc[train_count:].copy()
        return train_df, test_df

    def _merge_label_pair(
        self,
        df: pd.DataFrame,
        *,
        labels_dir: Path,
        dataset_prefix: str,
    ) -> pd.DataFrame:
        """Join labels_original_text + labels_mirrors for one analysis dataset."""
        original_path = labels_dir / self.ORIGINAL_LABELS_FILENAME
        mirrors_path = labels_dir / self.MIRRORS_LABELS_FILENAME

        labels_original = self._read_labels_csv(
            original_path,
            dataset_prefix=dataset_prefix,
            side_suffix="original_text",
        )
        labels_mirrors = self._read_labels_csv(
            mirrors_path,
            dataset_prefix=dataset_prefix,
            side_suffix="mirrors",
        )

        out = df.merge(labels_original, on="post_id", how="left")
        out = out.merge(labels_mirrors, on="post_id", how="left")
        return out

    def _read_labels_csv(
        self,
        path: Path,
        *,
        dataset_prefix: str,
        side_suffix: str,
    ) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing labels file: {path}. Generate it by running the corresponding "
                "analysis/classifier script first."
            )

        labels = pd.read_csv(path)
        if "post_primary_key" not in labels.columns:
            raise KeyError(f"Expected 'post_primary_key' column in {path}")

        labels = labels.copy()
        labels["post_id"] = labels["post_primary_key"].astype(str)
        labels = labels.drop(columns=["post_primary_key"])

        rename_map: dict[str, str] = {}
        for col in labels.columns:
            if col == "post_id":
                continue
            rename_map[col] = f"{dataset_prefix}_{col}_{side_suffix}"
        labels = labels.rename(columns=rename_map)
        return labels


if __name__ == "__main__":
    pilot_loader = MirrorViewPilotDataloader()
    raw_df = pilot_loader.get_latest_mirrorview_run_data()
    base_df = pilot_loader.transform_latest_mirrorview_run_data(raw_df)
    base_df = base_df.copy()
    base_df["evaluation_mode"] = base_df["evaluation_mode"].astype(str).str.lower().str.strip()
    base_df = base_df[base_df["evaluation_mode"] == "linked_fate"].copy()
    base_df["decision"] = base_df["decision"].astype(str).str.lower().str.strip()
    base_df = base_df[base_df["decision"].isin(["keep", "remove"])].copy()

    loader = Dataloader()
    features_df = loader.load_training_dataframe()

    base_rows = len(base_df)
    feature_rows = len(features_df)

    print(f"Base keep/remove rows: {base_rows}")
    print(f"Rows with analysis label features: {feature_rows}")

    if base_rows != feature_rows:
        raise ValueError(
            "Row-count mismatch between base keep/remove rows and joined feature rows: "
            f"{base_rows} != {feature_rows}"
        )

    print("Validation passed: row counts match.")
