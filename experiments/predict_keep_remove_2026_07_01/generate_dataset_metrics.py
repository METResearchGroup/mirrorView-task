"""Generate dataset metrics for the keep/remove prediction dataset.

How to run (from repo root):
`PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/generate_dataset_metrics.py`

This prints a dataset overview table for the "linked fate" keep/remove decision rows:
- total row count
- unique `post_id` count
- average rows per `post_id`
- unique participant count via `prolific_id`
- approximate unique (original_text, mirror_text) pair count via stable text hashes
"""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_2026_05_07.embeddings.text_hash import text_hash
from experiments.predict_keep_remove_2026_07_01.dataloader import Dataloader


def _load_linked_fate_keep_remove_rows() -> pd.DataFrame:
    """Load raw linked-fate keep/remove decision rows."""
    return Dataloader().load_trial_dataframe()


def main() -> None:
    """Print dataset overview metrics."""
    df = _load_linked_fate_keep_remove_rows().copy()

    required = [
        "post_id",
        "prolific_id",
        "original_text",
        "mirror_text",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Dataset is missing required columns: {missing}")

    # Approximate unique (original_text, mirror_text) pairs using stable text hashes.
    orig_hash = df["original_text"].fillna("").astype(str).map(text_hash)
    mirr_hash = df["mirror_text"].fillna("").astype(str).map(text_hash)
    pair_hash = (orig_hash + "||" + mirr_hash).map(text_hash)

    post_counts = df["post_id"].astype(str).value_counts(dropna=False)
    avg_rows_per_post_id = float(post_counts.mean()) if len(post_counts) else float("nan")

    overview = pd.DataFrame(
        [
            {"metric": "n_rows", "value": int(len(df))},
            {"metric": "unique_post_id", "value": int(df["post_id"].astype(str).nunique())},
            {"metric": "avg_rows_per_post_id", "value": avg_rows_per_post_id},
            {
                "metric": "unique_participants_prolific_id",
                "value": int(df["prolific_id"].astype(str).nunique()),
            },
            {
                "metric": "unique_(original_text,mirror_text)_pairs__via_hash",
                "value": int(pair_hash.nunique()),
            },
        ]
    )

    print("\n=== Dataset overview (linked-fate keep/remove decision rows) ===")
    print(overview.to_string(index=False))


if __name__ == "__main__":
    main()

