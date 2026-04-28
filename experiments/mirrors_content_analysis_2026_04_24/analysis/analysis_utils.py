"""Shared helpers for mirrors content analysis modules."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

# Display / axis ordering. Condition keys are normalized with lower-case and "-" -> "_".
PARTY_ORDER = ["democrat", "republican"]
CONDITION_ORDER = ["control", "training", "training_assisted"]
CONDITION_DISPLAY_MAP = {
    "control": "control",
    "training": "training",
    "training_assisted": "training-assisted",
}

PARTY_MARGINAL_HEADER = "Party marginal"
CONDITION_MARGINAL_ROW = "Condition marginal"
PARTY_CONDITION_TABLE_CAPTION = (
    "[dim]Cells: party×condition means. Row margin: party pooled. "
    "Footer: condition pooled. Lower-right: overall mean (partition key all).[/dim]"
)

ID_COLUMNS = [
    "prolific_id",
    "post_id",
    "party_group",
    "decision",
    "evaluation_mode",
    "phase",
    "condition",
]

WORD_RE = re.compile(r"\b\w+\b")
PUNCTUATION_RE = re.compile(r"[^\w\s]")
SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value)


def normalize_party(value: Any) -> str:
    t = str(value or "").strip().lower()
    return t if t else ""


def normalize_condition(value: Any) -> str:
    t = str(value or "").strip().lower().replace("-", "_")
    return t if t else ""


def coerce_phase(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        return float(int(float(str(value).strip())))
    except (TypeError, ValueError):
        return None


def rows_both_posts_shown(df: pd.DataFrame) -> pd.Series:
    """True when the trial shows original + mirror per study design."""
    em = df["evaluation_mode"].fillna("").astype(str).str.strip().str.lower()
    return em.isin(["linked_fate", "assisted"])
