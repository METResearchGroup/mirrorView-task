"""Summarize marker rates and paired prompt-arm differences.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment4.markers import (
    density_per_thousand,
    score_trace_detail,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    STATUS_VALID,
)

RATE_KEYS = ("prompt_arm", "model_id", "group")
RATE_COLUMNS = (
    "prompt_arm",
    "model_id",
    "group",
    "n_valid",
    "uncertainty_rate",
    "revision_rate",
    "tension_rate",
)
STRICT_RATE_COLUMNS = (
    "prompt_arm",
    "model_id",
    "group",
    "n_valid",
    "uncertainty_rate",
    "revision_rate",
    "tension_rate",
    "uncertainty_density",
    "revision_density",
    "tension_density",
)
ITEM_RATE_COLUMNS = (
    "prompt_arm",
    "model_id",
    "group",
    "family",
    "kind",
    "item",
    "n_valid",
    "rate",
)
CONTRAST_COLUMNS = (
    "prompt_arm",
    "model_id",
    "family",
    "metric",
    "split",
    "keep",
    "remove",
    "split_minus_keep",
    "split_minus_remove",
)
FAMILIES = ("uncertainty", "revision", "tension")
CONTRAST_METRICS = ("rate", "density")
CONTRAST_GROUPS = (GROUP_SPLIT, GROUP_UNANIMOUS_KEEP, GROUP_UNANIMOUS_REMOVE)
PAIR_KEYS = ("post_id", "model_id")
E1_SUFFIX = "_e1"
E2_SUFFIX = "_e2"


def marker_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write broad family-flag rates for each prompt_arm, model_id, and group.

    Only ``status=valid`` rows are scored. Rates are the share of those rows
    with each family flag.
    """
    scored = _valid_scored(traces)
    if scored.empty:
        return pd.DataFrame(columns=list(RATE_COLUMNS))
    rows = [
        _rate_row(arm, model_id, group, subset, "uncertainty", "revision", "tension")
        for (arm, model_id, group), subset in scored.groupby(list(RATE_KEYS), sort=False)
    ]
    return pd.DataFrame(rows)


def strict_marker_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write strict family rates and distinct item hits per 1,000 thinking tokens."""
    scored = _valid_scored(traces)
    if scored.empty:
        return pd.DataFrame(columns=list(STRICT_RATE_COLUMNS))
    rows = [
        _strict_rate_row(arm, model_id, group, subset)
        for (arm, model_id, group), subset in scored.groupby(list(RATE_KEYS), sort=False)
    ]
    return pd.DataFrame(rows)


def phrase_marker_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write phrase-only family-flag rates, ignoring bag-of-words tokens."""
    scored = _valid_scored(traces)
    if scored.empty:
        return pd.DataFrame(columns=list(RATE_COLUMNS))
    rows = [
        _rate_row(
            arm,
            model_id,
            group,
            subset,
            "phrase_uncertainty",
            "phrase_revision",
            "phrase_tension",
        )
        for (arm, model_id, group), subset in scored.groupby(list(RATE_KEYS), sort=False)
    ]
    return pd.DataFrame(rows)


def marker_item_rates(traces: pd.DataFrame) -> pd.DataFrame:
    """Write per-item presence rates for each prompt_arm, model_id, and group."""
    scored = _valid_scored(traces)
    if scored.empty:
        return pd.DataFrame(columns=list(ITEM_RATE_COLUMNS))
    rows: list[dict[str, object]] = []
    for (arm, model_id, group), subset in scored.groupby(list(RATE_KEYS), sort=False):
        rows.extend(_item_rate_rows(arm, model_id, group, subset))
    return pd.DataFrame(rows)


def group_contrasts(strict: pd.DataFrame) -> pd.DataFrame:
    """Write split minus keep and split minus remove on strict rates and density."""
    if strict.empty:
        return pd.DataFrame(columns=list(CONTRAST_COLUMNS))
    rows: list[dict[str, object]] = []
    for (arm, model_id), subset in strict.groupby(["prompt_arm", "model_id"], sort=False):
        rows.extend(_contrast_rows(str(arm), str(model_id), subset))
    return pd.DataFrame(rows)


def paired_arm_comparison(exp1: pd.DataFrame, exp2: pd.DataFrame) -> pd.DataFrame:
    """Inner-join valid traces and write experiment 2 minus experiment 1 means.

    Rows match on ``post_id`` and ``model_id``. Differences are experiment 2
    minus experiment 1 for thinking-token counts and family flags.
    """
    merged = _paired_valid(exp1, exp2)
    if merged.empty:
        return pd.DataFrame()
    rows = [
        _comparison_row(model_id, group, subset)
        for (model_id, group), subset in merged.groupby(["model_id", "group_e1"], sort=False)
    ]
    return pd.DataFrame(rows)


def _paired_valid(exp1: pd.DataFrame, exp2: pd.DataFrame) -> pd.DataFrame:
    """Inner-join scored valid rows on post_id and model_id and attach diffs."""
    left = _valid_scored(exp1)
    right = _valid_scored(exp2)
    if left.empty or right.empty:
        return pd.DataFrame()
    merged = left.merge(right, on=list(PAIR_KEYS), suffixes=(E1_SUFFIX, E2_SUFFIX))
    return _add_diffs(merged)


def _add_diffs(merged: pd.DataFrame) -> pd.DataFrame:
    """Add experiment 2 minus experiment 1 token and flag columns."""
    out = merged.copy()
    out["thinking_token_diff"] = _minus(out, "thinking_token_count")
    out["uncertainty_diff"] = _minus(out, "uncertainty")
    out["revision_diff"] = _minus(out, "revision")
    out["tension_diff"] = _minus(out, "tension")
    return out


