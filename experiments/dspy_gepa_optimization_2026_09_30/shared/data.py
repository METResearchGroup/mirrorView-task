"""Deterministic Study 2 splits for the DSPy GEPA pilot.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    COHORT_ROW_COUNT,
    DEVELOPMENT_SPLIT,
    ELIGIBLE_KEEP_COUNT,
    ELIGIBLE_REMOVE_COUNT,
    ELIGIBLE_ROW_COUNT,
    FIVE_LABELER_COUNT,
    GEPA_VALIDATION_SPLIT,
    KEEP_LABEL,
    OPTIMIZATION_SPLIT,
    RANDOM_SEED,
    REMOVE_LABEL,
    SOURCE_KEEP_COUNT,
    SOURCE_REMOVE_COUNT,
    SOURCE_ROW_COUNT,
    SPLIT_NAMES,
    SPLIT_REMOVE_COUNTS,
    SPLIT_ROW_COUNTS,
    TEST_SPLIT,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import prompt_demonstrations
from shared.data import dataloader
from shared.data.registry import STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, resolve_path

SAMPLING_METHOD = "stratified_largest_remainder_sha256_rank"
WHITESPACE = re.compile(r"\s+")
SHARED_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "keep_remove_label",
    "n_keep",
    "n_remove",
    "n_raters",
    "is_unanimous",
    "sampled_stance",
)

# Resolved once from the issue 329 examples against STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS.
EXCLUDELIST_POST_IDS = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e2b250b7296b6665553ddf1e062f4c9f74fa6d2022a67e57bdcb02ede10f4c6",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_212203f919beea6f275a586800b1bffdd67acbe9e44f93f7a631c7137faa8496",
    "bluesky_23995952a65f0f11e719fed6a7f1a1900726fd9309800ebe5ac6705d5eb5b703",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_0098e567eb615260f97de8b6d3947c76c6df50ead87157db1c510f471f6ced27",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00aa79b92bef053dd31160dee2b6c7c3e955761c8f93e2fc9d3995a9c9385744",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)


@dataclass(frozen=True)
class SplitBundle:
    """Ordered pilot splits and the rows they were drawn from."""

    source_count: int
    eligible: pd.DataFrame
    cohort_ids: tuple[str, ...]
    splits: dict[str, pd.DataFrame]


def load_unanimous_labels() -> pd.DataFrame:
    """Load the registered unanimous Study 2 labels."""
    frame = dataloader.load_dataset(STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, low_memory=False)
    return frame.loc[:, list(SHARED_COLUMNS)].copy()


def validate_source(frame: pd.DataFrame) -> pd.DataFrame:
    """Return source rows after the unanimous five-labeler checks.

    Raises
    ------
    ValueError
        When a count or agreement check differs from the pinned contract.
    """
    rows = _sorted_unique(frame)
    _require_count(len(rows), SOURCE_ROW_COUNT, "source rows")
    _require_label_counts(rows, SOURCE_KEEP_COUNT, SOURCE_REMOVE_COUNT, "source")
    _require_unanimous(rows)
    return rows


def eligible_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Return source rows that are not prompt examples."""
    source = validate_source(frame)
    excluded = set(EXCLUDELIST_POST_IDS)
    _require_exclusion_ids(source, excluded)
    eligible = source.loc[~source["post_id"].isin(excluded)].reset_index(drop=True)
    _require_count(len(eligible), ELIGIBLE_ROW_COUNT, "eligible rows")
    _require_label_counts(eligible, ELIGIBLE_KEEP_COUNT, ELIGIBLE_REMOVE_COUNT, "eligible")
    return eligible


def build_splits(frame: pd.DataFrame) -> SplitBundle:
    """Select the pilot cohort and four disjoint splits."""
    eligible = eligible_rows(frame)
    cohort = _select_cohort(eligible)
    splits = _split_cohort(cohort)
    _require_disjoint(splits, set(EXCLUDELIST_POST_IDS))
    return SplitBundle(len(frame), eligible, _ids(cohort), splits)


def normalized_text(value: object) -> str:
    """Collapse whitespace and casefold text for example matching."""
    return WHITESPACE.sub(" ", str(value).replace("\u00a0", " ")).strip().casefold()


def source_dataset_name() -> str:
    """Return the registry name of the unanimous labels."""
    return STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS


def source_dataset_path() -> str:
    """Return the registry path of the unanimous labels."""
    return resolve_path(STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS).as_posix()


def _select_cohort(eligible: pd.DataFrame) -> pd.DataFrame:
    keep_target = COHORT_ROW_COUNT - sum(SPLIT_REMOVE_COUNTS.values())
    remove_target = sum(SPLIT_REMOVE_COUNTS.values())
    chosen = _take_label(eligible, KEEP_LABEL, keep_target) + _take_label(eligible, REMOVE_LABEL, remove_target)
    cohort = pd.DataFrame(chosen)
    _require_count(len(cohort), COHORT_ROW_COUNT, "cohort rows")
    return _sorted_unique(cohort)


