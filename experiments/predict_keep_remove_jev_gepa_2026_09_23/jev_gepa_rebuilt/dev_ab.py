"""Stratified dev-A / dev-B split sidecar for rebuilt GEPA selection.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab import build_or_load_dev_ab_split; print(build_or_load_dev_ab_split(write=False)['n_dev_a'])"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
from sklearn.model_selection import train_test_split

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.artifacts import upload_rebuilt
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEV_AB_SPLIT_RELATIVE,
    EXPERIMENT_ROOT,
    GEPA_SEED,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET


def dev_ab_split_path() -> Path:
    """experiments/predict_keep_remove_jev_gepa_2026_09_23/data/dev_ab_split.json"""
    return _REPO_ROOT / EXPERIMENT_ROOT / DEV_AB_SPLIT_RELATIVE


def _read_split_file(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def build_or_load_dev_ab_split(
    *,
    parquet_path: Path = COHORT_UNION_PARQUET,
    seed: int = GEPA_SEED,
    write: bool = True,
) -> dict[str, object]:
    """Stratified 50/50 split of dev post_ids into dev_a_ids and dev_b_ids.

    Persist JSON: {seed, dev_a_ids, dev_b_ids, n_dev_a, n_dev_b}.
    Call upload_rebuilt(dev_ab_split_path()) after write.
    """
    sidecar_path = dev_ab_split_path()
    if sidecar_path.is_file():
        existing = _read_split_file(sidecar_path)
        if int(existing.get("seed", -1)) == seed:
            return existing

    resolved_parquet = parquet_path
    if not resolved_parquet.is_absolute():
        resolved_parquet = _REPO_ROOT / resolved_parquet
    frame = pd.read_parquet(resolved_parquet)
    dev_frame = frame.loc[frame["split"].eq("dev")].copy()
    if dev_frame.empty:
        raise ValueError("no dev rows in cohort parquet")

    dev_ids = dev_frame["post_id"].astype(str).tolist()
    labels = dev_frame["label"].astype(int).tolist()
    dev_a_ids, dev_b_ids = train_test_split(
        dev_ids,
        test_size=0.5,
        random_state=seed,
        stratify=labels,
    )
    payload: dict[str, object] = {
        "seed": seed,
        "dev_a_ids": [str(post_id) for post_id in dev_a_ids],
        "dev_b_ids": [str(post_id) for post_id in dev_b_ids],
        "n_dev_a": len(dev_a_ids),
        "n_dev_b": len(dev_b_ids),
    }

    if write:
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        upload_rebuilt(sidecar_path)

    return payload
