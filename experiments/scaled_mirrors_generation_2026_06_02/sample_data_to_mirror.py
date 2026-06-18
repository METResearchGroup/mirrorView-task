"""Deterministically sample posts to create a mirrorview mirror dataset.

This script:
- Discovers curated `mirrorview.csv` exports under `experiments/scaled_mirrors_generation_2026_06_02/data/*/*/curated/*/metadata.json`
- Normalizes rows into a unified internal schema
- Deduplicates by `post_primary_key` per integration before sampling (Reddit uses `unique_reddit_id`, a composite of post and comment id)
- Filters out `political_stance` values `unclear` and `neutral`
- Samples up to `TARGET_TOTAL` unique posts with an even split across low, middle, and high toxicity tiers; within each tier, Twitter is prioritized and remaining slots are split 50/50 between Bluesky and Reddit
- Writes `concatenated_records/{timestamp}/records.csv`
- Prints stdout summary `value_counts` tables

Run from repo root:

PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

TARGET_TOTAL = 10000
SEED = 42
CONCATENATED_RECORDS_DIRNAME = "concatenated_records"

TOXICITY_TIER_MAP = {
    "low": "sample_low_toxicity",
    "medium": "sample_middle_toxicity",
    "high": "sample_high_toxicity",
    "sample_low_toxicity": "sample_low_toxicity",
    "sample_middle_toxicity": "sample_middle_toxicity",
    "sample_high_toxicity": "sample_high_toxicity",
}
LOW_TOXICITY = "sample_low_toxicity"
MIDDLE_TOXICITY = "sample_middle_toxicity"
HIGH_TOXICITY = "sample_high_toxicity"
TOXICITY_TIERS = [LOW_TOXICITY, MIDDLE_TOXICITY, HIGH_TOXICITY]
STANCES = ["left", "right"]
INTEGRATIONS = ["reddit", "bluesky", "twitter"]

INTEGRATION_TOXICITY_ORDER = [
    (integration, tier) for integration in INTEGRATIONS for tier in TOXICITY_TIERS
]
INTEGRATION_STANCE_ORDER = [
    (integration, stance) for integration in INTEGRATIONS for stance in STANCES
]
TOXICITY_STANCE_ORDER = [
    (tier, stance) for tier in TOXICITY_TIERS for stance in STANCES
]


def _ordered_value_counts(counts: pd.Series, order: list) -> pd.Series:
    """Return value counts reindexed to *order* (missing keys count as 0)."""

    return pd.Series(
        [int(counts.get(key, 0)) for key in order],
        index=pd.Index(order),
    )


def sha256_hex(text: str) -> str:
    """Stable hex digest for deterministic IDs."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _map_sample_toxicity_type(raw_value: str) -> str:
    normalized = raw_value.strip().lower()
    if normalized not in TOXICITY_TIER_MAP:
        raise ValueError(
            f"Unexpected toxicity tier `{raw_value}`. "
            f"Expected one of: {sorted(TOXICITY_TIER_MAP)}."
        )
    return TOXICITY_TIER_MAP[normalized]


def _require_non_null(series: pd.Series, col_name: str, *, integration: str) -> None:
    if series.isna().any():
        null_count = int(series.isna().sum())
        raise ValueError(
            f"Nulls found in required column `{col_name}` for integration `{integration}` "
            f"(null_count={null_count})."
        )


def normalize_mirrorview_df(df_raw: pd.DataFrame, *, integration: str) -> pd.DataFrame:
    """Normalize one raw curated export into the unified internal schema."""

    if integration == "reddit":
        id_col = "post_reddit_id"
        comment_id_col = "comment_id"
        text_col = "body"
    elif integration == "twitter":
        id_col = "tweet_id"
        text_col = "text"
    elif integration == "bluesky":
        id_col = "uri"
        text_col = "text"
    else:
        raise ValueError(f"Unexpected integration `{integration}`.")

    if "political_stance" not in df_raw.columns:
        raise ValueError(
            f"Integration `{integration}` mirrorview export missing `political_stance` column."
        )

    if "toxicity_tier" in df_raw.columns:
        tox_col = "toxicity_tier"
    elif "sample_toxicity_type" in df_raw.columns:
        tox_col = "sample_toxicity_type"
    else:
        raise ValueError(
            f"Integration `{integration}` mirrorview export missing `toxicity_tier` "
            "and `sample_toxicity_type` columns."
        )

    required_cols = [id_col, text_col, tox_col, "political_stance"]
    if integration == "reddit":
        required_cols.append(comment_id_col)

    for required_col in required_cols:
        if required_col not in df_raw.columns:
            raise ValueError(
                f"Integration `{integration}` mirrorview export missing required column `{required_col}`."
            )

    _require_non_null(df_raw[id_col], id_col, integration=integration)
    _require_non_null(df_raw[text_col], text_col, integration=integration)
    _require_non_null(df_raw[tox_col], tox_col, integration=integration)
    _require_non_null(df_raw["political_stance"], "political_stance", integration=integration)
    if integration == "reddit":
        _require_non_null(df_raw[comment_id_col], comment_id_col, integration=integration)

    if integration == "bluesky":
        # Contract: `bluesky_{sha256(uri)}`.
        post_primary_key = "bluesky_" + df_raw[id_col].astype(str).map(sha256_hex)
    else:
        post_primary_key = integration + "_" + df_raw[id_col].astype(str)

    normalized = pd.DataFrame(
        {
            "post_primary_key": post_primary_key,
            "original_text": df_raw[text_col].astype(str),
            "sample_toxicity_type": df_raw[tox_col].astype(str).map(_map_sample_toxicity_type),
            # Normalize for downstream matching and filtering.
            "sampled_stance": df_raw["political_stance"].astype(str).str.strip().str.lower(),
            # Kept temporarily for stdout value_counts (dropped before writing).
            "integration": integration,
        }
    )

    if integration == "reddit":
        normalized["unique_reddit_id"] = (
            "reddit_"
            + df_raw[id_col].astype(str)
            + "_"
            + df_raw[comment_id_col].astype(str)
        )

    # For this sampling run, exclude non-binary stances.
    normalized = normalized[
        ~normalized["sampled_stance"].isin(
            {
                "unclear",
                "neutral",
            }
        )
    ].reset_index(drop=True)

    return normalized


