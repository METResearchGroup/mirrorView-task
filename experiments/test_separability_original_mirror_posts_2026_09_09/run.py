"""Run the separability original vs mirror experiment.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and pull request 273 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
then wrote 10000 presentations
and S3 object experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet exists
and gold_human_slot is first or second on every row
and first_text plus second_text are the original and the mirror in some order
and no OpenAI or Bedrock call is made

given the presentation key already exists
when the command is run again
then the process raises FileExistsError
and the catalog S3 object is unchanged

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.generate_features.campaign_engine_map import (
    BEDROCK_ENGINE_TYPE,
    OPENAI_ENGINE_TYPE,
)
from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.models import CampaignRunConfig, FeatureSpec, LabelTask
from data_platform.generate_features.s3_feature_batches import (
    adopt_unrecorded_batch,
    attach_row_metadata,
    consolidate_final,
    write_batch,
)
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    append_errors,
    load_manifest,
    new_manifest,
    read_failed_ids,
    run_id_for_feature,
    save_manifest,
)
from experiments.test_separability_original_mirror_posts_2026_09_09 import (
    bedrock_runner,
    openai_runner,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    ATTEMPT_COUNT,
    BATCH_ID_PREFIX,
    BEDROCK_SMOKE_ROOT_URI,
    CACHE_DIRNAME,
    CAMPAIGN_ID,
    CAMPAIGN_PLATFORM,
    DATASET_ID,
    EngineName,
    EXPERIMENT_DIRNAME,
    FAILED_SUMMARY_FORMAT,
    FEATURE_NAME,
    FINAL_EXISTS_FORMAT,
    ID_COLUMN,
    LABELS_ROOT_URI,
    LABELED_SUMMARY_FORMAT,
    OPENAI_SMOKE_ROOT_URI,
    OUTPUT_S3_BUCKET,
    PART_INDEX_WIDTH,
    PREPROCESSED_RUN,
    PROMPT_TEXT_COLUMN,
    REQUEST_ID_SEPARATOR,
    SMOKE_FEATURE_NAME,
    SORT_KIND,
    campaign_batch_size,
    pinned_catalog,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.loader import (
    build_presentation_table,
    load_catalog,
    load_presentations,
    smoke_presentations,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.schema import separability_spec
from experiments.test_separability_original_mirror_posts_2026_09_09.score import score_labels
from experiments.test_separability_original_mirror_posts_2026_09_09.write import (
    print_presentation_summary,
    require_presentation_key_absent,
    upload_presentation,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

MANIFEST_IDENTITY_FIELDS = (
    "campaign_id",
    "dataset_id",
    "preprocessed_run",
    "feature",
    "model_id",
    "prompt_hash",
    "batch_size",
    "expected_row_count",
    "run_id",
    "engine_type",
)
ENGINE_TYPE_FIELD = "engine_type"

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def main(
    write_presentation: bool = typer.Option(
        False, "--write-presentation", help="Write the shared presentation parquet."
    ),
    engine: str | None = typer.Option(
        None, "--engine", help="Labeling engine: openai or bedrock."
    ),
    smoke: bool = typer.Option(False, "--smoke", help="Label only the smoke subset."),
    score: bool = typer.Option(False, "--score", help="Score labels and write RESULTS.md."),
) -> None:
    """Write presentations, label pairs, or score results."""
    _validate_cli_flags(write_presentation, engine, smoke, score)
    if write_presentation:
        _write_presentation()
        return
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    presentations = load_presentations(store)
    if score:
        score_labels(presentations, store, _experiment_dir())
        return
    if engine is not None:
        _run_engine(_parse_engine_name(engine), smoke, presentations, store)


def _validate_cli_flags(
    write_presentation: bool,
    engine: str | None,
    smoke: bool,
    score: bool,
) -> None:
    """Ensure mutually exclusive CLI modes are not combined."""
    if smoke and engine is None:
        raise ValueError("--smoke requires --engine")
    selected = [write_presentation, engine is not None, score]
    if sum(selected) != 1:
        raise ValueError("choose exactly one of --write-presentation, --engine, or --score")
    if engine is not None:
        _parse_engine_name(engine)


def _parse_engine_name(engine: str) -> EngineName:
    try:
        return EngineName(engine)
    except ValueError as error:
        raise ValueError(f"unsupported engine: {engine}") from error


def _write_presentation() -> None:
    """Download the catalog, shuffle pairs, and upload presentations.parquet."""
    source = pinned_catalog()
    experiment_dir = _experiment_dir()
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    require_presentation_key_absent(store)
    catalog = load_catalog(source, store, experiment_dir / CACHE_DIRNAME)
    presentations = build_presentation_table(catalog)
    result = upload_presentation(presentations, experiment_dir, store)
    print_presentation_summary(result)


def _run_engine(
    engine: EngineName,
    smoke: bool,
    presentations: pd.DataFrame,
    store: CampaignObjectStore,
) -> None:
    subset = smoke_presentations(presentations) if smoke else presentations
    ordered_ids, texts = _ordered_label_input(subset)
    paths = _feature_paths(engine, smoke)
    spec = separability_spec(engine.value)
    campaign = _campaign_config()
    run_id = run_id_for_feature(campaign.campaign_id, FEATURE_NAME)
    manifest, manifest_etag = _load_or_create_manifest(
        store,
        paths,
        campaign,
        spec,
        expected_row_count=len(ordered_ids),
        engine_type=_engine_type_value(engine),
    )
    if manifest.get("final_parquet"):
        print(FINAL_EXISTS_FORMAT.format(uri=paths.uri(paths.final_key)))
        return
    manifest_etag = _label_parts(
        engine, store, paths, manifest, manifest_etag, spec, campaign, ordered_ids, texts, run_id
    )
    consolidate_final(
        store,
        paths,
        manifest,
        manifest_etag,
        expected_ids=ordered_ids,
        failed_ids=read_failed_ids(store, paths),
        spec=spec,
        run_id=run_id,
    )
    _print_label_summary(store, paths, len(ordered_ids))


def _label_parts(
    engine: EngineName,
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    ordered_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    written_parts = {int(entry["part_index"]) for entry in manifest["batches"]}
    for part_index, chunk_ids in enumerate(_chunks(ordered_ids, campaign.batch_size)):
        if part_index in written_parts:
            continue
        manifest_etag = _label_one_part(
            engine,
            store,
            paths,
            manifest,
            manifest_etag,
            spec,
            part_index,
            chunk_ids,
            texts,
            run_id,
        )
    return manifest_etag


def _label_one_part(
    engine: EngineName,
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    part_index: int,
    chunk_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    adopted = adopt_unrecorded_batch(
        store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
    )
    if adopted is not None:
        return adopted.manifest_etag
    tasks = [LabelTask(uri=record_id, text=texts[record_id]) for record_id in chunk_ids]
    rows, failures = _label_tasks(engine, spec, tasks)
    manifest_etag = _write_part_rows(
        store, paths, manifest, manifest_etag, spec, part_index, chunk_ids, rows, run_id, engine
    )
    if failures:
        append_errors(store, paths, _error_records(failures, run_id, part_index))
    return manifest_etag


def _label_tasks(
    engine: EngineName, spec: FeatureSpec, tasks: list[LabelTask]
) -> tuple[list[dict], list[RecordLabelFailure]]:
    if engine is EngineName.OPENAI:
        return openai_runner.label_tasks(spec, tasks)
    return bedrock_runner.label_tasks(spec, tasks)


def _write_part_rows(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    part_index: int,
    chunk_ids: list[str],
    rows: list[dict],
    run_id: str,
    engine: EngineName,
) -> str:
    if not rows:
        return manifest_etag
    batch_id = _batch_id(part_index)
    request_ids = _request_ids(engine, chunk_ids)
    with_metadata = attach_row_metadata(
        rows,
        run_id=run_id,
        batch_id=batch_id,
        request_ids=request_ids,
        attempt_count=ATTEMPT_COUNT,
    )
    result = write_batch(
        store,
        paths,
        manifest,
        manifest_etag,
        part_index=part_index,
        rows=with_metadata,
        spec=spec,
        run_id=run_id,
    )
    return result.manifest_etag


def _ordered_label_input(presentations: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    ordered = presentations.sort_values(ID_COLUMN, kind=SORT_KIND)
    ids = ordered[ID_COLUMN].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate source_record_id")
    texts = dict(zip(ids, ordered[PROMPT_TEXT_COLUMN].astype(str), strict=True))
    return ids, texts


def _load_or_create_manifest(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    campaign: CampaignRunConfig,
    spec: FeatureSpec,
    *,
    expected_row_count: int,
    engine_type: str,
) -> tuple[dict[str, Any], str]:
    fresh = new_manifest(
        campaign=campaign,
        spec=spec,
        expected_row_count=expected_row_count,
        engine_type=engine_type,
    )
    manifest, etag = load_manifest(store, paths)
    if manifest is None or etag is None:
        return fresh, save_manifest(store, paths, fresh, None)
    mismatched = _manifest_identity_mismatches(manifest, fresh)
    if mismatched:
        raise ValueError(
            f"manifest at {paths.uri(paths.manifest_key)} does not match this run on {mismatched}"
        )
    return manifest, etag


def _manifest_identity_mismatches(manifest: dict[str, Any], fresh: dict[str, Any]) -> list[str]:
    mismatched: list[str] = []
    for field in MANIFEST_IDENTITY_FIELDS:
        existing = manifest.get(field)
        if field == ENGINE_TYPE_FIELD and existing is None:
            existing = OPENAI_ENGINE_TYPE
        if existing != fresh[field]:
            mismatched.append(field)
    return mismatched


def _chunks(ids: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(ids), size):
        yield ids[start : start + size]


def _feature_paths(engine: EngineName, smoke: bool) -> FeaturePaths:
    if smoke:
        root = OPENAI_SMOKE_ROOT_URI if engine is EngineName.OPENAI else BEDROCK_SMOKE_ROOT_URI
        return FeaturePaths.from_root_uri(root, SMOKE_FEATURE_NAME)
    return FeaturePaths.from_root_uri(LABELS_ROOT_URI, engine.value)


def _engine_type_value(engine: EngineName) -> str:
    if engine is EngineName.BEDROCK:
        return BEDROCK_ENGINE_TYPE
    return OPENAI_ENGINE_TYPE


def _batch_id(part_index: int) -> str:
    return f"{BATCH_ID_PREFIX}{part_index:0{PART_INDEX_WIDTH}d}"


def _request_ids(engine: EngineName, chunk_ids: list[str]) -> dict[str, str]:
    prefix = f"{engine.value}{REQUEST_ID_SEPARATOR}"
    return {record_id: f"{prefix}{record_id}" for record_id in chunk_ids}


def _error_records(
    failures: list[RecordLabelFailure], run_id: str, part_index: int
) -> list[dict[str, Any]]:
    timestamp = get_current_timestamp()
    return [
        {
            "ts": timestamp,
            "run_id": run_id,
            "part_index": part_index,
            "source_record_id": failure.source_record_id,
            "error": failure.error,
            "attempts": failure.attempts,
        }
        for failure in failures
    ]


def _print_label_summary(
    store: CampaignObjectStore, paths: FeaturePaths, expected: int
) -> None:
    failed_ids = read_failed_ids(store, paths)
    labeled = expected - len(failed_ids)
    print(LABELED_SUMMARY_FORMAT.format(labeled=labeled, expected=expected))
    print(FAILED_SUMMARY_FORMAT.format(failed=len(failed_ids)))


def _experiment_dir() -> Path:
    return REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME


def _campaign_config() -> CampaignRunConfig:
    return CampaignRunConfig(
        campaign_id=CAMPAIGN_ID,
        dataset_id=DATASET_ID,
        preprocessed_run=PREPROCESSED_RUN,
        platform=CAMPAIGN_PLATFORM,
        batch_size=campaign_batch_size(),
    )


if __name__ == "__main__":
    try:
        app()
    except (FileExistsError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from error
