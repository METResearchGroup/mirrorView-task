"""Deterministically sample posts to create a mirrorview mirror dataset.

This script:
- Discovers curated `mirrorview.csv` exports under `experiments/scaled_mirrors_generation_2026_06_02/data/*/*/curated/*/metadata.json`
- Normalizes rows into a unified internal schema
- Samples exactly `TARGET_TOTAL=11000` posts (Twitter prioritized, remainder split 50/50 between Bluesky and Reddit)
- Writes `sampled_posts_{timestamp}.csv`
- Prints stdout summary `value_counts` tables
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

TARGET_TOTAL = 11000
SEED = 42


def sha256_hex(text: str) -> str:
    """Stable hex digest for deterministic IDs."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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

    for required_col in [id_col, text_col, tox_col, "political_stance"]:
        if required_col not in df_raw.columns:
            raise ValueError(
                f"Integration `{integration}` mirrorview export missing required column `{required_col}`."
            )

    _require_non_null(df_raw[id_col], id_col, integration=integration)
    _require_non_null(df_raw[text_col], text_col, integration=integration)
    _require_non_null(df_raw[tox_col], tox_col, integration=integration)
    _require_non_null(df_raw["political_stance"], "political_stance", integration=integration)

    if integration == "bluesky":
        # Contract: `bluesky_{sha256(uri)}`.
        post_id = "bluesky_" + df_raw[id_col].astype(str).map(sha256_hex)
    else:
        post_id = integration + "_" + df_raw[id_col].astype(str)

    return pd.DataFrame(
        {
            "post_id": post_id,
            "text": df_raw[text_col].astype(str),
            "toxicity_tier": df_raw[tox_col].astype(str),
            "political_stance": df_raw["political_stance"].astype(str),
            # Kept temporarily for stdout value_counts (dropped before writing).
            "integration": integration,
        }
    )


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

    df_twitter = dfs["twitter"]
    df_bluesky = dfs["bluesky"]
    df_reddit = dfs["reddit"]

    # Shuffle deterministically once, then slice to satisfy the sampling contract.
    df_twitter = df_twitter.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)
    df_bluesky = df_bluesky.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)
    df_reddit = df_reddit.sample(frac=1.0, random_state=SEED, replace=False).reset_index(drop=True)

    # 5) Sample deterministically without replacement to TOTAL.
    n_twitter = min(TARGET_TOTAL, len(df_twitter))
    df_twitter_sample = df_twitter.iloc[:n_twitter].copy()

    remaining = TARGET_TOTAL - n_twitter
    n_bluesky = min(len(df_bluesky), remaining // 2)
    n_reddit = min(len(df_reddit), remaining - n_bluesky)

    df_bluesky_sample = df_bluesky.iloc[:n_bluesky].copy()
    df_reddit_sample = df_reddit.iloc[:n_reddit].copy()

    selected_total = len(df_twitter_sample) + len(df_bluesky_sample) + len(df_reddit_sample)
    if selected_total < TARGET_TOTAL:
        fill = TARGET_TOTAL - selected_total
        bluesky_remaining = len(df_bluesky) - n_bluesky
        reddit_remaining = len(df_reddit) - n_reddit

        if bluesky_remaining >= fill:
            extra = df_bluesky.iloc[n_bluesky : n_bluesky + fill].copy()
            df_bluesky_sample = pd.concat([df_bluesky_sample, extra], ignore_index=True)
        elif reddit_remaining >= fill:
            extra = df_reddit.iloc[n_reddit : n_reddit + fill].copy()
            df_reddit_sample = pd.concat([df_reddit_sample, extra], ignore_index=True)
        else:
            raise RuntimeError(
                "Insufficient data to sample the target amount. "
                f"Have_total={len(df_twitter) + len(df_bluesky) + len(df_reddit)} "
                f"Target_total={TARGET_TOTAL}."
            )

    df_sampled = pd.concat(
        [df_twitter_sample, df_bluesky_sample, df_reddit_sample], ignore_index=True
    )

    # 7) Print stdout summaries.
    print("pd.value_counts by integration")
    print(df_sampled["integration"].value_counts())
    print()

    print("pd.value_counts by integration x toxicity_tier")
    integration_tox = pd.Series(
        list(zip(df_sampled["integration"], df_sampled["toxicity_tier"]))
    )
    print(integration_tox.value_counts())
    print()

    print("pd.value_counts by integration x political_stance")
    print(
        pd.Series(
            list(zip(df_sampled["integration"], df_sampled["political_stance"]))
        ).value_counts()
    )
    print()

    print("pd.value_counts by toxicity_tier x political_stance")
    stance_tox = pd.Series(
        list(zip(df_sampled["toxicity_tier"], df_sampled["political_stance"]))
    )
    print(stance_tox.value_counts())
    print()

    # 6) Write output CSV (contract columns only).
    required_cols = ["post_id", "text", "toxicity_tier", "political_stance"]
    for col in required_cols:
        if df_sampled[col].isna().any():
            raise ValueError(f"Nulls found in output column `{col}` after sampling.")

    timestamp = get_current_timestamp()
    out_fp = output_dir / f"sampled_posts_{timestamp}.csv"
    df_sampled[required_cols].to_csv(out_fp, index=False)
    print(f"Wrote {out_fp} ({len(df_sampled)} rows).")


if __name__ == "__main__":
    main()
