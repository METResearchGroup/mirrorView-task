"""Temporary helper that seeds ``progress.jsonl`` and ``watcher.json`` under a disposable prefix.

Delete this file before the Step 7 PR merges. Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/seed_progress_watcher_smoke.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --feature is_news_or_opinion \\
        --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/ \\
        --durable-row-total 10000
"""

from __future__ import annotations

import json

import typer

from data_platform.generate_features.feature_progress_watcher import (
    GITHUB_COMMENT_ID_FIELD,
    LAST_POSTED_MILESTONE_FIELD,
    resolve_feature_paths,
)
from data_platform.generate_features.progress_record import ProgressRecord
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    run_id_for_feature,
)
from data_platform.utils.object_store import sha256_hex
from lib.timestamp_utils import get_current_timestamp

DISPOSABLE_KEY_MARKER = "/_smoke/"
SEED_BATCH_SIZE = 2000
SEED_EXPECTED_ROW_TOTAL = 200_000


def _overwrite(store: CampaignObjectStore, key: str, body: bytes) -> None:
    current = store.get(key)
    store.replace(key, body, etag=None if current is None else current.etag)


def seed_progress_and_watcher(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    campaign_id: str,
    feature: str,
    durable_row_total: int,
) -> None:
    """Write synthetic cumulative batch lines and a fresh ``watcher.json``, overwriting both when present.

    Raises
    ------
    ValueError
        When ``paths`` is not under a ``/_smoke/`` key, so the helper can never
        touch a canonical feature prefix.
    """
    if DISPOSABLE_KEY_MARKER not in f"/{paths.prefix}":
        raise ValueError(f"refusing to seed outside a {DISPOSABLE_KEY_MARKER!r} prefix: {paths.prefix}")
    run_id = run_id_for_feature(campaign_id, feature)
    recorded_at = get_current_timestamp()
    lines: list[str] = []
    running_total = 0
    part_index = 0
    while running_total < durable_row_total:
        batch_rows = min(SEED_BATCH_SIZE, durable_row_total - running_total)
        running_total += batch_rows
        record = ProgressRecord(
            campaign_id=campaign_id,
            feature=feature,
            run_id=run_id,
            recorded_at=recorded_at,
            part_index=part_index,
            batch_row_count=batch_rows,
            durable_row_total=running_total,
            expected_row_total=SEED_EXPECTED_ROW_TOTAL,
            percent_complete=running_total / SEED_EXPECTED_ROW_TOTAL,
            last_source_record_id=f"at://example/{running_total}",
            manifest_sha256=sha256_hex(f"seed-manifest-{part_index}".encode()),
            active_openai_batch_id=None,
            ts=recorded_at,
            key=paths.batch_key(part_index),
            row_count=batch_rows,
            sha256=sha256_hex(f"seed-batch-{part_index}".encode()),
            provider_batch_ids=[f"batch_seed_{part_index:05d}"],
            rows_total=running_total,
            batches_total=part_index + 1,
        )
        lines.append(json.dumps(record.model_dump()))
        part_index += 1
    _overwrite(store, paths.progress_key, "".join(f"{line}\n" for line in lines).encode("utf-8"))
    watcher = {GITHUB_COMMENT_ID_FIELD: None, LAST_POSTED_MILESTONE_FIELD: 0}
    _overwrite(store, paths.watcher_key, json.dumps(watcher, indent=2).encode("utf-8"))


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str = typer.Option(..., "--smoke-prefix"),
    durable_row_total: int = typer.Option(..., "--durable-row-total"),
) -> None:
    """Seed the disposable prefix and print the four summary lines from the step spec."""
    paths = resolve_feature_paths(campaign_id, feature, smoke_prefix)
    store = CampaignObjectStore(paths.bucket)
    seed_progress_and_watcher(
        store,
        paths,
        campaign_id=campaign_id,
        feature=feature,
        durable_row_total=durable_row_total,
    )
    print(f"smoke_prefix={smoke_prefix}")
    print("progress_seeded=true")
    print("watcher_seeded=true")
    print(f"durable_row_total={durable_row_total}")


if __name__ == "__main__":
    typer.run(main)
