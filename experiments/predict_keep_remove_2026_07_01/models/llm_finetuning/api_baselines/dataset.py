"""Dataset helpers for Bedrock keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.dataloader import Dataloader


def load_dataset() -> pd.DataFrame:
    """Load the full canonical keep/remove dataset (no train/test split)."""
    return Dataloader().load_training_dataframe()


def maybe_limit_df(
    df: pd.DataFrame,
    *,
    limit: Optional[int],
    seed: int,
) -> pd.DataFrame:
    if limit is None:
        return df
    n = min(int(limit), len(df))
    if n <= 0:
        return df.iloc[0:0].copy()
    return df.sample(n=n, random_state=seed).copy()
