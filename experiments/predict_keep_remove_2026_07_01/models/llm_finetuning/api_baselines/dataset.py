"""Dataset and split helpers for Bedrock keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.dataloader import Dataloader
from experiments.simplified_predict_remove_2026_05_13.splits import make_train_test_split


def load_train_test_splits(
    *,
    train_split: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load canonical dataset and produce a stratified train/test split."""
    df = Dataloader().load_training_dataframe()
    train_df, test_df = make_train_test_split(
        df,
        train_split=train_split,
        seed=seed,
        label_column="keep_remove_label",
    )
    return train_df, test_df


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
