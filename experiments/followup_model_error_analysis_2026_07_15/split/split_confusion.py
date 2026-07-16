"""Phase 1: split base_model_llm_labels.csv into TP/TN/FP/FN confusion CSVs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
PRIOR_LABELS = (
    EXPERIMENT_DIR.parent
    / "model_errors_analysis_2026_07_15"
    / "outputs"
    / "base_model_llm_labels.csv"
)
OUT_DIR = EXPERIMENT_DIR / "outputs" / "confusion_splits"

EXPECTED = {
    "tp": 2067,
    "tn": 3572,
    "fp": 2406,
    "fn": 746,
}

BUCKET_FILES = {
    "tp": "true_positives.csv",
    "tn": "true_negatives.csv",
    "fp": "false_positives.csv",
    "fn": "false_negatives.csv",
}


def _atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp_path = Path(tmp.name)
        df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def derive_predictions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["human_is_remove"] = out["label"].astype(int)
    # qwen_is_remove = label if correct else 1 - label
    correct = out["is_correct"].astype(int) == 1
    out["qwen_is_remove"] = out["human_is_remove"].where(correct, 1 - out["human_is_remove"])
    y = out["human_is_remove"]
    yhat = out["qwen_is_remove"]
    out["confusion_bucket"] = "tn"
    out.loc[(y == 1) & (yhat == 1), "confusion_bucket"] = "tp"
    out.loc[(y == 0) & (yhat == 1), "confusion_bucket"] = "fp"
    out.loc[(y == 1) & (yhat == 0), "confusion_bucket"] = "fn"
    return out


def split_and_write(labels_path: Path = PRIOR_LABELS, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(labels_path)
    df = derive_predictions(raw)

    # Store only repository-relative path
    try:
        relative_source = str(labels_path.relative_to(EXPERIMENT_DIR.parent))
    except ValueError:
        # If not under repo root, use just the name
        relative_source = labels_path.name

    summary: dict = {
        "source": relative_source,
        "n_total": len(df),
        "buckets": {},
        "sanity": {},
    }

    frames: dict[str, pd.DataFrame] = {}
    for bucket, filename in BUCKET_FILES.items():
        part = df[df["confusion_bucket"] == bucket].copy()
        part = part.sort_values("post_id").reset_index(drop=True)
        path = out_dir / filename
        _atomic_write_csv(path, part)
        frames[bucket] = part
        summary["buckets"][bucket] = {
            "rows": len(part),
            "expected": EXPECTED[bucket],
            "path": str(path.relative_to(EXPERIMENT_DIR)),
            "match_expected": len(part) == EXPECTED[bucket],
        }

    counts = {b: len(frames[b]) for b in BUCKET_FILES}
    summary["sanity"] = {
        "union_equals_total": sum(counts.values()) == len(df),
        "pairwise_disjoint": len(df) == df["post_id"].nunique()
        and sum(counts.values()) == len(df),
        "fp_plus_fn_errors": counts["fp"] + counts["fn"] == 3152,
        "tp_plus_fn_human_remove": counts["tp"] + counts["fn"] == 2813,
        "tn_plus_fp_human_keep": counts["tn"] + counts["fp"] == 5978,
        "all_expected_match": all(counts[b] == EXPECTED[b] for b in EXPECTED),
    }

    summary_path = out_dir / "split_summary.json"
    _atomic_write_text(summary_path, json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not summary["sanity"]["all_expected_match"]:
        raise SystemExit("Split counts do not match expected table.")
    return summary


def main() -> None:
    split_and_write()


if __name__ == "__main__":
    main()
