from __future__ import annotations

"""
Run length-matching ablation experiments.

Run from repo root:

PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py --all
PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py --ablation B1
"""

import argparse
from pathlib import Path

import pandas as pd

from experiments.match_lengths_original_mirrors_2026_06_19.ablation_lib import (
    ABLATION_CONFIGS,
    compute_metrics,
    generate_ablation,
)
from experiments.match_lengths_original_mirrors_2026_06_19.run_match_lengths import (
    INPUT_CSV,
    _output_timestamp,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "ablations"
ABLATIONS_MD = EXPERIMENT_DIR / "ABLATIONS.md"

SAMPLE_SIZE = 25
RANDOM_SEED = 42


def _load_sample() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    if len(df) < SAMPLE_SIZE:
        raise ValueError(f"Input has {len(df)} rows; need at least {SAMPLE_SIZE}.")
    return df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED).reset_index(drop=True)


def _relative_output_path(ablation_id: str, timestamp: str) -> str:
    return f"outputs/ablations/{ablation_id}_{timestamp}.csv"


def _format_results_row(
    ablation_id: str,
    changes: str,
    metrics,
    csv_rel_path: str,
) -> str:
    return (
        f"| {ablation_id} | {changes} | "
        f"{metrics.char_fail_pct:.1%} | {metrics.token_fail_pct:.1%} | "
        f"{metrics.too_long_char_pct:.1%} | {metrics.too_short_char_pct:.1%} | "
        f"{metrics.parse_fail_pct:.1%} | "
        f"{metrics.avg_mirr_chars:.0f}/{metrics.avg_orig_chars:.0f} | "
        f"{metrics.avg_mirr_tokens:.0f}/{metrics.avg_orig_tokens:.0f} | "
        f"`{csv_rel_path}` |"
    )


def _write_ablations_md(rows: list[str]) -> None:
    header = """# Length-matching ablations

Character parity (≥10% relative diff) is the **primary** metric. Token parity is **diagnostic**.

Each ablation uses **25 posts** sampled from `combined_flips/flips.csv` with `random_state=42`.

| Ablation | Changes | Char fail | Token fail | Too long | Too short | Parse fail | Avg chars (mirr/orig) | Avg tokens (mirr/orig) | Output CSV |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
"""
    ABLATIONS_MD.write_text(header + "\n".join(rows) + "\n")


def _load_existing_rows() -> dict[str, str]:
    if not ABLATIONS_MD.exists():
        return {}
    rows: dict[str, str] = {}
    for line in ABLATIONS_MD.read_text().splitlines():
        if not line.startswith("|") or line.startswith("| Ablation") or line.startswith("|-"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if parts and parts[0] in ABLATION_CONFIGS:
            rows[parts[0]] = line
    return rows


def run_ablation(ablation_id: str, *, skip_existing: bool = False) -> str | None:
    config = ABLATION_CONFIGS[ablation_id]
    existing = _load_existing_rows()
    if skip_existing and ablation_id in existing:
        print(f"Skipping {ablation_id}; already in ABLATIONS.md")
        return None

    sampled = _load_sample()
    print(f"Running {ablation_id}: {config.changes}")

    results = generate_ablation(sampled, config)
    metrics = compute_metrics(results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _output_timestamp()
    out_fp = OUTPUT_DIR / f"{ablation_id}_{timestamp}.csv"
    results.to_csv(out_fp, index=False)

    csv_rel = _relative_output_path(ablation_id, timestamp)
    row = _format_results_row(ablation_id, config.changes, metrics, csv_rel)
    existing[ablation_id] = row

    ordered_rows = [existing[aid] for aid in ABLATION_CONFIGS if aid in existing]
    _write_ablations_md(ordered_rows)

    print(f"  {metrics.summary()}")
    print(f"  Wrote {out_fp}")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Run length-matching ablation experiments.")
    parser.add_argument("--ablation", choices=sorted(ABLATION_CONFIGS), action="append")
    parser.add_argument("--all", action="store_true", help="Run all ablations.")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.all:
        ablation_ids = list(ABLATION_CONFIGS)
    elif args.ablation:
        ablation_ids = args.ablation
    else:
        parser.error("Specify --ablation ID or --all")

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    for ablation_id in ablation_ids:
        run_ablation(ablation_id, skip_existing=args.skip_existing)


if __name__ == "__main__":
    main()
