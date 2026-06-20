from __future__ import annotations

"""
Plot histograms of (mirror_len - original_len) differentials for three variants.

Creates PNGs under:
  jobs/mirrorview_scaled_2026_06_18/outputs/differentials/{timestamp}/

Run from repo root:

PYTHONPATH=. uv run python jobs/mirrorview_scaled_2026_06_18/differentials.py
"""

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent

OLD_CSV = HERE / "old_flips.csv"
FULL_NEW_CSV = HERE / "full_new_flips.csv"

OUTPUT_ROOT = HERE / "outputs" / "differentials"


def _plot_differentials(
    *,
    input_csv: Path,
    mirror_col: str,
    output_png: Path,
    title: str,
) -> float:
    df = pd.read_csv(input_csv)
    if "original_text" not in df.columns or mirror_col not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `{mirror_col}` columns in {input_csv}"
        )

    original_lengths = df["original_text"].fillna("").astype(str).str.len()
    mirror_lengths = df[mirror_col].fillna("").astype(str).str.len()
    differentials = mirror_lengths - original_lengths
    mean_differential = float(differentials.mean())

    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 6))
    plt.hist(differentials, bins=50, color="steelblue", edgecolor="white", alpha=0.85)
    plt.axvline(
        mean_differential,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean differential ({mean_differential:.1f} chars)",
    )
    plt.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.4)
    plt.xlabel("Mirror length − original length (chars)")
    plt.ylabel("Number of posts")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_png, dpi=160)
    plt.close()
    return mean_differential


def main() -> None:
    timestamp = datetime.now().strftime("%Y_%m_%d-%H%M%S")
    out_dir = OUTPUT_ROOT / timestamp

    variants = [
        {
            "label": "old_flips (mirrored_text)",
            "csv": OLD_CSV,
            "mirror_col": "mirrored_text",
            "png": out_dir / "old_flips_mirrored_text_minus_original.png",
            "title": "Differential: old_flips.csv (mirrored_text − original_text)",
        },
        {
            "label": "full_new_flips (raw_mirrored_text)",
            "csv": FULL_NEW_CSV,
            "mirror_col": "raw_mirrored_text",
            "png": out_dir / "full_new_flips_raw_mirrored_text_minus_original.png",
            "title": "Differential: full_new_flips.csv (raw_mirrored_text − original_text)",
        },
        {
            "label": "full_new_flips (processed_mirrored_text)",
            "csv": FULL_NEW_CSV,
            "mirror_col": "processed_mirrored_text",
            "png": out_dir / "full_new_flips_processed_mirrored_text_minus_original.png",
            "title": "Differential: full_new_flips.csv (processed_mirrored_text − original_text)",
        },
    ]

    for v in variants:
        if not Path(v["csv"]).exists():
            raise FileNotFoundError(f"Missing {v['csv']}")

    print(f"Output directory: {out_dir}")
    for v in variants:
        mean = _plot_differentials(
            input_csv=Path(v["csv"]),
            mirror_col=str(v["mirror_col"]),
            output_png=Path(v["png"]),
            title=str(v["title"]),
        )
        print(f"- {v['label']}: wrote {v['png']} (mean differential {mean:.1f} chars)")


if __name__ == "__main__":
    main()

