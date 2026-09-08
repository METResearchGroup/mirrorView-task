"""Run the Reddit curated Perspective v2 experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --write-v2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.reddit_curated_perspective_v2_2026_09_08.load_curated import (
    PINNED_CURATED_S3_URI,
    PINNED_CURATED_SHA256,
    load_pinned_curated,
    medium_rows,
)
from experiments.reddit_curated_perspective_v2_2026_09_08.promote_v2 import (
    V2_OBJECT_KEY,
    apply_promotions,
    select_promotions,
    write_curated_v2,
)
from experiments.reddit_curated_perspective_v2_2026_09_08.score_medium import (
    count_already_scored,
    require_all_medium_scored,
    score_medium_comments,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_SCORES_PATH = EXPERIMENT_DIR / "outputs" / "medium_perspective_scores.parquet"
DEFAULT_PROMOTION_IDS_PATH = EXPERIMENT_DIR / "outputs" / "promotion_source_record_ids.json"
JSON_INDENT = 2


def _run_load_only() -> int:
    curated = load_pinned_curated()
    medium = medium_rows(curated)
    print(f"curated_rows={len(curated)}")
    print(f"medium_rows={len(medium)}")
    print(f"source_sha256={PINNED_CURATED_SHA256}")
    return 0


def _run_score() -> int:
    curated = load_pinned_curated()
    medium = medium_rows(curated)
    already_scored = count_already_scored(medium, DEFAULT_SCORES_PATH)
    scores = score_medium_comments(medium, scores_path=DEFAULT_SCORES_PATH)
    newly_scored = len(scores) - already_scored
    print(f"medium_rows={len(medium)}")
    print(f"already_scored={already_scored}")
    print(f"newly_scored={newly_scored}")
    print(f"scores_path={DEFAULT_SCORES_PATH}")
    return 0


def _run_write_v2() -> int:
    curated = load_pinned_curated()
    require_all_medium_scored(medium_rows(curated), DEFAULT_SCORES_PATH)
    scores = pd.read_parquet(DEFAULT_SCORES_PATH)
    promotion_ids = select_promotions(scores)
    curated_v2 = apply_promotions(curated, promotion_ids)
    store = _v2_store()
    v2_sha256 = write_curated_v2(curated_v2, store=store, key=V2_OBJECT_KEY)
    _write_promotion_ids(promotion_ids)
    _require_key_sha256(store, V2_OBJECT_KEY, v2_sha256)
    _require_key_sha256(store, _original_object_key(), PINNED_CURATED_SHA256)
    print(f"promotions={len(promotion_ids)}")
    print(f"v2_rows={len(curated_v2)}")
    print(f"v2_sha256={v2_sha256}")
    print(f"original_sha256={PINNED_CURATED_SHA256}")
    return 0


def _v2_store() -> CampaignObjectStore:
    bucket, _key = parse_s3_uri(PINNED_CURATED_S3_URI)
    return CampaignObjectStore(bucket)


def _original_object_key() -> str:
    _bucket, key = parse_s3_uri(PINNED_CURATED_S3_URI)
    return key


def _write_promotion_ids(promotion_ids: list[str]) -> None:
    DEFAULT_PROMOTION_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(promotion_ids, indent=JSON_INDENT) + "\n"
    DEFAULT_PROMOTION_IDS_PATH.write_text(payload)


def _require_key_sha256(store: CampaignObjectStore, key: str, expected: str) -> None:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    if sha256_hex(stored.body) != expected:
        raise ValueError(f"sha256 mismatch for {key}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--load-only", action="store_true")
    group.add_argument("--score", action="store_true")
    group.add_argument("--write-v2", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.load_only:
        return _run_load_only()
    if args.score:
        return _run_score()
    return _run_write_v2()


if __name__ == "__main__":
    sys.exit(main())