def _minus(frame: pd.DataFrame, column: str) -> pd.Series:
    """Return experiment 2 minus experiment 1 for one numeric or boolean column."""
    return frame[column + E2_SUFFIX].astype(float) - frame[column + E1_SUFFIX].astype(float)


def _comparison_row(
    model_id: str, group: str, subset: pd.DataFrame
) -> dict[str, object]:
    return {
        "model_id": model_id,
        "group": group,
        "n_paired": int(len(subset)),
        "mean_thinking_token_diff": float(subset["thinking_token_diff"].mean()),
        "mean_uncertainty_diff": float(subset["uncertainty_diff"].mean()),
        "mean_revision_diff": float(subset["revision_diff"].mean()),
        "mean_tension_diff": float(subset["tension_diff"].mean()),
    }


def _valid_scored(traces: pd.DataFrame) -> pd.DataFrame:
    """Score valid thinking spans and attach family flags and strict counts."""
    if traces.empty or "status" not in traces.columns:
        return pd.DataFrame()
    valid = traces[traces["status"] == STATUS_VALID]
    if valid.empty:
        return pd.DataFrame()
    rows = [_row_with_flags(row) for row in valid.to_dict(orient="records")]
    return pd.DataFrame(rows)


def _row_with_flags(row: dict[str, object]) -> dict[str, object]:
    text = str(row["thinking_text"])
    detail = score_trace_detail(text)
    return {
        **row,
        "uncertainty": detail.broad.uncertainty,
        "revision": detail.broad.revision,
        "tension": detail.broad.tension,
        "strict_uncertainty": detail.strict.uncertainty,
        "strict_revision": detail.strict.revision,
        "strict_tension": detail.strict.tension,
        "phrase_uncertainty": detail.phrase.uncertainty,
        "phrase_revision": detail.phrase.revision,
        "phrase_tension": detail.phrase.tension,
        "uncertainty_hits": detail.uncertainty_hits,
        "revision_hits": detail.revision_hits,
        "tension_hits": detail.tension_hits,
        "item_hits": detail.item_hits,
    }


def _rate_row(
    arm: str,
    model_id: str,
    group: str,
    subset: pd.DataFrame,
    uncertainty_col: str,
    revision_col: str,
    tension_col: str,
) -> dict[str, object]:
    return {
        "prompt_arm": arm,
        "model_id": model_id,
        "group": group,
        "n_valid": int(len(subset)),
        "uncertainty_rate": _mean_or_nan(subset, uncertainty_col),
        "revision_rate": _mean_or_nan(subset, revision_col),
        "tension_rate": _mean_or_nan(subset, tension_col),
    }


def _strict_rate_row(
    arm: str, model_id: str, group: str, subset: pd.DataFrame
) -> dict[str, object]:
    think = subset["thinking_token_count"].astype(float).sum()
    return {
        "prompt_arm": arm,
        "model_id": model_id,
        "group": group,
        "n_valid": int(len(subset)),
        "uncertainty_rate": _mean_or_nan(subset, "strict_uncertainty"),
        "revision_rate": _mean_or_nan(subset, "strict_revision"),
        "tension_rate": _mean_or_nan(subset, "strict_tension"),
        "uncertainty_density": density_per_thousand(
            int(subset["uncertainty_hits"].sum()), int(think)
        ),
        "revision_density": density_per_thousand(
            int(subset["revision_hits"].sum()), int(think)
        ),
        "tension_density": density_per_thousand(
            int(subset["tension_hits"].sum()), int(think)
        ),
    }


def _item_rate_rows(
    arm: str, model_id: str, group: str, subset: pd.DataFrame
) -> list[dict[str, object]]:
    n_valid = int(len(subset))
    first_hits = subset["item_hits"].iloc[0]
    keys = sorted(first_hits)
    counts = {key: 0 for key in keys}
    for hits in subset["item_hits"].tolist():
        for key, present in hits.items():
            if present:
                counts[key] = counts.get(key, 0) + 1
    return [
        {
            "prompt_arm": arm,
            "model_id": model_id,
            "group": group,
            "family": family,
            "kind": kind,
            "item": item,
            "n_valid": n_valid,
            "rate": counts.get((family, kind, item), 0) / n_valid if n_valid else float("nan"),
        }
        for family, kind, item in keys
    ]


def _contrast_rows(
    arm: str, model_id: str, subset: pd.DataFrame
) -> list[dict[str, object]]:
    by_group = {str(row["group"]): row for _, row in subset.iterrows()}
    if any(group not in by_group for group in CONTRAST_GROUPS):
        return []
    rows: list[dict[str, object]] = []
    for family in FAMILIES:
        for metric in CONTRAST_METRICS:
            column = f"{family}_{metric}"
            split_value = float(by_group[GROUP_SPLIT][column])
            keep_value = float(by_group[GROUP_UNANIMOUS_KEEP][column])
            remove_value = float(by_group[GROUP_UNANIMOUS_REMOVE][column])
            rows.append(
                {
                    "prompt_arm": arm,
                    "model_id": model_id,
                    "family": family,
                    "metric": metric,
                    "split": split_value,
                    "keep": keep_value,
                    "remove": remove_value,
                    "split_minus_keep": split_value - keep_value,
                    "split_minus_remove": split_value - remove_value,
                }
            )
    return rows


def _mean_or_nan(subset: pd.DataFrame, column: str) -> float:
    if subset.empty:
        return float("nan")
    return float(subset[column].mean())
