from __future__ import annotations

"""
Compare average character lengths between old/new MirrorView flip datasets.

Run from repo root:

PYTHONPATH=. uv run python jobs/mirrorview_scaled_2026_06_18/compare_avg_char_lengths.py
"""

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

OLD_CSV = HERE / "old_flips.csv"
FULL_NEW_CSV = HERE / "full_new_flips.csv"
NEW_CSV = HERE / "flips.csv"

REQUIRED_BASE_COLS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
]


def _avg_chars(series: pd.Series) -> float:
    return float(series.fillna("").astype(str).map(len).mean())


def _summarize_mirrored_text(path: Path) -> dict[str, object]:
    df = pd.read_csv(path)
    required = REQUIRED_BASE_COLS + ["mirrored_text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {path}: {missing}")

    return {
        "path": str(path),
        "rows": int(len(df)),
        "unique_post_primary_key": int(df["post_primary_key"].astype(str).nunique()),
        "avg_original_chars": _avg_chars(df["original_text"]),
        "avg_mirrored_chars": _avg_chars(df["mirrored_text"]),
    }

def _summarize_full_new(path: Path) -> dict[str, object]:
    df = pd.read_csv(path)
    required = REQUIRED_BASE_COLS + ["raw_mirrored_text", "processed_mirrored_text"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {path}: {missing}")

    return {
        "path": str(path),
        "rows": int(len(df)),
        "unique_post_primary_key": int(df["post_primary_key"].astype(str).nunique()),
        "avg_original_chars": _avg_chars(df["original_text"]),
        "avg_raw_mirrored_chars": _avg_chars(df["raw_mirrored_text"]),
        "avg_processed_mirrored_chars": _avg_chars(df["processed_mirrored_text"]),
    }


def main() -> None:
    if not OLD_CSV.exists():
        raise FileNotFoundError(f"Missing {OLD_CSV}")
    if not FULL_NEW_CSV.exists():
        raise FileNotFoundError(f"Missing {FULL_NEW_CSV}")
    if not NEW_CSV.exists():
        raise FileNotFoundError(f"Missing {NEW_CSV}")

    old = _summarize_mirrored_text(OLD_CSV)
    full_new = _summarize_full_new(FULL_NEW_CSV)
    new = _summarize_mirrored_text(NEW_CSV)

    print("### Average character counts")
    print()
    print(f"Old: {old['path']}")
    print(f"- rows: {old['rows']:,} (unique keys: {old['unique_post_primary_key']:,})")
    print(f"- avg original chars: {old['avg_original_chars']:.1f}")
    print(f"- avg mirrored chars: {old['avg_mirrored_chars']:.1f}")
    print()
    print(f"Full new (raw + processed): {full_new['path']}")
    print(
        f"- rows: {full_new['rows']:,} (unique keys: {full_new['unique_post_primary_key']:,})"
    )
    print(f"- avg original chars: {full_new['avg_original_chars']:.1f}")
    print(f"- avg raw mirrored chars: {full_new['avg_raw_mirrored_chars']:.1f}")
    print(f"- avg processed mirrored chars: {full_new['avg_processed_mirrored_chars']:.1f}")
    print()
    print(f"New: {new['path']}")
    print(f"- rows: {new['rows']:,} (unique keys: {new['unique_post_primary_key']:,})")
    print(f"- avg original chars: {new['avg_original_chars']:.1f}")
    print(f"- avg mirrored chars: {new['avg_mirrored_chars']:.1f}")
    print()
    print("Delta (new - old):")
    print(f"- avg original chars: {new['avg_original_chars'] - old['avg_original_chars']:+.1f}")
    print(f"- avg mirrored chars: {new['avg_mirrored_chars'] - old['avg_mirrored_chars']:+.1f}")


if __name__ == "__main__":
    main()