def _split_by_toxicity_tier(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split a shuffled frame into low, middle, and high toxicity rows."""

    unknown = ~df["sample_toxicity_type"].isin(TOXICITY_TIERS)
    if unknown.any():
        bad = sorted(df.loc[unknown, "sample_toxicity_type"].unique())
        raise ValueError(f"Unexpected toxicity tiers: {bad}")

    return {
        tier: df[df["sample_toxicity_type"] == tier].reset_index(drop=True)
        for tier in TOXICITY_TIERS
    }


def _allocate_tier_targets(total: int) -> dict[str, int]:
    """Split *total* evenly across toxicity tiers (remainder goes to first tiers)."""

    base, remainder = divmod(total, len(TOXICITY_TIERS))
    targets = {tier: base for tier in TOXICITY_TIERS}
    for tier in TOXICITY_TIERS[:remainder]:
        targets[tier] += 1
    return targets


def _allocate_remaining_slots(
    n_bluesky_available: int,
    n_reddit_available: int,
    remaining: int,
) -> tuple[int, int]:
    """Split remaining slots 50/50 between Bluesky and Reddit, with backfill."""

    if remaining <= 0:
        return 0, 0

    n_bluesky = min(n_bluesky_available, remaining // 2)
    n_reddit = min(n_reddit_available, remaining - n_bluesky)

    fill = remaining - n_bluesky - n_reddit
    if fill <= 0:
        return n_bluesky, n_reddit

    extra_bluesky = min(n_bluesky_available - n_bluesky, fill)
    n_bluesky += extra_bluesky
    fill -= extra_bluesky

    extra_reddit = min(n_reddit_available - n_reddit, fill)
    n_reddit += extra_reddit

    return n_bluesky, n_reddit


def _sample_one_tier(
    df_twitter: pd.DataFrame,
    df_bluesky: pd.DataFrame,
    df_reddit: pd.DataFrame,
    *,
    n: int,
) -> pd.DataFrame:
    """Sample up to *n* rows for one toxicity tier (Twitter first, then 50/50 Bsky/Reddit)."""

    n_twitter = min(n, len(df_twitter))
    parts: list[pd.DataFrame] = []
    if n_twitter:
        parts.append(df_twitter.iloc[:n_twitter])

    remaining = n - n_twitter
    if remaining > 0:
        n_bluesky, n_reddit = _allocate_remaining_slots(
            len(df_bluesky),
            len(df_reddit),
            remaining,
        )
        if n_bluesky:
            parts.append(df_bluesky.iloc[:n_bluesky])
        if n_reddit:
            parts.append(df_reddit.iloc[:n_reddit])

    if not parts:
        return df_twitter.iloc[:0].copy()
    return pd.concat(parts, ignore_index=True)


def dedupe_rows(df: pd.DataFrame, *, integration: str, subset: list[str]) -> pd.DataFrame:
    """Drop duplicate rows on the given key columns, keeping the first row in frame order."""

    n_before = len(df)
    df_unique = df.drop_duplicates(subset=subset, keep="first")
    n_after = len(df_unique)
    if n_after < n_before:
        key_label = ", ".join(subset)
        print(
            f"Deduplicated {integration}: {n_before:,} rows -> {n_after:,} unique rows on "
            f"({key_label}) ({n_before - n_after:,} duplicates dropped)"
        )
    return df_unique.reset_index(drop=True)


def main() -> None:
    data_root = (
        REPO_ROOT / "experiments/scaled_mirrors_generation_2026_06_02/data"
    ).resolve()
    output_dir = (REPO_ROOT / "experiments/scaled_mirrors_generation_2026_06_02").resolve()

    # 1) Discover curated runs by globbing metadata.json
    metadata_fps = sorted(data_root.glob("*/*/curated/*/metadata.json"))
    if not metadata_fps:
        raise RuntimeError(f"No metadata.json files found under `{data_root}`.")

    data_by_integration: dict[str, list[pd.DataFrame]] = {
        "twitter": [],
        "bluesky": [],
        "reddit": [],
    }

    for metadata_fp in metadata_fps:
        integration = metadata_fp.relative_to(data_root).parts[0]
        if integration not in data_by_integration:
            # Ignore any unexpected folder names under `data/`.
            continue

        metadata = json.loads(metadata_fp.read_text(encoding="utf-8"))
        export_name = metadata["files"]["export"]
        export_fp = metadata_fp.parent / export_name

        if not export_fp.exists():
            raise RuntimeError(
                f"Missing export `{export_name}` for `{metadata_fp}` (expected at `{export_fp}`)."
            )

        df_raw = pd.read_csv(export_fp)
        data_by_integration[integration].append(
            normalize_mirrorview_df(df_raw, integration=integration)
        )

    # 4) Concatenate all rows per integration into three DataFrames.
    dfs: dict[str, pd.DataFrame] = {}
    for integration in ["twitter", "bluesky", "reddit"]:
        if not data_by_integration[integration]:
            raise RuntimeError(f"No curated data found for integration `{integration}`.")
        dfs[integration] = pd.concat(data_by_integration[integration], ignore_index=True)

    df_twitter = dedupe_rows(
        dfs["twitter"], integration="twitter", subset=["post_primary_key"]
    )
    df_bluesky = dedupe_rows(
        dfs["bluesky"], integration="bluesky", subset=["post_primary_key"]
    )
    df_reddit = dedupe_rows(
        dfs["reddit"], integration="reddit", subset=["unique_reddit_id"]
    )
    print()

    # Shuffle deterministically once, then slice to satisfy the sampling contract.
    df_twitter = df_twitter.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)
    df_bluesky = df_bluesky.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)
    df_reddit = df_reddit.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)

    # 5) Sample deterministically without replacement (unique keys only).
    # Even split across toxicity tiers; within each tier, Twitter first, then 50/50 Bsky/Reddit.
    twitter_by_tier = _split_by_toxicity_tier(df_twitter)
    bluesky_by_tier = _split_by_toxicity_tier(df_bluesky)
    reddit_by_tier = _split_by_toxicity_tier(df_reddit)
    tier_targets = _allocate_tier_targets(TARGET_TOTAL)

    sample_parts: list[pd.DataFrame] = []
    for tier in TOXICITY_TIERS:
        sample_parts.append(
            _sample_one_tier(
                twitter_by_tier[tier],
                bluesky_by_tier[tier],
                reddit_by_tier[tier],
                n=tier_targets[tier],
            )
        )

    df_sampled = pd.concat(sample_parts, ignore_index=True)

    selected_total = len(df_sampled)
    if selected_total < TARGET_TOTAL:
        available_total = len(df_twitter) + len(df_bluesky) + len(df_reddit)
        print(
            f"Warning: only {available_total:,} unique posts available; "
            f"sampled {selected_total:,} of target {TARGET_TOTAL:,} "
            f"({TARGET_TOTAL - selected_total:,} short)."
        )

    # 7) Print stdout summaries.
    print("pd.value_counts by integration")
    print(df_sampled["integration"].value_counts())
    print()

    print("pd.value_counts by sample_toxicity_type")
    print(df_sampled["sample_toxicity_type"].value_counts())
    print()

    print("pd.value_counts by sampled_stance")
    print(df_sampled["sampled_stance"].value_counts())
    print()

    print("pd.value_counts by integration x sample_toxicity_type")
    integration_tox = pd.Series(
        list(zip(df_sampled["integration"], df_sampled["sample_toxicity_type"]))
    )
    print(_ordered_value_counts(integration_tox.value_counts(), INTEGRATION_TOXICITY_ORDER))
    print()

    print("pd.value_counts by integration x sampled_stance")
    integration_stance = pd.Series(
        list(zip(df_sampled["integration"], df_sampled["sampled_stance"]))
    )
    print(_ordered_value_counts(integration_stance.value_counts(), INTEGRATION_STANCE_ORDER))
    print()

    print("pd.value_counts by sample_toxicity_type x sampled_stance")
    stance_tox = pd.Series(
        list(zip(df_sampled["sample_toxicity_type"], df_sampled["sampled_stance"]))
    )
    print(_ordered_value_counts(stance_tox.value_counts(), TOXICITY_STANCE_ORDER))
    print()

    # 6) Write output CSV (contract columns only).
    required_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    for col in required_cols:
        if df_sampled[col].isna().any():
            raise ValueError(f"Nulls found in output column `{col}` after sampling.")

    timestamp = get_current_timestamp()
    out_dir = output_dir / CONCATENATED_RECORDS_DIRNAME / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out_fp = out_dir / "records.csv"
    df_sampled[required_cols].to_csv(out_fp, index=False)
    print(f"Wrote {out_fp} ({len(df_sampled)} rows).")


if __name__ == "__main__":
    main()
