from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lib.timestamp_utils import get_current_timestamp


REQUIRED_COLUMNS = [
    "prolific_id",
    "trial_type",
    "post_id",
    "original_text",
    "mirror_text",
    "decision",
]


def is_valid_post_id(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip()
    return (s != "") & (s.str.lower() != "nan")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Postprocess a MirrorView exported CSV into a compact moderation-trial table.\n\n"
            "Input must be a CSV produced by scripts/export_study_results.py."
        )
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="Path to CSV output from scripts/export_study_results.py (required).",
    )
    args = parser.parse_args()

    input_csv: Path = args.input_csv
    if not input_csv.is_file():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {input_csv}: {missing}")

    mask = (df["trial_type"] == "moderation-trial") & is_valid_post_id(df["post_id"])
    filtered = df.loc[
        mask, ["prolific_id", "post_id", "original_text", "mirror_text", "decision"]
    ].copy()
    filtered = filtered.rename(columns={"post_id": "message_id"})

    out_dir = (
        Path(__file__).resolve().parent
        / "outputs"
        / "postprocessed"
        / get_current_timestamp()
    )
    out_dir.mkdir(parents=True, exist_ok=False)

    out_csv = out_dir / "mirrorview.csv"
    filtered.to_csv(out_csv, index=False)

    metadata = {
        "source_csv": str(input_csv.resolve()),
        "output_csv": str(out_csv.resolve()),
        "rows_input": int(len(df)),
        "rows_output": int(len(filtered)),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"Wrote {len(filtered)} row(s) to {out_csv}")


if __name__ == "__main__":
    main()

