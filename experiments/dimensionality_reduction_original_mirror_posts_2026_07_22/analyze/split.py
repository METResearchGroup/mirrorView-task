"""Post-level train/test split for original+mirror long matrix (pair-safe).

Stratified on keep/remove ``label`` (not ``is_mirrored``), seed=42, train_split=0.8.
Each train/test post contributes **both** original and mirror rows.

Run from repo root::

    PYTHONPATH=. uv run python experiments/dimensionality_reduction_original_mirror_posts_2026_07_22/analyze/split.py
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
    ANALYSIS_DIR,
    ANALYSIS_META_PATH,
    ANALYSIS_TABLE_PATH,
    FEATURE_SET,
    LDA_TARGET,
    PROGRESS_UPDATES_PATH,
    SPLIT_IDS_PATH,
    SPLIT_SEED,
    STRATIFY_ON,
    TRAIN_SPLIT,
)
from analyze.split_lib import (  # noqa: E402
    assert_long_table_schema,
    expand_post_split_to_row_masks,
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
    df = df.copy()
    df["post_id"] = df["post_id"].astype(str)
    df["text_role"] = df["text_role"].astype(str)
    df["is_mirrored"] = df["is_mirrored"].astype(int)
    df["label"] = df["label"].astype(int)
    assert_long_table_schema(df)
    return df


def make_post_level_split(df: pd.DataFrame) -> dict:
    """Collapse to one row per post_id, split, expand both roles."""
    post_level = (
        df.groupby("post_id", as_index=False)
        .agg(label=("label", "first"))
        .sort_values("post_id", kind="mergesort")
        .reset_index(drop=True)
    )
    if STRATIFY_ON != "label":
        raise ValueError(f"Expected STRATIFY_ON='label'; got {STRATIFY_ON!r}")

    post_ids = post_level["post_id"].to_numpy()
    y = post_level[STRATIFY_ON].to_numpy()
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

    train_mask, test_mask = expand_post_split_to_row_masks(df, train_ids, test_ids)

    train_set = set(train_ids)
    label_rate_overall = float(post_level["label"].mean())
    label_rate_train = float(post_level.loc[post_level["post_id"].isin(train_set), "label"].mean())
    label_rate_test = float(
        post_level.loc[post_level["post_id"].isin(set(test_ids)), "label"].mean()
    )

    payload = {
        "seed": SPLIT_SEED,
        "train_split": TRAIN_SPLIT,
        "stratify_on": STRATIFY_ON,
        "feature_set": FEATURE_SET,
        "lda_target": LDA_TARGET,
        "n_posts_total": int(len(post_level)),
        "n_train": int(len(train_ids)),
        "n_test": int(len(test_ids)),
        "n_rows_train": int(train_mask.sum()),
        "n_rows_test": int(test_mask.sum()),
        "label_rate_overall": label_rate_overall,
        "label_rate_train": label_rate_train,
        "label_rate_test": label_rate_test,
        "train_post_ids": train_ids,
        "test_post_ids": test_ids,
    }

    if payload["n_rows_train"] != 2 * payload["n_train"]:
        raise AssertionError("n_rows_train != 2 * n_train")
    if payload["n_rows_test"] != 2 * payload["n_test"]:
        raise AssertionError("n_rows_test != 2 * n_test")
    if set(train_ids) & set(test_ids):
        raise AssertionError("train/test post_id overlap")

    return payload


def write_split_assignment(df: pd.DataFrame, payload: dict) -> Path:
    train_set = set(payload["train_post_ids"])
    out = df[["post_id", "text_role", "is_mirrored", "label"]].copy()
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
    print("Loading analysis frame for post-level split...")
    df = load_analysis_frame()
    n_posts = int(df["post_id"].nunique())
    print(f"  n_rows={len(df)} n_posts={n_posts}")

    payload = make_post_level_split(df)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SPLIT_IDS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assignment_path = write_split_assignment(df, payload)

    loaded = json.loads(SPLIT_IDS_PATH.read_text(encoding="utf-8"))
    assert set(loaded["train_post_ids"]) & set(loaded["test_post_ids"]) == set()
    assert set(loaded["train_post_ids"]) | set(loaded["test_post_ids"]) == set(
        df["post_id"].astype(str)
    )
    assert loaded["n_rows_train"] == 2 * loaded["n_train"]
    assert loaded["n_rows_test"] == 2 * loaded["n_test"]
    print(
        f"Disjointness OK: train∩test=∅; "
        f"n_rows_train={loaded['n_rows_train']} (==2×{loaded['n_train']}); "
        f"n_rows_test={loaded['n_rows_test']} (==2×{loaded['n_test']})"
    )

    print(
        f"Wrote {SPLIT_IDS_PATH} "
        f"n_train={payload['n_train']} n_test={payload['n_test']} "
        f"n_rows_train={payload['n_rows_train']} n_rows_test={payload['n_rows_test']} "
        f"label_train={payload['label_rate_train']:.4f} "
        f"label_test={payload['label_rate_test']:.4f}"
    )
    print(f"Wrote {assignment_path}")

    append_progress(
        [
            "## Single shared post-level train/test split",
            "",
            f"- Seed={SPLIT_SEED}, train_split={TRAIN_SPLIT}, stratify_on=`{STRATIFY_ON}`",
            f"- lda_target=`{LDA_TARGET}` (not used for split)",
            f"- Artifact: `{SPLIT_IDS_PATH}`",
            f"- n_posts_total={payload['n_posts_total']} "
            f"n_train={payload['n_train']} n_test={payload['n_test']}",
            f"- n_rows_train={payload['n_rows_train']} n_rows_test={payload['n_rows_test']} "
            f"(exactly 2× post counts)",
            "- Disjoint: train ∩ test post_ids = ∅; each post contributes both roles to one split",
            f"- Convenience join: `{assignment_path}`",
            "- Downstream agents must load these IDs; do **not** re-split.",
            "",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
