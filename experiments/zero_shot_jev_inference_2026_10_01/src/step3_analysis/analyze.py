"""Compare a complete Jev run with Study 2 human labels.

Issue 326 supplies dataset splits, label counts, split-vote counts, and the
per-dataset confusion metrics. This module loads the Jev run, checks those
counts against the fixed Study 2 totals, and writes the analysis bundle.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --run-id RUN_ID
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from pydantic import BaseModel, ConfigDict, Field

from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import (
    INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY,
    JEV_MODEL,
    S3_BUCKET,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.schemas import JevRunManifest
from experiments.zero_shot_jev_inference_2026_10_01.shared.storage import (
    build_analysis_prefix,
    build_manifests_prefix,
    build_predictions_prefix,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    InputManifest,
    ModelRunManifestStatus,
    PredictionRecord,
    Study2InputRecord,
    validate_prediction_record_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    load_json_objects_under_prefix,
    load_jsonl_records_under_prefix,
    parse_study2_input_jsonl_bytes,
    put_immutable_object,
    serialize_json_document,
    sha256_hex,
    validate_path_segment,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    AnalysisDataset,
    LabelCountRow,
    LabelName,
    ModelMetricRow,
    SplitRemoveVoteCountRow,
    build_label_counts,
    build_model_metric_row,
    build_split_remove_vote_counts,
    partition_prepared_records,
    validate_prepared_partitions,
)
from shared.models.jev.constants import (
    JEV_USD_PER_MILLION_INPUT,
    JEV_USD_PER_MILLION_OUTPUT,
)

from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.render import (
    UsageRow,
    render_results_fragment,
)

_JSON_SUFFIX = ".json"
_LABEL_COUNTS_NAME = "label_counts.csv"
_SPLIT_VOTES_NAME = "split_remove_vote_counts.csv"
_METRICS_NAME = "model_metrics.csv"
_USAGE_NAME = "usage.csv"
_FRAGMENT_NAME = "results_fragment.md"
_MANIFEST_NAME = "analysis_manifest.json"
_USD_DECIMAL_PLACES = 6
_PINNED_LABEL_COUNTS = {
    (AnalysisDataset.ALL, LabelName.KEEP): 11024,
    (AnalysisDataset.ALL, LabelName.REMOVE): 2968,
    (AnalysisDataset.UNANIMOUS, LabelName.KEEP): 3743,
    (AnalysisDataset.UNANIMOUS, LabelName.REMOVE): 308,
    (AnalysisDataset.SPLIT, LabelName.KEEP): 7281,
    (AnalysisDataset.SPLIT, LabelName.REMOVE): 2660,
}
_PINNED_SPLIT_VOTES = {1: 4244, 2: 3037, 3: 1777, 4: 883}
_DATASET_ORDER = (
    AnalysisDataset.ALL,
    AnalysisDataset.UNANIMOUS,
    AnalysisDataset.SPLIT,
)


@dataclass(frozen=True)
class AnalysisTables:
    """Tables written into the analysis bundle."""

    label_counts: tuple[LabelCountRow, ...]
    split_votes: tuple[SplitRemoveVoteCountRow, ...]
    metrics: tuple[ModelMetricRow, ...]
    usage: UsageRow


class JevAnalysisManifest(BaseModel):
    """Immutable description of one Jev analysis bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    prepared_input_records_sha256: str = Field(min_length=1)
    final_run_manifest_key: str = Field(min_length=1)
    input_row_count: int = Field(ge=0)
    unanimous_row_count: int = Field(ge=0)
    split_row_count: int = Field(ge=0)
    label_counts_sha256: str = Field(min_length=1)
    split_remove_vote_counts_sha256: str = Field(min_length=1)
    model_metrics_sha256: str = Field(min_length=1)
    usage_sha256: str = Field(min_length=1)
    results_fragment_sha256: str = Field(min_length=1)
    label_count_rows: int = Field(ge=0)
    split_remove_vote_rows: int = Field(ge=0)
    metric_rows: int = Field(ge=0)
    usage_rows: int = Field(ge=0)


