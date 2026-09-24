"""Shared keep/remove trial filtering and label aggregation.

Used by Part 2 and Part 3 transformed label builders.
"""

from __future__ import annotations

import pandas as pd

_KEEP_REMOVE = frozenset({"keep", "remove"})

_MODAL_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
]

_UNANIMOUS_OUTPUT_COLUMNS = _MODAL_OUTPUT_COLUMNS


def _normalize_keep_remove_trials(raw: pd.DataFrame) -> pd.DataFrame:
    """Apply linked-fate keep/remove filtering without worker-post dedupe."""
    if "decision" not in raw.columns:
        raise KeyError("Expected `decision` column in study results.")
    if "evaluation_mode" not in raw.columns:
        raise KeyError("Expected `evaluation_mode` column in study results.")
    if "post_id" not in raw.columns:
        raise KeyError("Expected `post_id` column in study results.")

    trials = raw.copy()
    trials["decision"] = trials["decision"].astype(str).str.lower().str.strip()
    trials["evaluation_mode"] = (
        trials["evaluation_mode"].astype(str).str.lower().str.strip()
    )
    trials = trials[trials["evaluation_mode"] == "linked_fate"].copy()
    trials = trials[trials["decision"].isin(_KEEP_REMOVE)].copy()

    post_id = trials["post_id"]
    trials = trials[post_id.notna()].copy()
    trials["post_id"] = trials["post_id"].astype(str).str.strip()
    trials = trials[trials["post_id"] != ""].copy()
    trials = trials[trials["post_id"].str.lower() != "nan"].copy()
    return trials


def filter_keep_remove_trials(
    raw: pd.DataFrame,
    *,
    dedupe_worker_post: bool = False,
) -> pd.DataFrame:
    """Select linked-fate keep/remove trials with a usable ``post_id``.

    Normalizes ``decision`` and ``evaluation_mode`` for comparison. Rows with
    null, empty, or literal ``"nan"`` post IDs are dropped.

    When ``dedupe_worker_post`` is True, drop all rows for any
    ``(prolific_id, post_id)`` pair whose decisions conflict, then keep the
    earliest row per pair by original CSV row order.

    Parameters
    ----------
    raw
        Raw study results frame.
    dedupe_worker_post
        When True, deduplicate conflicting worker-post pairs (Part 3 path).
        When False, skip dedupe (Part 2 byte-identical path).

    Returns
    -------
    pandas.DataFrame
        Filtered trial rows.

    Raises
    ------
    KeyError
        If ``evaluation_mode``, ``post_id``, or ``decision`` is missing.
    """
    trials = _normalize_keep_remove_trials(raw)
    if not dedupe_worker_post:
        return trials

    if "prolific_id" not in trials.columns:
        raise KeyError("Expected `prolific_id` column in study results.")

    trials = trials.reset_index(drop=True)
    trials["_row_order"] = trials.index

    pair_decisions = (
        trials.groupby(["prolific_id", "post_id"], dropna=False)["decision"]
        .nunique()
        .reset_index(name="n_unique_decisions")
    )
    conflicting_pairs = pair_decisions.loc[
        pair_decisions["n_unique_decisions"] > 1, ["prolific_id", "post_id"]
    ]
    if len(conflicting_pairs):
        trials = trials.merge(
            conflicting_pairs.assign(_conflict=True),
            on=["prolific_id", "post_id"],
            how="left",
        )
        trials = trials[trials["_conflict"].isna()].drop(columns="_conflict")

    trials = (
        trials.sort_values("_row_order")
        .drop_duplicates(subset=["prolific_id", "post_id"], keep="first")
        .sort_values("_row_order")
        .drop(columns="_row_order")
        .reset_index(drop=True)
    )
    return trials


def _assert_stable_texts(trials: pd.DataFrame) -> None:
    """Raise if any ``post_id`` has conflicting original or mirror text."""
    text_nunique = (
        trials.groupby("post_id", dropna=False)
        .agg(
            original_text_nunique=("original_text", lambda s: s.fillna("").nunique()),
            mirror_text_nunique=("mirror_text", lambda s: s.fillna("").nunique()),
        )
        .reset_index()
    )
    bad = text_nunique[
        (text_nunique["original_text_nunique"] != 1)
        | (text_nunique["mirror_text_nunique"] != 1)
    ]
    if len(bad):
        example_post = str(bad.iloc[0]["post_id"])
        raise ValueError(
            "Expected stable original/mirror text per post_id, but found conflicts. "
            f"Example problematic post_id={example_post}."
        )


def aggregate_modal_labels(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trials to one modal keep/remove label per post.

    Modal decision is ``keep`` only when ``keep_count > remove_count``; ties
    become ``remove``. ``keep_remove_label`` is ``1`` for remove and ``0`` for
    keep. ``n_raters`` is the unique ``prolific_id`` count per post.

    Parameters
    ----------
    trials
        Filtered trial rows with ``post_id``, ``original_text``,
        ``mirror_text``, ``decision``, and ``prolific_id``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``message_id``, ``original_text``, ``mirror_text``,
        ``decision``, ``keep_remove_label``, ``n_raters``.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    required = {"post_id", "original_text", "mirror_text", "decision", "prolific_id"}
    missing = required - set(trials.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")

    _assert_stable_texts(trials)

    counts = (
        trials.groupby(["post_id", "decision"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    if "keep" not in counts.columns:
        counts["keep"] = 0
    if "remove" not in counts.columns:
        counts["remove"] = 0

    counts["decision"] = counts.apply(
        lambda row: "keep" if int(row["keep"]) > int(row["remove"]) else "remove",
        axis=1,
    )
    counts["keep_remove_label"] = (counts["decision"] == "remove").astype(int)

    n_raters = (
        trials.groupby("post_id", dropna=False)["prolific_id"]
        .nunique()
        .reset_index(name="n_raters")
    )
    counts = counts.merge(n_raters, on="post_id", how="left")

    texts = trials.drop_duplicates(subset=["post_id"])[
        ["post_id", "original_text", "mirror_text"]
    ]
    out = counts.merge(texts, on="post_id", how="left")
    out = out.rename(columns={"post_id": "message_id"})
    return out[_MODAL_OUTPUT_COLUMNS].reset_index(drop=True)


def aggregate_unanimous_labels(
    trials: pd.DataFrame,
    *,
    min_raters: int = 3,
) -> pd.DataFrame:
    """Aggregate trials to unanimous posts with at least ``min_raters`` raters.

    Per ``post_id``, ``n_raters`` counts trial rows (equals unique
    ``prolific_id`` after Part 3 dedupe). Keeps posts where all decisions
    agree and ``n_raters >= min_raters``.

    Parameters
    ----------
    trials
        Filtered trial rows.
    min_raters
        Minimum trial count required per post.

    Returns
    -------
    pandas.DataFrame
        Columns: ``message_id``, ``original_text``, ``mirror_text``,
        ``decision``, ``keep_remove_label``, ``n_raters``.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    raise NotImplementedError
