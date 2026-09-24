"""Union cohort GEPA train/val loaders for rebuilt optimization.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.splits import load_gepa_union_splits; print(len(load_gepa_union_splits()[0]))"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevDataInst
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab import dev_ab_split_path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET


def _row_to_jev_data_inst(row: object) -> JevDataInst:
    remove_share = float(row.remove_share)
    return JevDataInst(
        post_id=str(row.post_id),
        original_text=str(row.original_text),
        mirror_text=str(row.mirror_text),
        post_1_role=str(row.post_1_role),
        post_2_role=str(row.post_2_role),
        label=int(row.label),
        n_keep=int(row.n_keep),
        n_remove=int(row.n_remove),
        n_raters=int(row.n_raters),
        remove_share=remove_share,
        sampled_stance=str(row.sampled_stance),
        sample_toxicity_type=str(row.sample_toxicity_type),
    )


def load_gepa_union_splits() -> tuple[list[JevDataInst], list[JevDataInst]]:
    """Load train and val from COHORT_UNION_PARQUET gepa_subset train|val; map remove_share."""
    parquet_path = _REPO_ROOT / COHORT_UNION_PARQUET
    if not parquet_path.is_file():
        raise FileNotFoundError(f"union cohort parquet missing at {parquet_path}")
    frame = pd.read_parquet(parquet_path)
    trainset = [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["gepa_subset"].eq("train")].itertuples()
    ]
    valset = [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["gepa_subset"].eq("val")].itertuples()
    ]
    return trainset, valset


def _load_dev_frame(parquet_path: Path | None = None) -> list[JevDataInst]:
    path = parquet_path or (_REPO_ROOT / COHORT_UNION_PARQUET)
    if not path.is_file():
        raise FileNotFoundError(f"union cohort parquet missing at {path}")
    frame = pd.read_parquet(path)
    return [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["split"].eq("dev")].itertuples()
    ]


def load_dev_instances(*, split: Literal["dev_a", "dev_b", "dev"]) -> list[JevDataInst]:
    """Map post_id via dev_ab_split.json; full dev if split=='dev'."""
    dev_instances = _load_dev_frame()
    if split == "dev":
        return dev_instances
    sidecar = json.loads(dev_ab_split_path().read_text(encoding="utf-8"))
    id_key = "dev_a_ids" if split == "dev_a" else "dev_b_ids"
    allowed = {str(post_id) for post_id in sidecar[id_key]}
    return [instance for instance in dev_instances if instance.post_id in allowed]


def load_train_post_texts(parquet_path: Path | None = None) -> list[str]:
    """Collect original and mirror train texts for memorization guards."""
    path = parquet_path or (_REPO_ROOT / COHORT_UNION_PARQUET)
    frame = pd.read_parquet(path)
    train_frame = frame.loc[frame["gepa_subset"].eq("train")]
    texts: list[str] = []
    for row in train_frame.itertuples():
        texts.append(str(row.original_text))
        texts.append(str(row.mirror_text))
    return texts