@dataclass(frozen=True)
class LoadedJevAnalysis:
    """Prepared input, predictions, and the latest run manifest."""

    run_id: str
    input_manifest: InputManifest
    records: tuple[Study2InputRecord, ...]
    predictions: tuple[PredictionRecord, ...]
    manifest_key: str
    manifest: JevRunManifest


def run_analysis(store: CampaignObjectStore, run_id: str) -> str:
    """Validate one complete run and write or verify the analysis bundle.

    Parameters
    ----------
    store
        Object store for the experiment bucket.
    run_id
        Safe run identifier.

    Returns
    -------
    str
        Analysis prefix for ``run_id``.

    Raises
    ------
    ValueError
        When the run is incomplete, the join fails, a pinned count differs,
        or an existing object does not match the new bytes.
    """
    validate_path_segment(run_id)
    loaded = _load_analysis_inputs(store, run_id)
    _reject_incomplete_run(loaded)
    tables = build_analysis_tables(loaded.records, loaded.predictions)
    _reject_pinned_count_mismatch(tables)
    fragment = render_results_fragment(
        tables.label_counts,
        tables.split_votes,
        tables.metrics,
        tables.usage,
    )
    prefix = build_analysis_prefix(run_id)
    _write_bundle(store, prefix, loaded, tables, fragment)
    _print_success(prefix, tables)
    return prefix


def build_analysis_tables(
    records: tuple[Study2InputRecord, ...],
    predictions: tuple[PredictionRecord, ...],
) -> AnalysisTables:
    """Calculate label, vote, metric, and usage tables for one joined run.

    Parameters
    ----------
    records
        Prepared rows in input order.
    predictions
        One prediction per prepared post. The stored Boolean is the label.

    Returns
    -------
    AnalysisTables
        Counts and metrics. The remove threshold is not applied again.
    """
    partitions = partition_prepared_records(records)
    labels = build_label_counts(partitions)
    votes = build_split_remove_vote_counts(partitions.split_rows)
    metrics = _metric_rows(partitions, predictions)
    usage = build_usage_row(predictions)
    return AnalysisTables(labels, votes, metrics, usage)


def build_usage_row(predictions: tuple[PredictionRecord, ...]) -> UsageRow:
    """Sum token counts and convert them to Jev's input-only price.

    Parameters
    ----------
    predictions
        Prediction rows whose usage fields are summed.

    Returns
    -------
    UsageRow
        Totals for one model. ``usd`` is rounded to six decimal places.
    """
    input_tokens = sum(row.usage.input_tokens for row in predictions)
    output_tokens = sum(row.usage.output_tokens for row in predictions)
    raw_usd = (
        input_tokens * JEV_USD_PER_MILLION_INPUT
        + output_tokens * JEV_USD_PER_MILLION_OUTPUT
    ) / 1_000_000
    return UsageRow(
        model=JEV_MODEL.folder_name,
        predictions=len(predictions),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usd=round(raw_usd, _USD_DECIMAL_PLACES),
    )


def main() -> None:
    """Parse the run id and write the analysis bundle."""
    args = _parse_args()
    try:
        validate_path_segment(args.run_id)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(S3_BUCKET)
    run_analysis(store, args.run_id)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one complete Jev Study 2 run.")
    parser.add_argument("--run-id", required=True, help="Safe run identifier segment")
    return parser.parse_args()


def _load_analysis_inputs(store: CampaignObjectStore, run_id: str) -> LoadedJevAnalysis:
    manifest_bytes = _required_bytes(store, INPUT_MANIFEST_KEY)
    records_bytes = _required_bytes(store, INPUT_RECORDS_KEY)
    input_manifest = InputManifest.model_validate_json(manifest_bytes)
    if sha256_hex(records_bytes) != input_manifest.records_sha256:
        raise ValueError("prepared input records digest mismatch")
    records = tuple(parse_study2_input_jsonl_bytes(records_bytes))
    manifest_key, run_manifest = _latest_run_manifest(store, run_id)
    predictions = _load_predictions(store, run_id, records)
    return LoadedJevAnalysis(
        run_id,
        input_manifest,
        records,
        predictions,
        manifest_key,
        run_manifest,
    )


