"""Simplified keep/remove dataloader: one row per ``post_id`` with majority decision.

Aggregates the per-rater rows from
``experiments.predict_keep_remove_2026_05_07.dataloader.Dataloader`` by ``post_id``.

To run (from repository root):

    PYTHONPATH=. uv run python experiments/simplified_predict_remove_2026_05_13/dataloader.py
"""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader as ParentDataloader


def _mode_or_first(series: pd.Series) -> object:
    modes = series.mode()
    if len(modes):
        return modes.iloc[0]
    return series.iloc[0]


class Dataloader(ParentDataloader):
    """Aggregate pilot-linked keep/remove rows to one row per ``post_id``."""

    def load_training_dataframe(self) -> pd.DataFrame:
        raw = super().load_training_dataframe()
        toxicity_src = "sample_toxicity_type"
        if toxicity_src not in raw.columns:
            raise KeyError(
                f"Expected column {toxicity_src!r} from parent loader; "
                f"got columns: {sorted(raw.columns)}"
            )
        base = (
            raw.groupby("post_id", as_index=False)
            .agg(
                original_text=("original_text", "first"),
                mirror_text=("mirror_text", "first"),
                sampled_toxicity=(toxicity_src, "first"),
                sampled_stance=("sampled_stance", "first"),
                decision=("decision", _mode_or_first),
            )
        )
        base["keep_remove_label"] = (base["decision"] == "remove").astype(int)
        return base


if __name__ == "__main__":
    df = Dataloader().load_training_dataframe()
    print(f"Row count: {len(df)}")
    print(f"Unique post_id: {df['post_id'].nunique()}")
    print("keep_remove_label value counts:")
    print(df["keep_remove_label"].value_counts(dropna=False).sort_index())
