"""Temporary live smoke for the campaign batch writer under a disposable S3 prefix.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_write_s3_batch.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --feature is_news_or_opinion \\
        --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/ \\
        --row-count 10
"""

from __future__ import annotations

import json
from typing import Any

import typer

from data_platform.generate_features.generate_bluesky_features import BLUESKY_SPEC
from data_platform.generate_features.models import CampaignRunConfig
from data_platform.generate_features.platform_cli import load_pinned_preprocessed_records
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.generate_features.s3_feature_batches import (
    attach_provenance,
    label_fields,
    write_batch,
)
from data_platform.generate_features.s3_feature_campaign import (
    INTERMEDIATE_ARTIFACT_TAG,
    CampaignObjectStore,
    FeaturePaths,
    load_manifest,
    new_manifest,
    run_id_for_feature,
    save_manifest,
)
from lib.timestamp_utils import get_current_timestamp

SMOKE_BATCH_ID = "batch_smoke_step5_fake"
FAKE_LABELS: dict[str, Any] = {
    "category": "neither",
    "is_political": False,
    "is_likely_spam": False,
    "is_self_contained": True,
    "is_structurally_complete": True,
    "political_stance": "neutral",
    "toxicity_tier": "low",
}


def _fake_rows(
    dataset_id: str, preprocessed_run: str, feature: str, row_count: int, run_id: str
) -> list[dict[str, Any]]:
    """Return ``row_count`` Q44 rows for the first pinned ids, labeled with a fixed fake value."""
    records = load_pinned_preprocessed_records(BLUESKY_SPEC, dataset_id, preprocessed_run)
    ids = sorted(records["source_record_id"].astype(str))[:row_count]
    fields = label_fields(FEATURE_REGISTRY[feature])
    label_timestamp = get_current_timestamp()
    rows = [
        {
            "source_record_id": source_record_id,
            "label_timestamp": label_timestamp,
            **{field: FAKE_LABELS[field] for field in fields},
        }
        for source_record_id in ids
    ]
    request_ids = {source_record_id: f"task-{index:05d}" for index, source_record_id in enumerate(ids)}
    return attach_provenance(
        rows,
        run_id=run_id,
        batch_id=SMOKE_BATCH_ID,
        request_ids=request_ids,
        attempt_count=1,
    )


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str = typer.Option(..., "--smoke-prefix"),
    row_count: int = typer.Option(10, "--row-count"),
) -> None:
    """Write one disposable batch with fake provider ids, or prove that a rewrite is refused.

    The first run under an empty smoke prefix writes ``part-00000`` and prints
    its key, SHA-256, and the manifest, progress, and tag checks. A second run
    finds the manifest, tries to write ``part-00000`` again, and prints that
    the rewrite was refused and the next part index. Both runs print whether
    the canonical campaign feature ``batches/`` prefix gained any object.
    """
    paths = FeaturePaths.from_root_uri(smoke_prefix, feature)
    canonical = FeaturePaths.canonical(campaign_id, feature, dataset_id=dataset_id)
    if paths.prefix.startswith(canonical.prefix) or canonical.prefix.startswith(paths.prefix):
        raise ValueError("smoke prefix must not overlap the canonical campaign feature prefix")
    store = CampaignObjectStore(paths.bucket)
    canonical_before = store.list_keys(canonical.batches_prefix)

    spec = FEATURE_REGISTRY[feature]
    run_id = run_id_for_feature(campaign_id, feature)
    campaign = CampaignRunConfig(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        platform=BLUESKY_SPEC.platform,
        batch_size=row_count,
    )
    rows = _fake_rows(dataset_id, preprocessed_run, feature, row_count, run_id)

    manifest, etag = load_manifest(store, paths)
    if manifest is None:
        manifest = new_manifest(campaign=campaign, spec=spec, expected_row_count=row_count)
        etag = save_manifest(store, paths, manifest, None)
        result = write_batch(
            store, paths, manifest, etag, part_index=0, rows=rows, spec=spec, run_id=run_id
        )
        reloaded, _ = load_manifest(store, paths)
        manifest_updated = any(
            entry["part_index"] == 0 and entry["sha256"] == result.sha256
            for entry in (reloaded or {}).get("batches", [])
        )
        progress = store.get(paths.progress_key)
        last_line = json.loads(progress.body.splitlines()[-1]) if progress else {}
        progress_appended = last_line.get("sha256") == result.sha256
        intermediate_tag = store.get_tags(result.key) == INTERMEDIATE_ARTIFACT_TAG
        print(f"smoke_prefix={smoke_prefix}")
        print(f"batch_key={paths.uri(result.key)}")
        print(f"batch_sha256={result.sha256}")
        print(f"manifest_updated={str(manifest_updated).lower()}")
        print(f"progress_appended={str(progress_appended).lower()}")
        print(f"intermediate_tag={str(intermediate_tag).lower()}")
    else:
        try:
            write_batch(
                store, paths, manifest, etag, part_index=0, rows=rows, spec=spec, run_id=run_id
            )
            refused = False
        except FileExistsError:
            refused = True
        print(f"batch_rewrite_refused={str(refused).lower()}")
        print(f"next_part_index={len(manifest['batches'])}")

    canonical_after = store.list_keys(canonical.batches_prefix)
    touched = bool(canonical_after) or canonical_after != canonical_before
    print(f"canonical_batches_prefix_touched={str(touched).lower()}")


if __name__ == "__main__":
    typer.run(main)