def _required_bytes(store: CampaignObjectStore, key: str) -> bytes:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    return stored.body


def _latest_run_manifest(
    store: CampaignObjectStore,
    run_id: str,
) -> tuple[str, JevRunManifest]:
    loaded = load_json_objects_under_prefix(
        store,
        build_manifests_prefix(run_id),
        _JSON_SUFFIX,
        JevRunManifest,
    )
    if not loaded:
        raise ValueError("run has no manifest")
    key, manifest = loaded[-1]
    if manifest.run_id != run_id or manifest.model_folder != JEV_MODEL.folder_name:
        raise ValueError("latest manifest identity mismatch")
    return key, manifest


def _load_predictions(
    store: CampaignObjectStore,
    run_id: str,
    records: tuple[Study2InputRecord, ...],
) -> tuple[PredictionRecord, ...]:
    batches = load_jsonl_records_under_prefix(
        store,
        build_predictions_prefix(run_id),
        PredictionRecord,
    )
    known_ids = frozenset(record.post_id for record in records)
    rows: list[PredictionRecord] = []
    seen: set[str] = set()
    for _, batch in batches:
        for prediction in batch:
            validate_prediction_record_identity(
                prediction,
                run_id,
                JEV_MODEL.folder_name,
                JEV_MODEL.model_id,
                known_ids,
            )
            if prediction.post_id in seen:
                raise ValueError(f"duplicate prediction post_id: {prediction.post_id}")
            seen.add(prediction.post_id)
            rows.append(prediction)
    return tuple(rows)


def _reject_incomplete_run(loaded: LoadedJevAnalysis) -> None:
    if loaded.manifest.status is not ModelRunManifestStatus.COMPLETE:
        raise ValueError("latest manifest is not complete")
    if loaded.manifest.unresolved_failure_count != 0:
        raise ValueError("unresolved failures remain")
    prepared_ids = [record.post_id for record in loaded.records]
    predicted_ids = {row.post_id for row in loaded.predictions}
    missing = [post_id for post_id in prepared_ids if post_id not in predicted_ids]
    if missing:
        raise ValueError(f"missing prediction for {missing[0]}")
    if len(loaded.predictions) != len(prepared_ids):
        raise ValueError("prediction count does not match prepared input")


def _metric_rows(partitions, predictions: tuple[PredictionRecord, ...]) -> tuple[ModelMetricRow, ...]:
    by_post_id = {row.post_id: row.is_remove for row in predictions}
    dataset_rows = {
        AnalysisDataset.ALL: partitions.all_rows,
        AnalysisDataset.UNANIMOUS: partitions.unanimous_rows,
        AnalysisDataset.SPLIT: partitions.split_rows,
    }
    return tuple(
        build_model_metric_row(dataset, JEV_MODEL.folder_name, dataset_rows[dataset], by_post_id)
        for dataset in _DATASET_ORDER
    )


def _reject_pinned_count_mismatch(tables: AnalysisTables) -> None:
    for row in tables.label_counts:
        expected = _PINNED_LABEL_COUNTS[(row.dataset, row.label)]
        if row.count != expected:
            raise ValueError(f"pinned label count mismatch: {row.dataset.value} {row.label.value}")
    for row in tables.split_votes:
        if row.count != _PINNED_SPLIT_VOTES[row.remove_votes]:
            raise ValueError(f"pinned split vote mismatch: {row.remove_votes}")


def _write_bundle(
    store: CampaignObjectStore,
    prefix: str,
    loaded: LoadedJevAnalysis,
    tables: AnalysisTables,
    fragment: str,
) -> None:
    bodies = {
        prefix + _LABEL_COUNTS_NAME: _label_counts_csv(tables.label_counts),
        prefix + _SPLIT_VOTES_NAME: _split_votes_csv(tables.split_votes),
        prefix + _METRICS_NAME: _metrics_csv(tables.metrics),
        prefix + _USAGE_NAME: _usage_csv(tables.usage),
        prefix + _FRAGMENT_NAME: fragment.encode("utf-8"),
    }
    manifest = _analysis_manifest(loaded, tables, bodies, prefix)
    bodies[prefix + _MANIFEST_NAME] = serialize_json_document(manifest.model_dump(mode="json"))
    for key, body in bodies.items():
        _write_or_verify(store, key, body)


