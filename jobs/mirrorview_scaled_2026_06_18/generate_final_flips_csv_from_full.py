from __future__ import annotations

"""
Generate the final `flips.csv` from `full_new_flips.csv`.

Transforms:
- `processed_mirrored_text` -> `mirrored_text`
- drops `raw_mirrored_text`
- keeps all other columns the same

Run from repo root:

PYTHONPATH=. uv run python jobs/mirrorview_scaled_2026_06_18/generate_final_flips_csv_from_full.py --force
"""

from pathlib import Path

import pandas as pd
import typer

app = typer.Typer(add_completion=False)

HERE = Path(__file__).resolve().parent
FULL_NEW_CSV = HERE / "full_new_flips.csv"
OUTPUT_CSV = HERE / "flips.csv"

REQUIRED_COLS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "raw_mirrored_text",
    "processed_mirrored_text",
]

OUTPUT_COLS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "mirrored_text",
]


def generate_final_flips_csv_from_full(*, full_csv: Path = FULL_NEW_CSV, output_csv: Path = OUTPUT_CSV) -> None:
    if not full_csv.exists():
        raise FileNotFoundError(f"Missing input CSV: {full_csv}")

    df = pd.read_csv(full_csv)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {full_csv}: {missing}")

    out = df.drop(columns=["raw_mirrored_text"]).rename(
        columns={"processed_mirrored_text": "mirrored_text"}
    )
    out = out[OUTPUT_COLS]
    out.to_csv(output_csv, index=False)
    print(f"Wrote {len(out)} rows to {output_csv}")


@app.command()
def main(
    full_csv: Path = typer.Option(
        FULL_NEW_CSV,
        "--full-csv",
        help="Input CSV that includes raw + processed mirrored text.",
    ),
    output_csv: Path = typer.Option(
        OUTPUT_CSV,
        "--output-csv",
        help="Output final flips.csv.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite output CSV if it exists.",
    ),
) -> None:
    if force and output_csv.exists():
        output_csv.unlink()
    generate_final_flips_csv_from_full(full_csv=full_csv, output_csv=output_csv)


if __name__ == "__main__":
    app()