def _split_cohort(cohort: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pools = _pools(cohort)
    splits: dict[str, list[dict[str, object]]] = {name: [] for name in SPLIT_NAMES}
    for name in SPLIT_NAMES:
        keep_target = SPLIT_ROW_COUNTS[name] - SPLIT_REMOVE_COUNTS[name]
        splits[name].extend(_take_from_pools(pools, KEEP_LABEL, keep_target))
        splits[name].extend(_take_from_pools(pools, REMOVE_LABEL, SPLIT_REMOVE_COUNTS[name]))
    return {name: _sorted_unique(pd.DataFrame(rows)) for name, rows in splits.items()}


def _take_label(frame: pd.DataFrame, label: int, target: int) -> list[dict[str, object]]:
    pools = _pools(frame.loc[frame["keep_remove_label"] == label])
    return _take_from_pools({label: pools.get(label, {})}, label, target)


def _take_from_pools(
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


def _pools(frame: pd.DataFrame) -> dict[int, dict[str, list[dict[str, object]]]]:
    grouped: dict[int, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for row in frame.to_dict(orient="records"):
        label = int(row["keep_remove_label"])
        grouped[label][str(row["sampled_stance"])].append(row)
    for label_rows in grouped.values():
        for stance, rows in label_rows.items():
            label_rows[stance] = sorted(rows, key=lambda item: _rank(str(item["post_id"])))
    return grouped


def _largest_remainder(counts: dict[str, int], target: int) -> dict[str, int]:
    population = sum(counts.values())
    if target < 0 or target > population:
        raise ValueError(f"cannot allocate {target} from {population}")
    if population == 0:
        return {}
    raw = {key: target * value / population for key, value in counts.items()}
    floors = {key: math.floor(value) for key, value in raw.items()}
    leftover = target - sum(floors.values())
    order = sorted(counts, key=lambda key: (-(raw[key] - floors[key]), key))
    for key in order[:leftover]:
        floors[key] += 1
    return floors


def post_rank(post_id: str) -> tuple[str, str]:
    """Return the deterministic rank key for a post id."""
    return _rank(post_id)


def _rank(post_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{RANDOM_SEED}:{post_id}".encode()).hexdigest()
    return digest, post_id


def _sorted_unique(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame.copy()
    rows["post_id"] = rows["post_id"].astype(str)
    if rows["post_id"].duplicated().any() or rows["post_id"].eq("").any():
        raise ValueError("post_id values must be unique and nonempty")
    return rows.sort_values("post_id", kind="mergesort").reset_index(drop=True)


def _require_unanimous(frame: pd.DataFrame) -> None:
    raters = frame["n_raters"].astype(int)
    keep = frame["n_keep"].astype(int)
    remove = frame["n_remove"].astype(int)
    if not raters.eq(FIVE_LABELER_COUNT).all() or not (keep + remove).eq(FIVE_LABELER_COUNT).all():
        raise ValueError("every source row must have five agreeing labelers")
    if not remove.isin([0, FIVE_LABELER_COUNT]).all():
        raise ValueError("unanimous rows must have 0 or 5 remove votes")
    expected = remove.eq(FIVE_LABELER_COUNT).astype(int)
    if not frame["keep_remove_label"].astype(int).eq(expected).all():
        raise ValueError("keep_remove_label disagrees with the remove votes")


def _require_label_counts(frame: pd.DataFrame, keep_count: int, remove_count: int, name: str) -> None:
    labels = frame["keep_remove_label"].astype(int)
    observed_keep = int(labels.eq(KEEP_LABEL).sum())
    observed_remove = int(labels.eq(REMOVE_LABEL).sum())
    if observed_keep != keep_count or observed_remove != remove_count:
        raise ValueError(
            f"{name} keep/remove counts were {observed_keep}/{observed_remove}, "
            f"expected {keep_count}/{remove_count}"
        )


def _require_count(observed: int, expected: int, name: str) -> None:
    if observed != expected:
        raise ValueError(f"{name} were {observed}, expected {expected}")


def _require_exclusion_ids(frame: pd.DataFrame, excluded: set[str]) -> None:
    if len(excluded) != len(EXCLUDELIST_POST_IDS):
        raise ValueError("exclusion ids must be unique")
    present = set(frame["post_id"].astype(str))
    missing = sorted(excluded - present)
    if missing:
        raise ValueError(f"exclusion ids missing from the source data: {missing}")


def _require_disjoint(splits: dict[str, pd.DataFrame], excluded: set[str]) -> None:
    seen: set[str] = set()
    for name in SPLIT_NAMES:
        ids = set(_ids(splits[name]))
        if seen & ids or ids & excluded:
            raise ValueError(f"{name} overlaps another split or an excluded id")
        _require_count(len(ids), SPLIT_ROW_COUNTS[name], f"{name} rows")
        labels = splits[name]["keep_remove_label"].astype(int)
        remove_count = int(labels.eq(REMOVE_LABEL).sum())
        if remove_count != SPLIT_REMOVE_COUNTS[name]:
            raise ValueError(f"{name} remove count was {remove_count}")
        seen |= ids


def _ids(frame: pd.DataFrame) -> tuple[str, ...]:
    return tuple(frame["post_id"].astype(str))


def example_match_keys() -> list[tuple[str, str]]:
    """Return normalized post texts for each prompt example."""
    return [
        (normalized_text(row.post_1_text), normalized_text(row.post_2_text))
        for row in prompt_demonstrations()
    ]