def _analysis_manifest(
    loaded: LoadedJevAnalysis,
    tables: AnalysisTables,
    bodies: dict[str, bytes],
    prefix: str,
) -> JevAnalysisManifest:
    partitions = partition_prepared_records(loaded.records)
    validate_prepared_partitions(partitions)
    return JevAnalysisManifest(
        run_id=loaded.run_id,
        prepared_input_records_sha256=loaded.input_manifest.records_sha256,
        final_run_manifest_key=loaded.manifest_key,
        input_row_count=len(partitions.all_rows),
        unanimous_row_count=len(partitions.unanimous_rows),
        split_row_count=len(partitions.split_rows),
        label_counts_sha256=sha256_hex(bodies[prefix + _LABEL_COUNTS_NAME]),
        split_remove_vote_counts_sha256=sha256_hex(bodies[prefix + _SPLIT_VOTES_NAME]),
        model_metrics_sha256=sha256_hex(bodies[prefix + _METRICS_NAME]),
        usage_sha256=sha256_hex(bodies[prefix + _USAGE_NAME]),
        results_fragment_sha256=sha256_hex(bodies[prefix + _FRAGMENT_NAME]),
        label_count_rows=len(tables.label_counts),
        split_remove_vote_rows=len(tables.split_votes),
        metric_rows=len(tables.metrics),
        usage_rows=1,
    )


def _write_or_verify(store: CampaignObjectStore, key: str, body: bytes) -> None:
    existing = store.get(key)
    digest = sha256_hex(body)
    if existing is None:
        put_immutable_object(store, key, body)
        return
    if sha256_hex(existing.body) != digest:
        raise ValueError(f"immutable object hash mismatch: {key}")


def _label_counts_csv(rows: tuple[LabelCountRow, ...]) -> bytes:
    return _csv_bytes(
        ["dataset", "label", "count", "dataset_total", "proportion"],
        [
            [row.dataset.value, row.label.value, row.count, row.dataset_total, row.proportion]
            for row in rows
        ],
    )


def _split_votes_csv(rows: tuple[SplitRemoveVoteCountRow, ...]) -> bytes:
    return _csv_bytes(
        ["remove_votes", "count", "split_total", "proportion"],
        [[row.remove_votes, row.count, row.split_total, row.proportion] for row in rows],
    )


def _metrics_csv(rows: tuple[ModelMetricRow, ...]) -> bytes:
    header = [
        "dataset",
        "model",
        "sample_count",
        "true_positive",
        "false_positive",
        "true_negative",
        "false_negative",
        "f1",
        "accuracy",
        "recall",
        "precision",
    ]
    body = [
        [
            row.dataset.value,
            row.model_folder,
            row.sample_count,
            row.true_positive,
            row.false_positive,
            row.true_negative,
            row.false_negative,
            row.f1,
            row.accuracy,
            row.recall,
            row.precision,
        ]
        for row in rows
    ]
    return _csv_bytes(header, body)


def _usage_csv(usage: UsageRow) -> bytes:
    return _csv_bytes(
        ["model", "predictions", "input_tokens", "output_tokens", "usd"],
        [[usage.model, usage.predictions, usage.input_tokens, usage.output_tokens, usage.usd]],
    )


def _csv_bytes(header: list[str], rows: list[list[object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _print_success(prefix: str, tables: AnalysisTables) -> None:
    totals = {
        row.dataset: row.dataset_total
        for row in tables.label_counts
        if row.label is LabelName.KEEP
    }
    print(
        f"analysis_prefix={prefix} input_rows={totals[AnalysisDataset.ALL]} "
        f"unanimous_rows={totals[AnalysisDataset.UNANIMOUS]} "
        f"split_rows={totals[AnalysisDataset.SPLIT]} models=1 "
        f"metric_rows={len(tables.metrics)} artifacts=6"
    )


if __name__ == "__main__":
    main()
