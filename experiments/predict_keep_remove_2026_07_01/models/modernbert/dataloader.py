"""Classifier dataframe and stratified 80/10/10 splits for ModernBERT.

Maps parent training rows (original text only) to ``text`` / ``label`` columns
and produces a stratified train/val/test split.

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python -c \\
      "from experiments.predict_keep_remove_2026_07_01.models.modernbert.dataloader import load_classifier_dataframe, make_train_val_test_split; df=load_classifier_dataframe(); tr,va,te=make_train_val_test_split(df); print(len(df), len(tr), len(va), len(te), set(df['label']))"
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader


def load_classifier_dataframe() -> pd.DataFrame:
    """Load training rows with original text and binary keep/remove labels.

    Returns:
        DataFrame with columns ``message_id``, ``text``, ``label``, and
        ``keep_remove_label`` (identical to ``label``; ``1=remove``, ``0=keep``).
    """
    source = Dataloader().load_training_dataframe()
    out = pd.DataFrame(
        {
            "message_id": source["message_id"].astype(str),
            "text": source["original_text"].fillna("").astype(str),
            "label": source["keep_remove_label"].astype(int),
        }
    )
    out["keep_remove_label"] = out["label"]
    return out


def make_train_val_test_split(
    df: pd.DataFrame,
    *,
    train_fraction: float = 0.8,
    val_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 42,
    label_column: str = "label",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Two-stage stratified split into train / val / test.

    First splits train vs temp at ``train_fraction``, then splits temp into
    val/test with relative share ``val_fraction / (val_fraction + test_fraction)``.
    """
    if label_column not in df.columns:
        raise KeyError(f"Missing label column {label_column!r}")

    total = train_fraction + val_fraction + test_fraction
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"train/val/test fractions must sum to 1.0, got {total}"
        )
    if not (0.0 < train_fraction < 1.0):
        raise ValueError("train_fraction must be between 0 and 1 (exclusive).")
    if val_fraction <= 0.0 or test_fraction <= 0.0:
        raise ValueError("val_fraction and test_fraction must be positive.")

    train_df, temp_df = train_test_split(
        df,
        train_size=train_fraction,
        stratify=df[label_column],
        random_state=seed,
    )
    val_share = val_fraction / (val_fraction + test_fraction)
    val_df, test_df = train_test_split(
        temp_df,
        train_size=val_share,
        stratify=temp_df[label_column],
        random_state=seed,
    )
    return (
        train_df.reset_index(drop=True),
        val_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )
