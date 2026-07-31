"""Load Study 2 posts, sample without replacement, form unique-id batches."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader

EXPERIMENT_ROOT = Path(__file__).resolve().parent


def load_posts() -> pd.DataFrame:
    """Return one row per post with modal human keep/remove labels."""
    return Dataloader().load_training_dataframe()


def _normalize_message_ids(raw: Any) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, (set, list, tuple)):
        return {str(x) for x in raw}
    raise TypeError(f"exclude_ids must be a set/list/tuple, got {type(raw)!r}")


def load_exclude_ids(path: str | Path | None) -> set[str]:
    """Load message ids to exclude from a prior metadata.json or a JSON list file."""
    if path is None:
        return set()
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {str(x) for x in data}
    if isinstance(data, dict):
        run_meta = data.get("run_metadata", data)
        ids = run_meta.get("message_ids")
        if ids is None:
            raise KeyError(
                f"No message_ids found in {p}. Expected a JSON list or metadata "
                "with run_metadata.message_ids."
            )
        return {str(x) for x in ids}
    raise TypeError(f"Unsupported exclude-ids JSON type in {p}: {type(data)!r}")


def sample_posts(
    df: pd.DataFrame,
    *,
    fraction: float,
    seed: int,
    exclude_ids: set[str] | list[str] | None = None,
) -> pd.DataFrame:
    """Stratified sample without replacement by decision label.

    Each non-empty class is sampled at ``fraction`` of its available rows
    (after exclusions). Uses ``math.ceil`` so tiny fractions still yield at
    least one row per non-empty class.
    """
    if not (0.0 < fraction <= 1.0):
        raise ValueError(f"fraction must be in (0, 1], got {fraction!r}")

    exclude = _normalize_message_ids(exclude_ids)
    work = df.copy()
    work["message_id"] = work["message_id"].astype(str)
    if exclude:
        work = work[~work["message_id"].isin(exclude)].copy()

    if work.empty:
        raise ValueError("No posts left after applying exclude_ids.")

    parts: list[pd.DataFrame] = []
    rng = seed
    for decision, group in work.groupby("decision", sort=True):
        n = max(1, math.ceil(len(group) * fraction)) if fraction < 1.0 else len(group)
        n = min(n, len(group))
        # Distinct per-class seed derived from the base seed for stability.
        class_seed = rng + (0 if decision == "keep" else 1_000_003)
        parts.append(group.sample(n=n, random_state=class_seed, replace=False))

    out = pd.concat(parts, ignore_index=True)
    # Deterministic row order for downstream batching.
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def form_batches(
    sample: pd.DataFrame,
    *,
    keep_per_batch: int = 10,
    remove_per_batch: int = 10,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    """Form mixed keep/remove batches with unique message_ids across batches.

    Returns ``(batches, leftover_rows)``. Each batch dict has:
    ``batch_id``, ``keep_posts``, ``remove_posts``, ``message_ids``.
    """
    if keep_per_batch < 1 or remove_per_batch < 1:
        raise ValueError("keep_per_batch and remove_per_batch must be >= 1")

    keep = sample[sample["decision"] == "keep"].reset_index(drop=True)
    remove = sample[sample["decision"] == "remove"].reset_index(drop=True)

    n_batches = min(len(keep) // keep_per_batch, len(remove) // remove_per_batch)
    if n_batches < 1:
        raise ValueError(
            "Cannot form any full batches from sample: "
            f"keep={len(keep)} (need {keep_per_batch}/batch), "
            f"remove={len(remove)} (need {remove_per_batch}/batch)."
        )

    batches: list[dict[str, Any]] = []
    keep_cursor = 0
    remove_cursor = 0
    for batch_id in range(n_batches):
        keep_chunk = keep.iloc[keep_cursor : keep_cursor + keep_per_batch]
        remove_chunk = remove.iloc[remove_cursor : remove_cursor + remove_per_batch]
        keep_cursor += keep_per_batch
        remove_cursor += remove_per_batch
        keep_posts = keep_chunk.to_dict(orient="records")
        remove_posts = remove_chunk.to_dict(orient="records")
        message_ids = [str(r["message_id"]) for r in keep_posts + remove_posts]
        batches.append(
            {
                "batch_id": batch_id,
                "keep_posts": keep_posts,
                "remove_posts": remove_posts,
                "message_ids": message_ids,
            }
        )

    leftover = pd.concat(
        [keep.iloc[keep_cursor:], remove.iloc[remove_cursor:]],
        ignore_index=True,
    )
    _assert_unique_message_ids(batches)
    return batches, leftover


def _assert_unique_message_ids(batches: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for batch in batches:
        for mid in batch["message_ids"]:
            mid_s = str(mid)
            if mid_s in seen:
                raise ValueError(f"Duplicate message_id across batches: {mid_s}")
            seen.add(mid_s)


def all_message_ids(batches: list[dict[str, Any]]) -> list[str]:
    """Flat unique message ids in batch order."""
    ids: list[str] = []
    seen: set[str] = set()
    for batch in batches:
        for mid in batch["message_ids"]:
            mid_s = str(mid)
            if mid_s not in seen:
                seen.add(mid_s)
                ids.append(mid_s)
    return ids


if __name__ == "__main__":
    df = load_posts()
    sample = sample_posts(df, fraction=0.01, seed=42)
    batches, leftover = form_batches(sample)
    print(
        f"posts={len(df)} sample={len(sample)} "
        f"batches={len(batches)} leftover={len(leftover)}"
    )
