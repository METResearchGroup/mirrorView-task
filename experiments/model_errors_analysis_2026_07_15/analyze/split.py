"""Single shared post-level train/test split for linear separator / 2D reduction.

Stratified on ``is_error``, seed=42, train_split=0.8.
Writes ``outputs/analysis/split_ids.json`` and a convenience join table.

Run from repo root::

    PYTHONPATH=. uv run python experiments/model_errors_analysis_2026_07_15/analyze/split.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

_EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _EXPERIMENT_ROOT.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENT_ROOT))

from analyze.paths import (  # noqa: E402
    ANALYSIS_META_PATH,
    ANALYSIS_TABLE_PATH,
    FEATURE_SET,
    PRIMARY_CLASSIFIER_ID,
    PROGRESS_UPDATES_PATH,
    SPLIT_IDS_PATH,
    SPLIT_SEED,
    STRATIFY_ON,
    TRAIN_SPLIT,
    ANALYSIS_DIR,
)


def load_analysis_frame() -> pd.DataFrame:
    if ANALYSIS_TABLE_PATH.is_file():
        df = pd.read_parquet(ANALYSIS_TABLE_PATH)
    elif ANALYSIS_META_PATH.is_file():
        df = pd.read_csv(ANALYSIS_META_PATH)
    else:
        raise FileNotFoundError(
            f"Missing analysis table. Run build_table.py first "
            f"(expected {ANALYSIS_TABLE_PATH} or {ANALYSIS_META_PATH})."
        )
    required = {"post_id", "is_error", "is_correct", "label"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"analysis table missing columns: {sorted(missing)}")
    df = df.copy()
    df["post_id"] = df["post_id"].astype(str)
    df["is_error"] = df["is_error"].astype(int)
    if df["post_id"].duplicated().any():
        raise ValueError("Duplicate post_id in analysis table")
    return df


def make_split(df: pd.DataFrame) -> dict:
    post_ids = df["post_id"].to_numpy()
    y = df[STRATIFY_ON].to_numpy()
    train_ids, test_ids = train_test_split(
        post_ids,
        test_size=1.0 - TRAIN_SPLIT,
        train_size=TRAIN_SPLIT,
        random_state=SPLIT_SEED,
        stratify=y,
        shuffle=True,
    )
    train_ids = [str(x) for x in train_ids.tolist()]
    test_ids = [str(x) for x in test_ids.tolist()]

    train_set = set(train_ids)
    test_set = set(test_ids)
    all_ids = set(df["post_id"].astype(str))

    if train_set & test_set:
        raise AssertionError("train/test post_id overlap")
    if train_set | test_set != all_ids:
        missing = all_ids - (train_set | test_set)
        extra = (train_set | test_set) - all_ids
        raise AssertionError(f"split coverage failure missing={len(missing)} extra={len(extra)}")
    if len(train_ids) != len(train_set) or len(test_ids) != len(test_set):
        raise AssertionError("duplicate IDs within a split list")

    # Stratification sanity: rates should be close.
    train_err = float(df.loc[df["post_id"].isin(train_set), "is_error"].mean())
    test_err = float(df.loc[df["post_id"].isin(test_set), "is_error"].mean())
    overall_err = float(df["is_error"].mean())

    payload = {
        "seed": SPLIT_SEED,
        "train_split": TRAIN_SPLIT,
        "stratify_on": STRATIFY_ON,
        "classifier_id": PRIMARY_CLASSIFIER_ID,
        "feature_set": FEATURE_SET,
        "n_total": int(len(df)),
        "n_train": int(len(train_ids)),
        "n_test": int(len(test_ids)),
        "is_error_rate_overall": overall_err,
        "is_error_rate_train": train_err,
        "is_error_rate_test": test_err,
        "train_post_ids": train_ids,
        "test_post_ids": test_ids,
    }
    return payload


def write_split_assignment(df: pd.DataFrame, payload: dict) -> Path:
    """Write meta + split column for downstream convenience (no re-split needed)."""
    train_set = set(payload["train_post_ids"])
    out = df[["post_id", "label", "is_correct", "is_error"]].copy()
    out["split"] = np.where(out["post_id"].isin(train_set), "train", "test")
    path = ANALYSIS_DIR / "analysis_with_split.csv"
    out.to_csv(path, index=False)
    return path


def append_progress(lines: list[str]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if PROGRESS_UPDATES_PATH.is_file():
        existing = PROGRESS_UPDATES_PATH.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    PROGRESS_UPDATES_PATH.write_text(existing + block, encoding="utf-8")


def main() -> int:
    print(f"Loading analysis frame for split...")
    df = load_analysis_frame()
    print(f"  rows={len(df)}")

    payload = make_split(df)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SPLIT_IDS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assignment_path = write_split_assignment(df, payload)

    # Verify load round-trip
    loaded = json.loads(SPLIT_IDS_PATH.read_text(encoding="utf-8"))
    assert set(loaded["train_post_ids"]) & set(loaded["test_post_ids"]) == set()
    assert set(loaded["train_post_ids"]) | set(loaded["test_post_ids"]) == set(df["post_id"])

    print(
        f"Wrote {SPLIT_IDS_PATH} "
        f"n_train={payload['n_train']} n_test={payload['n_test']} "
        f"err_train={payload['is_error_rate_train']:.4f} "
        f"err_test={payload['is_error_rate_test']:.4f}"
    )
    print(f"Wrote {assignment_path}")

    append_progress(
        [
            "## Single shared train/test split",
            "",
            f"- Seed={SPLIT_SEED}, train_split={TRAIN_SPLIT}, stratify_on=`{STRATIFY_ON}`",
            f"- Artifact: `{SPLIT_IDS_PATH}`",
            f"- n_total={payload['n_total']} n_train={payload['n_train']} n_test={payload['n_test']}",
            f"- Disjoint: train ∩ test = ∅; union covers analysis set",
            f"- is_error rates: overall={payload['is_error_rate_overall']:.4f}, "
            f"train={payload['is_error_rate_train']:.4f}, test={payload['is_error_rate_test']:.4f}",
            f"- Convenience join: `{assignment_path}` "
            f"(columns `post_id,label,is_correct,is_error,split`)",
            "- Downstream agents must load these IDs; do **not** re-split.",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
