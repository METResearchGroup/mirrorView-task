"""Flatten mining rows and deduplicate features by category and normalized text.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/run.py
"""

from __future__ import annotations

import re

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    FEATURE_CATEGORIES,
    FEATURE_SIDES,
    SIDE_KEPT,
    SIDE_REMOVED,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
_SIDE_BY_FIELD = {
    FEATURE_SIDES[0]: SIDE_KEPT,
    FEATURE_SIDES[1]: SIDE_REMOVED,
}


def flatten_candidate_rows(rows: list[dict]) -> pd.DataFrame:
    """Expand mining rows into one record per non-empty feature string.

    Parameters
    ----------
    rows
        Step 2 candidate feature rows with ``source_record_id`` and side dicts.

    Returns
    -------
    pandas.DataFrame
        Columns ``batch_id``, ``side``, ``category``, ``position``, and ``text``.
    """
    records: list[dict[str, object]] = []
    for row in rows:
        batch_id = row["source_record_id"]
        for side_field in FEATURE_SIDES:
            side = _SIDE_BY_FIELD[side_field]
            categories = row[side_field]
            for category in FEATURE_CATEGORIES:
                for position, text in enumerate(categories[category]):
                    if not isinstance(text, str) or not text.strip():
                        continue
                    records.append(
                        {
                            "batch_id": batch_id,
                            "side": side,
                            "category": category,
                            "position": position,
                            "text": text,
                        }
                    )
    return pd.DataFrame.from_records(records)


def normalize_feature_text(text: str) -> str:
    """Build the deduplication key for a feature string.

    Lowercases, keeps ``[a-z0-9']+`` tokens, drops English stop words, and joins
    with a single space. When no tokens remain, returns the lowercased stripped
    text.

    Parameters
    ----------
    text
        Raw feature phrase.

    Returns
    -------
    str
        Normalized duplicate key.
    """
    lowered = text.lower()
    tokens = _TOKEN_PATTERN.findall(lowered)
    kept = [token for token in tokens if token not in ENGLISH_STOP_WORDS]
    if kept:
        return " ".join(kept)
    return lowered.strip()


def dedupe_features(flat: pd.DataFrame) -> pd.DataFrame:
    """Collapse flat records to one row per category and normalized key.

    The kept ``text`` comes from the first record when sorting by ``batch_id``,
    then ``side``, then ``position``. ``feature_id`` is ``{category}__{index:05d}``
    with a zero-based index within each category after sorting by category and key.

    Parameters
    ----------
    flat
        Output of :func:`flatten_candidate_rows`.

    Returns
    -------
    pandas.DataFrame
        Columns ``feature_id``, ``category``, ``text``, ``normalized_text``,
        ``n_occurrences``, ``n_batches``, ``n_kept_side``, ``n_removed_side``,
        and ``batch_ids``.
    """
    working = flat.copy()
    working["normalized_text"] = working["text"].map(normalize_feature_text)

    grouped_rows: list[dict[str, object]] = []
    for (category, normalized_text), group in working.groupby(
        ["category", "normalized_text"], sort=False
    ):
        ordered = group.sort_values(["batch_id", "side", "position"])
        first = ordered.iloc[0]
        batch_ids = sorted(group["batch_id"].unique().tolist())
        grouped_rows.append(
            {
                "category": category,
                "text": first["text"],
                "normalized_text": normalized_text,
                "n_occurrences": len(group),
                "n_batches": group["batch_id"].nunique(),
                "n_kept_side": int((group["side"] == SIDE_KEPT).sum()),
                "n_removed_side": int((group["side"] == SIDE_REMOVED).sum()),
                "batch_ids": batch_ids,
            }
        )

    result = pd.DataFrame.from_records(grouped_rows)
    result = result.sort_values(["category", "normalized_text"]).reset_index(drop=True)
    within_category = result.groupby("category", sort=True).cumcount()
    result["feature_id"] = result["category"] + "__" + within_category.map(
        lambda index: f"{int(index):05d}"
    )
    column_order = [
        "feature_id",
        "category",
        "text",
        "normalized_text",
        "n_occurrences",
        "n_batches",
        "n_kept_side",
        "n_removed_side",
        "batch_ids",
    ]
    return result[column_order]
