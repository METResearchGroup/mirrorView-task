"""Dataset and split helpers for keep/remove prompting.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.dataloader import Dataloader
from experiments.simplified_predict_remove_2026_05_13.splits import make_train_test_split

KeepRemoveLabelInt = Literal[0, 1]


def label_int_to_decision(label: KeepRemoveLabelInt) -> str:
    return "remove" if int(label) == 1 else "keep"


@dataclass(frozen=True)
class SupportExample:
    message_id: str
    original_text: str
    mirror_text: str
    keep_remove_label: KeepRemoveLabelInt

    @property
    def decision(self) -> str:
        return label_int_to_decision(self.keep_remove_label)


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
    # Deterministic subsample for reproducible smoke runs.
    return df.sample(n=n, random_state=seed).copy()


def select_support_examples(
    train_df: pd.DataFrame,
    *,
    support_examples: int,
    seed: int,
) -> tuple[list[SupportExample], pd.DataFrame]:
    """Select support examples from train fold; return (support, train_scored_df)."""
    n = min(int(support_examples), len(train_df))
    if n <= 0:
        return [], train_df

    reserved = train_df.sample(n=n, random_state=seed).copy()
    reserved_ids = set(reserved["message_id"].astype(str).tolist())
    train_scored_df = train_df[~train_df["message_id"].astype(str).isin(reserved_ids)].copy()

    support = [
        SupportExample(
            message_id=str(r["message_id"]),
            original_text=str(r["original_text"]),
            mirror_text=str(r["mirror_text"]),
            keep_remove_label=int(r["keep_remove_label"]),
        )
        for _, r in reserved.iterrows()
    ]
    return support, train_scored_df

