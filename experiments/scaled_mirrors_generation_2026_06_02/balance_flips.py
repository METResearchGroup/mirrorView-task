"""Balance and subsample generated mirror flips into a single combined dataset.

Context:
- Two flip-generation runs produced more rows than needed and with uneven toxicity mix:
  - ``generated_flips/2026_06_12-12:44:13/flips.csv`` (older run, extra coverage)
  - ``generated_flips/2026_06_17-14:50:48/flips.csv`` (newer run, ~33/33/33 toxicity)
- The target combined sample is 10,000 rows with a 25/50/25 low/middle/high toxicity split.
- Within each toxicity tier, Twitter rows are taken first; remaining slots split 50/50
  between Bluesky and Reddit (same integration priority as ``sample_data_to_mirror.py``).

This script:
- Loads both source ``edited_flips.csv`` files (produced by
  ``fix_primary_key_column_for_reddit_posts.py``) and concatenates them
  (newer file wins on duplicate keys)
- Deduplicates on ``post_primary_key`` (Reddit keys are ``unique_reddit_id``)
- Deterministically subsamples to the tier targets
- Writes ``generated_flips/combined_flips/flips.csv``
- Prints stdout summary ``value_counts`` tables (same dimensions as ``sample_data_to_mirror.py``)

Run from repo root:

PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/balance_flips.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror import (
    INTEGRATION_STANCE_ORDER,
    INTEGRATION_TOXICITY_ORDER,
    INTEGRATIONS,
    LOW_TOXICITY,
    MIDDLE_TOXICITY,
    HIGH_TOXICITY,
    TOXICITY_STANCE_ORDER,
    TOXICITY_TIERS,
    _ordered_value_counts,
    _sample_one_tier,
    _split_by_toxicity_tier,
    SEED,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
GENERATED_FLIPS_DIR = EXPERIMENT_DIR / "generated_flips"

SOURCE_FLIPS = [
    GENERATED_FLIPS_DIR / "2026_06_12-12:44:13" / "edited_flips.csv",
    GENERATED_FLIPS_DIR / "2026_06_17-14:50:48" / "edited_flips.csv",
]

OUTPUT_DIR = GENERATED_FLIPS_DIR / "combined_flips"
OUTPUT_CSV = OUTPUT_DIR / "flips.csv"

TARGET_TOTAL = 10_000
TOXICITY_TIER_WEIGHTS = {
    LOW_TOXICITY: 0.25,
    MIDDLE_TOXICITY: 0.50,
    HIGH_TOXICITY: 0.25,
}

OUTPUT_COLUMNS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "mirrored_text",
]


def _integration_from_key(post_primary_key: str) -> str:
    for integration in INTEGRATIONS:
        if post_primary_key.startswith(f"{integration}_"):
            return integration
    raise ValueError(f"Unexpected post_primary_key prefix: {post_primary_key!r}")


def _allocate_weighted_tier_targets(total: int) -> dict[str, int]:
    """Split *total* across tiers using ``TOXICITY_TIER_WEIGHTS`` (largest-remainder)."""

    raw = {tier: total * TOXICITY_TIER_WEIGHTS[tier] for tier in TOXICITY_TIERS}
    targets = {tier: int(value) for tier, value in raw.items()}
    remainder = total - sum(targets.values())
    if remainder:
        fractional_rank = sorted(
            TOXICITY_TIERS,
            key=lambda tier: raw[tier] - targets[tier],
            reverse=True,
        )
        for tier in fractional_rank[:remainder]:
            targets[tier] += 1
    return targets


def _load_and_merge_sources(source_paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for source_fp in source_paths:
        if not source_fp.exists():
            raise FileNotFoundError(f"Missing source flips CSV: {source_fp}")
        frames.append(pd.read_csv(source_fp))

    merged = pd.concat(frames, ignore_index=True)
    n_before = len(merged)
    merged = merged.drop_duplicates(subset=["post_primary_key"], keep="last").reset_index(drop=True)
    n_after = len(merged)
    if n_after < n_before:
        print(
            f"Deduplicated merged flips: {n_before:,} rows -> {n_after:,} unique rows on "
            f"(post_primary_key) ({n_before - n_after:,} duplicates dropped; newer file wins)"
        )
    return merged


def _split_by_integration(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = df.copy()
    df["integration"] = df["post_primary_key"].astype(str).map(_integration_from_key)
    return {
        integration: df[df["integration"] == integration].reset_index(drop=True)
        for integration in INTEGRATIONS
    }


def _print_sampling_summaries(df: pd.DataFrame) -> None:
    print("pd.value_counts by integration")
    print(df["integration"].value_counts())
    print()

    print("pd.value_counts by sample_toxicity_type")
    print(df["sample_toxicity_type"].value_counts())
    print()

    print("pd.value_counts by sampled_stance")
    print(df["sampled_stance"].value_counts())
    print()

    print("pd.value_counts by integration x sample_toxicity_type")
    integration_tox = pd.Series(
        list(zip(df["integration"], df["sample_toxicity_type"]))
    )
    print(_ordered_value_counts(integration_tox.value_counts(), INTEGRATION_TOXICITY_ORDER))
    print()

    print("pd.value_counts by integration x sampled_stance")
    integration_stance = pd.Series(
        list(zip(df["integration"], df["sampled_stance"]))
    )
    print(_ordered_value_counts(integration_stance.value_counts(), INTEGRATION_STANCE_ORDER))
    print()

    print("pd.value_counts by sample_toxicity_type x sampled_stance")
    stance_tox = pd.Series(
        list(zip(df["sample_toxicity_type"], df["sampled_stance"]))
    )
    print(_ordered_value_counts(stance_tox.value_counts(), TOXICITY_STANCE_ORDER))
    print()


def main() -> None:
    df = _load_and_merge_sources(SOURCE_FLIPS)
    print()

    by_integration = _split_by_integration(df)
    for integration in INTEGRATIONS:
        by_integration[integration] = (
            by_integration[integration]
            .sample(frac=1.0, random_state=SEED, replace=False)
            .reset_index(drop=True)
        )

    tier_targets = _allocate_weighted_tier_targets(TARGET_TOTAL)
    print("Tier targets:")
    for tier in TOXICITY_TIERS:
        print(f"  {tier}: {tier_targets[tier]:,}")
    print()

    sample_parts: list[pd.DataFrame] = []
    for tier in TOXICITY_TIERS:
        twitter_tier = _split_by_toxicity_tier(by_integration["twitter"])[tier]
        bluesky_tier = _split_by_toxicity_tier(by_integration["bluesky"])[tier]
        reddit_tier = _split_by_toxicity_tier(by_integration["reddit"])[tier]
        sample_parts.append(
            _sample_one_tier(
                twitter_tier,
                bluesky_tier,
                reddit_tier,
                n=tier_targets[tier],
            )
        )

    df_sampled = pd.concat(sample_parts, ignore_index=True)

    selected_total = len(df_sampled)
    if selected_total < TARGET_TOTAL:
        print(
            f"Warning: only {len(df):,} unique flips available; "
            f"sampled {selected_total:,} of target {TARGET_TOTAL:,} "
            f"({TARGET_TOTAL - selected_total:,} short)."
        )

    missing_cols = [col for col in OUTPUT_COLUMNS if col not in df_sampled.columns]
    if missing_cols:
        raise KeyError(f"Sampled frame missing required columns: {missing_cols}")

    _print_sampling_summaries(df_sampled)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_sampled[OUTPUT_COLUMNS].to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {OUTPUT_CSV} ({len(df_sampled)} rows).")


if __name__ == "__main__":
    main()
