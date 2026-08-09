"""PRIME classifier for MirrorView run data.

To run:

PYTHONPATH=. uv run python experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader
from shared.textual_features.prime import (
    PrimeClassification,
    classify_post,
    classify_texts,
    get_llm,
)

PRIME_CLASSIFIER_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = PRIME_CLASSIFIER_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = PRIME_CLASSIFIER_DIR / "labels_mirrors.csv"

__all__ = [
    "LABELS_MIRRORS_PATH",
    "LABELS_ORIGINAL_PATH",
    "PRIME_CLASSIFIER_DIR",
    "PrimeClassification",
    "classify_post",
    "classify_posts",
    "classify_texts",
    "get_llm",
]


def _all_mirrors_claude_path() -> Path:
    return Dataloader.PROJECT_ROOT / "img" / "all_mirrors_claude.csv"


def _build_posts_frame(raw: pd.DataFrame, text_column: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_primary_key": raw["post_primary_key"].astype(str),
            "text": raw[text_column].fillna("").astype(str),
        }
    )


def _label_posts_dataframe(posts: pd.DataFrame) -> pd.DataFrame:
    texts = posts["text"].tolist()
    classifications = classify_texts(texts)
    return pd.DataFrame(
        {
            "post_primary_key": posts["post_primary_key"].tolist(),
            "is_prime": [c.is_prime for c in classifications],
        }
    )


def classify_posts() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load Claude mirrors CSV, classify both text columns, and write label CSVs."""
    path = _all_mirrors_claude_path()
    raw = pd.read_csv(path)
    for col in ("post_primary_key", "original_text", "claude_mirror"):
        if col not in raw.columns:
            raise KeyError(f"Expected column {col!r} in {path}")

    original_posts = _build_posts_frame(raw, "original_text")
    mirrored_posts = _build_posts_frame(raw, "claude_mirror")

    labels_original = _label_posts_dataframe(original_posts)
    labels_mirrors = _label_posts_dataframe(mirrored_posts)

    labels_original.to_csv(LABELS_ORIGINAL_PATH, index=False)
    labels_mirrors.to_csv(LABELS_MIRRORS_PATH, index=False)
    return labels_original, labels_mirrors


if __name__ == "__main__":
    classify_posts()
