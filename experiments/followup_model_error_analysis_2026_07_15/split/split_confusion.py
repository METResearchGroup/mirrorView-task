"""Phase 1: split base_model_llm_labels.csv into TP/TN/FP/FN confusion CSVs."""

from __future__ import annotations

import json
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

    summary: dict = {
        "source": str(labels_path),
        "n_total": int(len(df)),
        "buckets": {},
        "sanity": {},
    }

    frames: dict[str, pd.DataFrame] = {}
    for bucket, filename in BUCKET_FILES.items():
        part = df[df["confusion_bucket"] == bucket].copy()
        part = part.sort_values("post_id").reset_index(drop=True)
        path = out_dir / filename
        part.to_csv(path, index=False)
        frames[bucket] = part
        summary["buckets"][bucket] = {
            "rows": int(len(part)),
            "expected": EXPECTED[bucket],
            "path": str(path.relative_to(EXPERIMENT_DIR)),
            "match_expected": int(len(part)) == EXPECTED[bucket],
        }

    counts = {b: int(len(frames[b])) for b in BUCKET_FILES}
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
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not summary["sanity"]["all_expected_match"]:
        raise SystemExit("Split counts do not match expected table.")
    return summary


def main() -> None:
    split_and_write()


if __name__ == "__main__":
    main()
