"""Patch Reddit ``post_primary_key`` values in generated flip CSVs.

Background:
- ``sample_data_to_mirror.py`` deduplicates Reddit on ``unique_reddit_id``
  (``reddit_{post_reddit_id}_{comment_id}``), but writes only ``post_primary_key``
  (``reddit_{post_reddit_id}``) to ``records.csv``.
- ``generate_flips.py`` copies that column through unchanged, so each ``flips.csv``
  can contain many distinct comments that share the same ``post_primary_key``.
- ``balance_flips.py`` merges flip runs and deduplicates on ``post_primary_key``,
  which incorrectly collapses multiple Reddit comments from the same post.

This script repairs existing flip outputs without re-running generation:
- Loads all curated Reddit ``mirrorview.csv`` exports under ``data/reddit``
- Builds a lookup from ``(post_reddit_id, body)`` to ``unique_reddit_id``
- For each source ``flips.csv``, writes ``edited_flips.csv`` in the same folder
  with Reddit rows updated to the composite key; Twitter/Bluesky rows are unchanged.

Run ``balance_flips.py`` against the resulting ``edited_flips.csv`` files.

Run from repo root:

PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/fix_primary_key_column_for_reddit_posts.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPERIMENT_DIR = Path(__file__).resolve().parent
REDDIT_DATA_ROOT = EXPERIMENT_DIR / "data" / "reddit"
GENERATED_FLIPS_DIR = EXPERIMENT_DIR / "generated_flips"

SOURCE_FLIPS = [
    GENERATED_FLIPS_DIR / "2026_06_12-12:44:13" / "flips.csv",
    GENERATED_FLIPS_DIR / "2026_06_17-14:50:48" / "flips.csv",
]

OUTPUT_NAME = "edited_flips.csv"


def _load_reddit_lookup() -> tuple[set[str], pd.Series]:
    """Build ``(post_reddit_id, body) -> unique_reddit_id`` from curated Reddit exports."""

    mirrorview_fps = sorted(REDDIT_DATA_ROOT.glob("*/curated/*/mirrorview.csv"))
    if not mirrorview_fps:
        raise FileNotFoundError(f"No Reddit mirrorview exports found under `{REDDIT_DATA_ROOT}`.")

    frames: list[pd.DataFrame] = []
    for mirrorview_fp in mirrorview_fps:
        df = pd.read_csv(mirrorview_fp, usecols=["post_reddit_id", "comment_id", "body"])
        df["post_reddit_id"] = df["post_reddit_id"].astype(str)
        df["comment_id"] = df["comment_id"].astype(str)
        df["body"] = df["body"].astype(str)
        df["unique_reddit_id"] = (
            "reddit_" + df["post_reddit_id"] + "_" + df["comment_id"]
        )
        frames.append(df)

    reddit = pd.concat(frames, ignore_index=True)
    n_before = len(reddit)
    reddit = reddit.drop_duplicates(subset=["unique_reddit_id"], keep="first").reset_index(drop=True)
    if len(reddit) < n_before:
        print(
            f"Deduplicated Reddit lookup: {n_before:,} rows -> {len(reddit):,} unique "
            f"``unique_reddit_id`` values ({n_before - len(reddit):,} duplicates dropped)"
        )

    body_dupes = reddit.duplicated(subset=["post_reddit_id", "body"], keep=False)
    if body_dupes.any():
        n_dupes = int(body_dupes.sum())
        print(
            f"Warning: Reddit lookup has {n_dupes} rows with duplicate (post_reddit_id, body) "
            f"pairs; keeping the first ``unique_reddit_id`` per pair."
        )
        reddit = reddit.drop_duplicates(subset=["post_reddit_id", "body"], keep="first")

    unique_ids = set(reddit["unique_reddit_id"].astype(str))
    lookup = reddit.set_index(["post_reddit_id", "body"])["unique_reddit_id"]
    return unique_ids, lookup


def _fix_post_primary_key(
    post_primary_key: str,
    original_text: str,
    *,
    unique_reddit_ids: set[str],
    reddit_lookup: pd.Series,
) -> str:
    key = str(post_primary_key)
    if not key.startswith("reddit_"):
        return key

    if key in unique_reddit_ids:
        return key

    post_id = key.removeprefix("reddit_")
    if "_" in post_id:
        raise ValueError(
            f"Reddit ``post_primary_key`` {key!r} is not a known ``unique_reddit_id`` "
            f"and is not a post-only key."
        )

    try:
        return str(reddit_lookup.loc[(post_id, str(original_text))])
    except KeyError as exc:
        raise KeyError(
            f"No Reddit lookup match for post_primary_key={key!r} "
            f"(post_reddit_id={post_id!r})."
        ) from exc


def _fix_flips_csv(
    flips_fp: Path,
    *,
    unique_reddit_ids: set[str],
    reddit_lookup: pd.Series,
) -> Path:
    if not flips_fp.exists():
        raise FileNotFoundError(f"Missing flips CSV: {flips_fp}")

    df = pd.read_csv(flips_fp)
    if "post_primary_key" not in df.columns or "original_text" not in df.columns:
        raise KeyError(f"{flips_fp} must contain `post_primary_key` and `original_text`.")

    n_unique_before = df["post_primary_key"].nunique()
    reddit_mask = df["post_primary_key"].astype(str).str.startswith("reddit_")
    n_reddit = int(reddit_mask.sum())
    if n_reddit:
        df.loc[reddit_mask, "post_primary_key"] = [
            _fix_post_primary_key(
                key,
                text,
                unique_reddit_ids=unique_reddit_ids,
                reddit_lookup=reddit_lookup,
            )
            for key, text in zip(
                df.loc[reddit_mask, "post_primary_key"],
                df.loc[reddit_mask, "original_text"],
            )
        ]

    out_fp = flips_fp.parent / OUTPUT_NAME
    df.to_csv(out_fp, index=False)

    print(f"Input:  {flips_fp} ({len(df):,} rows; {n_reddit:,} Reddit rows)")
    print(
        f"        unique post_primary_key before: {n_unique_before:,}; "
        f"after: {df['post_primary_key'].nunique():,}"
    )
    print(f"Output: {out_fp}")
    return out_fp


def main() -> None:
    unique_reddit_ids, reddit_lookup = _load_reddit_lookup()
    print(f"Reddit lookup: {len(unique_reddit_ids):,} unique ``unique_reddit_id`` values")
    print()

    for flips_fp in SOURCE_FLIPS:
        _fix_flips_csv(
            flips_fp,
            unique_reddit_ids=unique_reddit_ids,
            reddit_lookup=reddit_lookup,
        )
        print()


if __name__ == "__main__":
    main()
