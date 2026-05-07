"""Join PRIME-classifier labels onto transformed MirrorView run data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader

PRIME_CLASSIFIER_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = PRIME_CLASSIFIER_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = PRIME_CLASSIFIER_DIR / "labels_mirrors.csv"


def get_mirrorview_run_data_with_labels() -> pd.DataFrame:
    """Attach PRIME labels to the latest transformed MirrorView trial table."""
    dataloader = Dataloader()
    df = dataloader.get_latest_mirrorview_run_data()
    df = dataloader.transform_latest_mirrorview_run_data(df)

    if "post_id" not in df.columns:
        raise KeyError(
            "Transformed MirrorView data must include 'post_id' to join PRIME labels."
        )

    labels_original_text = pd.read_csv(LABELS_ORIGINAL_PATH)
    labels_mirrors = pd.read_csv(LABELS_MIRRORS_PATH)

    for lbl_df, path in (
        (labels_original_text, LABELS_ORIGINAL_PATH),
        (labels_mirrors, LABELS_MIRRORS_PATH),
    ):
        if "post_primary_key" not in lbl_df.columns or "is_prime" not in lbl_df.columns:
            raise KeyError(
                f"Expected columns 'post_primary_key' and 'is_prime' in {path}"
            )

    orig_join = labels_original_text[["post_primary_key", "is_prime"]].rename(
        columns={"is_prime": "prime_clf_label_original_text"}
    )
    mir_join = labels_mirrors[["post_primary_key", "is_prime"]].rename(
        columns={"is_prime": "prime_clf_label_mirrors"}
    )

    out = df.merge(
        orig_join,
        left_on="post_id",
        right_on="post_primary_key",
        how="left",
    ).drop(columns=["post_primary_key"])

    out = out.merge(
        mir_join,
        left_on="post_id",
        right_on="post_primary_key",
        how="left",
    ).drop(columns=["post_primary_key"])

    return out
