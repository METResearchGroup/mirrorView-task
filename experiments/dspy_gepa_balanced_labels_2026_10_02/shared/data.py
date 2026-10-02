"""Draw a 405-post cohort with 203 keep posts and 202 remove posts.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step1_setup/main.py
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.config import (
    COHORT_KEEP_COUNT,
    COHORT_REMOVE_COUNT,
    COHORT_ROW_COUNT,
    RANDOM_SEED,
    SPLIT_KEEP_COUNTS,
    SPLIT_NAMES,
    SPLIT_REMOVE_COUNTS,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import KEEP_LABEL, REMOVE_LABEL
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import (
    EXCLUDELIST_POST_IDS,
    eligible_rows,
    load_unanimous_labels,
)

SAMPLING_METHOD = "balanced_class_stance_sha256_rank"


@dataclass(frozen=True)
class BalancedBundle:
    """The balanced cohort and its four disjoint splits."""

    eligible_count: int
    cohort_ids: tuple[str, ...]
    splits: dict[str, pd.DataFrame]


def build_balanced_splits() -> BalancedBundle:
    """Return the 405-post balanced cohort from the unanimous eligible pool."""
    eligible = eligible_rows(load_unanimous_labels())
    pools = _pools(eligible)
    splits = {name: [] for name in SPLIT_NAMES}
    for name in SPLIT_NAMES:
        splits[name].extend(_take(pools, KEEP_LABEL, SPLIT_KEEP_COUNTS[name]))
        splits[name].extend(_take(pools, REMOVE_LABEL, SPLIT_REMOVE_COUNTS[name]))
    frames = {name: _sorted_unique(pd.DataFrame(rows)) for name, rows in splits.items()}
    _require_bundle(frames, set(EXCLUDELIST_POST_IDS))
    cohort_ids = tuple(sorted(post_id for frame in frames.values() for post_id in frame["post_id"].astype(str)))
    return BalancedBundle(len(eligible), cohort_ids, frames)


def _pools(frame: pd.DataFrame) -> dict[int, dict[str, list[dict[str, object]]]]:
    grouped: dict[int, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for row in frame.to_dict(orient="records"):
        grouped[int(row["keep_remove_label"])][str(row["sampled_stance"])].append(row)
    for label_rows in grouped.values():
        for stance, rows in label_rows.items():
            label_rows[stance] = sorted(rows, key=lambda item: _rank(str(item["post_id"])))
    return grouped


def _take(
    pools: dict[int, dict[str, list[dict[str, object]]]],
    label: int,
    target: int,
) -> list[dict[str, object]]:
    stance_rows = pools.setdefault(label, {})
    available = {stance: rows for stance, rows in stance_rows.items() if rows}
    quotas = _largest_remainder({stance: len(rows) for stance, rows in available.items()}, target)
    chosen: list[dict[str, object]] = []
    for stance in sorted(quotas):
        quota = quotas[stance]
        rows = stance_rows[stance]
        if quota > len(rows):
            raise ValueError(f"quota {quota} exceeds {stance} rows for label {label}")
        chosen.extend(rows[:quota])
        stance_rows[stance] = rows[quota:]
    if len(chosen) != target:
        raise ValueError(f"selected {len(chosen)} rows for label {label}, expected {target}")
    return chosen


def _largest_remainder(counts: dict[str, int], target: int) -> dict[str, int]:
    population = sum(counts.values())
    if target < 0 or target > population:
        raise ValueError(f"cannot allocate {target} from {population}")
    raw = {key: target * value / population for key, value in counts.items()}
    floors = {key: math.floor(value) for key, value in raw.items()}
    leftover = target - sum(floors.values())
    order = sorted(counts, key=lambda key: (-(raw[key] - floors[key]), key))
    for key in order[:leftover]:
        floors[key] += 1
    return floors


def _rank(post_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{RANDOM_SEED}:{post_id}".encode()).hexdigest()
    return digest, post_id


def _sorted_unique(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame.copy()
    rows["post_id"] = rows["post_id"].astype(str)
    if rows["post_id"].duplicated().any():
        raise ValueError("post ids repeat inside a split")
    return rows.sort_values("post_id", kind="mergesort").reset_index(drop=True)


def _require_bundle(frames: dict[str, pd.DataFrame], excluded: set[str]) -> None:
    seen: set[str] = set()
    keep_total = 0
    remove_total = 0
    for name in SPLIT_NAMES:
        frame = frames[name]
        ids = set(frame["post_id"].astype(str))
        if seen & ids or ids & excluded:
            raise ValueError(f"{name} overlaps another split or an excluded prompt example")
        labels = frame["keep_remove_label"].astype(int)
        keep_count = int(labels.eq(KEEP_LABEL).sum())
        remove_count = int(labels.eq(REMOVE_LABEL).sum())
        if keep_count != SPLIT_KEEP_COUNTS[name] or remove_count != SPLIT_REMOVE_COUNTS[name]:
            raise ValueError(f"{name} class counts were {keep_count} keep and {remove_count} remove")
        if len(frame) != keep_count + remove_count:
            raise ValueError(f"{name} row count does not match its class counts")
        seen |= ids
        keep_total += keep_count
        remove_total += remove_count
    if len(seen) != COHORT_ROW_COUNT or keep_total != COHORT_KEEP_COUNT or remove_total != COHORT_REMOVE_COUNT:
        raise ValueError(f"cohort totals were {len(seen)} posts, {keep_total} keep, {remove_total} remove")
