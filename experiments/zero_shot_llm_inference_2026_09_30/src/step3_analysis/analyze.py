"""Load inference outputs, calculate Study 2 metrics, and write analysis artifacts.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --run-id RUN_ID
"""

from __future__ import annotations

import argparse
import csv
import io
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from pydantic import BaseModel, ConfigDict, Field

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    FailureRecord,
    InputManifest,
    ModelDefinition,
    ModelRunManifest,
    ModelRunManifestStatus,
    PredictionRecord,
    Study2InputRecord,
    validate_model_run_manifest_identity,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPECTED_SPLIT_RECORD_COUNT,
    EXPECTED_TOTAL_RECORD_COUNT,
    EXPECTED_UNANIMOUS_RECORD_COUNT,
    EXPERIMENT_S3_BUCKET,
    MODEL_REGISTRY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    build_manifests_prefix,
    join_experiment_key,
    load_json_objects_under_prefix,
    load_verified_prepared_input,
    put_immutable_object,
    serialize_json_document,
    sha256_hex,
    validate_path_segment,
)
from experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run import (
    load_existing_run_artifacts,
    unresolved_failure_post_ids,
)

ANALYSIS_SCHEMA_VERSION = "study2-zero-shot-analysis-v1"
_ANALYSIS_SEGMENT = "analysis"
_LABEL_COUNTS_FILENAME = "label_counts.csv"
_SPLIT_REMOVE_VOTE_COUNTS_FILENAME = "split_remove_vote_counts.csv"
_MODEL_METRICS_FILENAME = "model_metrics.csv"
_RESULTS_FRAGMENT_FILENAME = "results_fragment.md"
_ANALYSIS_MANIFEST_FILENAME = "analysis_manifest.json"
_METRIC_DECIMAL_PLACES = 6
_SPLIT_REMOVE_VOTE_VALUES = (1, 2, 3, 4)


class AnalysisDataset(str, Enum):
    """Evaluation dataset partitions for Study 2 analysis."""

    ALL = "all"
    UNANIMOUS = "unanimous"
    SPLIT = "split"


_DATASET_ORDER: tuple[AnalysisDataset, ...] = (
    AnalysisDataset.ALL,
    AnalysisDataset.UNANIMOUS,
    AnalysisDataset.SPLIT,
)


class LabelName(str, Enum):
    """Human keep/remove labels."""

    KEEP = "keep"
    REMOVE = "remove"


_LABEL_ORDER: tuple[LabelName, ...] = (LabelName.KEEP, LabelName.REMOVE)


@dataclass(frozen=True)
class PreparedInputPartitions:
    """Prepared input rows partitioned by evaluation dataset."""

    all_rows: tuple[Study2InputRecord, ...]
    unanimous_rows: tuple[Study2InputRecord, ...]
    split_rows: tuple[Study2InputRecord, ...]


@dataclass(frozen=True)
class LabelCountRow:
    """One human label count row."""

    dataset: AnalysisDataset
    label: LabelName
    count: int
    dataset_total: int
    proportion: float


@dataclass(frozen=True)
class SplitRemoveVoteCountRow:
    """One split remove-vote count row."""

    remove_votes: int
    count: int
    split_total: int
    proportion: float


@dataclass(frozen=True)
class ConfusionCounts:
    """Confusion matrix counts with remove as the positive class."""

    sample_count: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int


@dataclass(frozen=True)
class ClassificationMetrics:
    """Classification metrics derived from one confusion matrix."""

    f1: float
    accuracy: float
    recall: float
    precision: float


@dataclass(frozen=True)
class ModelMetricRow:
    """One model metric row for one evaluation dataset."""

    dataset: AnalysisDataset
    model_folder: str
    sample_count: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    f1: float
    accuracy: float
    recall: float
    precision: float


@dataclass(frozen=True)
class AnalysisTables:
    """Completed machine-readable tables for one analysis run."""

    label_counts: tuple[LabelCountRow, ...]
    split_remove_vote_counts: tuple[SplitRemoveVoteCountRow, ...]
    model_metrics: tuple[ModelMetricRow, ...]


class ModelRunReference(BaseModel):
    """One completed model manifest referenced by the analysis bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_folder: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    manifest_s3_key: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=1)


class AnalysisManifest(BaseModel):
    """Immutable manifest describing one analysis bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    prepared_input_records_s3_key: str = Field(min_length=1)
    prepared_input_records_sha256: str = Field(min_length=1)
    prepared_input_manifest_schema_version: str = Field(min_length=1)
    input_row_count: int = Field(ge=0)
    unanimous_row_count: int = Field(ge=0)
    split_row_count: int = Field(ge=0)
    model_runs: tuple[ModelRunReference, ...]
    label_counts_s3_key: str = Field(min_length=1)
    split_remove_vote_counts_s3_key: str = Field(min_length=1)
    model_metrics_s3_key: str = Field(min_length=1)
    results_fragment_s3_key: str = Field(min_length=1)
    analysis_manifest_s3_key: str = Field(min_length=1)
    label_counts_sha256: str = Field(min_length=1)
    split_remove_vote_counts_sha256: str = Field(min_length=1)
    model_metrics_sha256: str = Field(min_length=1)
    results_fragment_sha256: str = Field(min_length=1)


@dataclass(frozen=True)
class LoadedModelRun:
    """Validated predictions and manifest for one model folder."""

    model_folder: str
    model_id: str
    manifest: ModelRunManifest
    manifest_s3_key: str
    manifest_sha256: str
    predictions: tuple[PredictionRecord, ...]


@dataclass(frozen=True)
class LoadedAnalysisRun:
    """Validated prepared input and model outputs for one run."""

    run_id: str
    input_manifest: InputManifest
    prepared_records: tuple[Study2InputRecord, ...]
    model_runs: tuple[LoadedModelRun, ...]


class ObjectStoreBoundary(Protocol):
    """Minimal store surface required by analysis IO."""

    def get(self, key: str) -> object | None: ...

    def put_new(self, key: str, body: bytes) -> None: ...

    def list_keys(self, prefix: str) -> list[str]: ...


def partition_prepared_records(
    records: tuple[Study2InputRecord, ...],
) -> PreparedInputPartitions:
    """Split prepared rows into all, unanimous, and split partitions."""
    unanimous = tuple(record for record in records if record.is_unanimous)
    split = tuple(record for record in records if not record.is_unanimous)
    return PreparedInputPartitions(
        all_rows=records,
        unanimous_rows=unanimous,
        split_rows=split,
    )


def validate_prepared_partitions(partitions: PreparedInputPartitions) -> None:
    """Reject prepared partitions whose counts differ from pinned totals."""
    _reject_partition_count(len(partitions.all_rows), EXPECTED_TOTAL_RECORD_COUNT, "all")
    _reject_partition_count(
        len(partitions.unanimous_rows),
        EXPECTED_UNANIMOUS_RECORD_COUNT,
        "unanimous",
    )
    _reject_partition_count(len(partitions.split_rows), EXPECTED_SPLIT_RECORD_COUNT, "split")


def _reject_partition_count(observed: int, expected: int, name: str) -> None:
    if observed != expected:
        raise ValueError(f"{name} partition count mismatch: {observed} != {expected}")


def build_label_counts(partitions: PreparedInputPartitions) -> tuple[LabelCountRow, ...]:
    """Build human label counts and proportions for each dataset."""
    rows: list[LabelCountRow] = []
    dataset_rows = (
        (AnalysisDataset.ALL, partitions.all_rows),
        (AnalysisDataset.UNANIMOUS, partitions.unanimous_rows),
        (AnalysisDataset.SPLIT, partitions.split_rows),
    )
    for dataset, partition in dataset_rows:
        rows.extend(_label_count_rows_for_partition(dataset, partition))
    return tuple(rows)


def _label_count_rows_for_partition(
    dataset: AnalysisDataset,
    rows: tuple[Study2InputRecord, ...],
) -> list[LabelCountRow]:
    dataset_total = len(rows)
    keep_count = sum(1 for row in rows if not row.gold_is_remove)
    remove_count = dataset_total - keep_count
    return [
        _label_count_row(dataset, LabelName.KEEP, keep_count, dataset_total),
        _label_count_row(dataset, LabelName.REMOVE, remove_count, dataset_total),
    ]


def _label_count_row(
    dataset: AnalysisDataset,
    label: LabelName,
    count: int,
    dataset_total: int,
) -> LabelCountRow:
    proportion = count / dataset_total if dataset_total else 0.0
    return LabelCountRow(dataset, label, count, dataset_total, proportion)


def build_split_remove_vote_counts(
    split_rows: tuple[Study2InputRecord, ...],
) -> tuple[SplitRemoveVoteCountRow, ...]:
    """Build split remove-vote counts and proportions for votes one through four."""
    split_total = len(split_rows)
    vote_counts = {vote: 0 for vote in _SPLIT_REMOVE_VOTE_VALUES}
    for row in split_rows:
        if row.n_remove not in vote_counts:
            raise ValueError(f"unexpected split remove votes: {row.n_remove}")
        vote_counts[row.n_remove] += 1
    return tuple(
        _split_remove_vote_row(vote, vote_counts[vote], split_total)
        for vote in _SPLIT_REMOVE_VOTE_VALUES
    )


def _split_remove_vote_row(
    remove_votes: int,
    count: int,
    split_total: int,
) -> SplitRemoveVoteCountRow:
    proportion = count / split_total if split_total else 0.0
    return SplitRemoveVoteCountRow(remove_votes, count, split_total, proportion)


def build_confusion_counts(
    rows: tuple[Study2InputRecord, ...],
    predictions_by_post_id: dict[str, bool],
) -> ConfusionCounts:
    """Build confusion counts for one dataset with remove as positive."""
    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0
    for row in rows:
        bucket = _confusion_bucket(row.gold_is_remove, predictions_by_post_id[row.post_id])
        if bucket == "tp":
            true_positive += 1
        elif bucket == "fp":
            false_positive += 1
        elif bucket == "tn":
            true_negative += 1
        else:
            false_negative += 1
    sample_count = len(rows)
    return ConfusionCounts(
        sample_count,
        true_positive,
        false_positive,
        true_negative,
        false_negative,
    )


def _confusion_bucket(actual_remove: bool, predicted_remove: bool) -> str:
    if predicted_remove and actual_remove:
        return "tp"
    if predicted_remove and not actual_remove:
        return "fp"
    if not predicted_remove and not actual_remove:
        return "tn"
    return "fn"


def build_classification_metrics(confusion: ConfusionCounts) -> ClassificationMetrics:
    """Derive F1, accuracy, recall, and precision from confusion counts."""
    precision = _safe_ratio(confusion.true_positive, confusion.true_positive + confusion.false_positive)
    recall = _safe_ratio(confusion.true_positive, confusion.true_positive + confusion.false_negative)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    accuracy = _safe_ratio(
        confusion.true_positive + confusion.true_negative,
        confusion.sample_count,
    )
    return ClassificationMetrics(f1=f1, accuracy=accuracy, recall=recall, precision=precision)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def build_model_metric_row(
    dataset: AnalysisDataset,
    model_folder: str,
    rows: tuple[Study2InputRecord, ...],
    predictions_by_post_id: dict[str, bool],
) -> ModelMetricRow:
    """Build one model metric row for one dataset partition."""
    confusion = build_confusion_counts(rows, predictions_by_post_id)
    metrics = build_classification_metrics(confusion)
    return ModelMetricRow(
        dataset=dataset,
        model_folder=model_folder,
        sample_count=confusion.sample_count,
        true_positive=confusion.true_positive,
        false_positive=confusion.false_positive,
        true_negative=confusion.true_negative,
        false_negative=confusion.false_negative,
        f1=metrics.f1,
        accuracy=metrics.accuracy,
        recall=metrics.recall,
        precision=metrics.precision,
    )


def build_model_metrics_table(
    partitions: PreparedInputPartitions,
    model_runs: tuple[LoadedModelRun, ...],
) -> tuple[ModelMetricRow, ...]:
    """Build the standardized twelve-row model metric table."""
    runs_by_folder = {run.model_folder: run for run in model_runs}
    rows: list[ModelMetricRow] = []
    partition_by_dataset = {
        AnalysisDataset.ALL: partitions.all_rows,
        AnalysisDataset.UNANIMOUS: partitions.unanimous_rows,
        AnalysisDataset.SPLIT: partitions.split_rows,
    }
    for dataset in _DATASET_ORDER:
        partition_rows = partition_by_dataset[dataset]
        for model in MODEL_REGISTRY:
            loaded = runs_by_folder[model.folder_name]
            predictions = _predictions_map(loaded.predictions)
            rows.append(
                build_model_metric_row(dataset, model.folder_name, partition_rows, predictions)
            )
    return tuple(rows)


def _predictions_map(predictions: tuple[PredictionRecord, ...]) -> dict[str, bool]:
    return {record.post_id: record.is_remove for record in predictions}


def load_run_inputs(store: CampaignObjectStore, run_id: str) -> LoadedAnalysisRun:
    """Load prepared input and four completed model outputs for one run."""
    safe_run_id = validate_path_segment(run_id)
    input_manifest, prepared_records = load_verified_prepared_input(store)
    prepared_post_ids = frozenset(record.post_id for record in prepared_records)
    expected_count = len(prepared_records)
    model_runs = _load_completed_model_runs(
        store,
        safe_run_id,
        input_manifest,
        prepared_records,
        prepared_post_ids,
        expected_count,
    )
    return LoadedAnalysisRun(safe_run_id, input_manifest, prepared_records, model_runs)


def validate_run_inputs(loaded: LoadedAnalysisRun) -> None:
    """Reject incomplete or mismatched inputs before calculation."""
    if len(loaded.model_runs) != len(MODEL_REGISTRY):
        raise ValueError("expected four completed model runs")
    partitions = partition_prepared_records(loaded.prepared_records)
    validate_prepared_partitions(partitions)
    for model_run in loaded.model_runs:
        _validate_model_run_predictions(model_run, loaded.prepared_records)


def _load_completed_model_runs(
    store: CampaignObjectStore,
    run_id: str,
    input_manifest: InputManifest,
    prepared_records: tuple[Study2InputRecord, ...],
    prepared_post_ids: frozenset[str],
    expected_count: int,
) -> tuple[LoadedModelRun, ...]:
    loaded_runs: list[LoadedModelRun] = []
    for model in MODEL_REGISTRY:
        loaded_runs.append(
            _load_one_completed_model_run(
                store,
                run_id,
                model,
                input_manifest,
                prepared_records,
                prepared_post_ids,
                expected_count,
            )
        )
    return tuple(loaded_runs)


def _load_one_completed_model_run(
    store: CampaignObjectStore,
    run_id: str,
    model: ModelDefinition,
    input_manifest: InputManifest,
    prepared_records: tuple[Study2InputRecord, ...],
    prepared_post_ids: frozenset[str],
    expected_count: int,
) -> LoadedModelRun:
    artifacts = load_existing_run_artifacts(
        store,
        run_id,
        model.folder_name,
        model.model_id,
        prepared_post_ids,
    )
    manifest_key, manifest, manifest_sha = _select_complete_manifest(
        store,
        run_id,
        model.folder_name,
        model.model_id,
        expected_count,
    )
    _validate_manifest_prepared_identity(manifest, input_manifest)
    _reject_unresolved_failures(artifacts.failures, artifacts.predictions, prepared_post_ids)
    _validate_prediction_coverage(artifacts.predictions, prepared_records)
    return LoadedModelRun(
        model_folder=model.folder_name,
        model_id=model.model_id,
        manifest=manifest,
        manifest_s3_key=manifest_key,
        manifest_sha256=manifest_sha,
        predictions=artifacts.predictions,
    )


def _select_complete_manifest(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    model_id: str,
    expected_count: int,
) -> tuple[str, ModelRunManifest, str]:
    entries = _load_manifest_entries(store, run_id, model_folder, model_id)
    complete = [
        entry
        for entry in entries
        if _manifest_is_complete(entry[1], expected_count)
    ]
    if not complete:
        raise ValueError(f"incomplete model run for folder: {model_folder}")
    return complete[-1]


def _load_manifest_entries(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    model_id: str,
) -> list[tuple[str, ModelRunManifest, str]]:
    prefix = build_manifests_prefix(run_id, model_folder)
    loaded = load_json_objects_under_prefix(store, prefix, ".json", ModelRunManifest)
    entries: list[tuple[str, ModelRunManifest, str]] = []
    for key, manifest in loaded:
        validate_model_run_manifest_identity(manifest, run_id, model_folder, model_id)
        stored = store.get(key)
        if stored is None:
            raise ValueError(f"missing manifest object: {key}")
        entries.append((key, manifest, sha256_hex(stored.body)))
    return entries


def _manifest_is_complete(manifest: ModelRunManifest, expected_count: int) -> bool:
    return (
        manifest.status is ModelRunManifestStatus.COMPLETE
        and manifest.configured_limit is None
        and manifest.requested_record_count == expected_count
        and manifest.completed_prediction_count == expected_count
        and manifest.unresolved_failure_count == 0
    )


def _validate_manifest_prepared_identity(
    manifest: ModelRunManifest,
    input_manifest: InputManifest,
) -> None:
    if manifest.prepared_input_records_key != input_manifest.records_s3_key:
        raise ValueError("prepared input records key mismatch")
    if manifest.prepared_input_records_sha256 != input_manifest.records_sha256:
        raise ValueError("prepared input records digest mismatch")


def _reject_unresolved_failures(
    failures: tuple[FailureRecord, ...],
    predictions: tuple[PredictionRecord, ...],
    prepared_post_ids: frozenset[str],
) -> None:
    unresolved = unresolved_failure_post_ids(failures, predictions, prepared_post_ids)
    if unresolved:
        raise ValueError("unresolved inference failures remain")


def _validate_prediction_coverage(
    predictions: tuple[PredictionRecord, ...],
    prepared_records: tuple[Study2InputRecord, ...],
) -> None:
    prediction_ids = {record.post_id for record in predictions}
    for record in prepared_records:
        if record.post_id not in prediction_ids:
            raise ValueError(f"missing prediction post_id: {record.post_id}")
    if len(predictions) != len(prepared_records):
        raise ValueError("prediction row count mismatch")


def _validate_model_run_predictions(
    model_run: LoadedModelRun,
    prepared_records: tuple[Study2InputRecord, ...],
) -> None:
    _validate_prediction_coverage(model_run.predictions, prepared_records)


def calculate_analysis_tables(loaded: LoadedAnalysisRun) -> AnalysisTables:
    """Build label, vote, and metric tables from validated inputs."""
    partitions = partition_prepared_records(loaded.prepared_records)
    validate_prepared_partitions(partitions)
    label_counts = build_label_counts(partitions)
    split_remove_vote_counts = build_split_remove_vote_counts(partitions.split_rows)
    model_metrics = build_model_metrics_table(partitions, loaded.model_runs)
    return AnalysisTables(label_counts, split_remove_vote_counts, model_metrics)


def write_analysis_bundle(
    store: CampaignObjectStore,
    loaded: LoadedAnalysisRun,
    tables: AnalysisTables,
    results_fragment: str,
) -> str:
    """Serialize tables and write the immutable analysis bundle."""
    prefix = build_analysis_prefix(loaded.run_id)
    bodies = _serialize_analysis_artifact_bodies(tables, results_fragment)
    keys = _analysis_artifact_keys(prefix)
    _write_or_verify_artifact(store, keys.label_counts, bodies.label_counts)
    _write_or_verify_artifact(store, keys.split_remove_vote_counts, bodies.split_remove_vote_counts)
    _write_or_verify_artifact(store, keys.model_metrics, bodies.model_metrics)
    _write_or_verify_artifact(store, keys.results_fragment, bodies.results_fragment)
    manifest = _build_analysis_manifest(loaded, keys, bodies)
    manifest_body = serialize_json_document(manifest.model_dump(mode="json"))
    _write_or_verify_artifact(store, keys.analysis_manifest, manifest_body)
    return build_analysis_prefix_uri(loaded.run_id)


def build_analysis_prefix(run_id: str) -> str:
    """Return the S3 key prefix for one analysis run."""
    safe_run_id = validate_path_segment(run_id)
    return join_experiment_key(_ANALYSIS_SEGMENT, safe_run_id) + "/"


def build_analysis_prefix_uri(run_id: str) -> str:
    """Return the S3 URI prefix for one analysis run."""
    return f"s3://{EXPERIMENT_S3_BUCKET}/{build_analysis_prefix(run_id)}"


def run_analysis(store: CampaignObjectStore, run_id: str) -> str:
    """Execute the full analysis pipeline and return the analysis prefix."""
    loaded = load_run_inputs(store, run_id)
    validate_run_inputs(loaded)
    tables = calculate_analysis_tables(loaded)
    from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.render import (
        render_results_fragment,
    )

    fragment = render_results_fragment(tables)
    return write_analysis_bundle(store, loaded, tables, fragment)


def main() -> None:
    """Run load, validate, calculate, render, and write for one run ID."""
    args = _parse_args()
    apply_lab_aws_credentials_when_unset()
    from data_platform.utils.object_store import DEFAULT_S3_REGION
    from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
        EXPERIMENT_S3_BUCKET,
    )

    store = CampaignObjectStore(EXPERIMENT_S3_BUCKET, DEFAULT_S3_REGION)
    prefix = run_analysis(store, args.run_id)
    _print_success_line(prefix, args.run_id)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one complete Study 2 zero-shot run.")
    parser.add_argument("--run-id", required=True, help="Safe run identifier segment")
    return parser.parse_args()


def _print_success_line(prefix: str, run_id: str) -> None:
    print(
        f"{prefix} input_rows={EXPECTED_TOTAL_RECORD_COUNT} "
        f"unanimous_rows={EXPECTED_UNANIMOUS_RECORD_COUNT} "
        f"split_rows={EXPECTED_SPLIT_RECORD_COUNT} models=4 metric_rows=12 artifacts=5"
    )


@dataclass(frozen=True)
class _AnalysisArtifactKeys:
    label_counts: str
    split_remove_vote_counts: str
    model_metrics: str
    results_fragment: str
    analysis_manifest: str


@dataclass(frozen=True)
class _SerializedAnalysisBodies:
    label_counts: bytes
    split_remove_vote_counts: bytes
    model_metrics: bytes
    results_fragment: bytes


def _analysis_artifact_keys(prefix: str) -> _AnalysisArtifactKeys:
    return _AnalysisArtifactKeys(
        label_counts=prefix + _LABEL_COUNTS_FILENAME,
        split_remove_vote_counts=prefix + _SPLIT_REMOVE_VOTE_COUNTS_FILENAME,
        model_metrics=prefix + _MODEL_METRICS_FILENAME,
        results_fragment=prefix + _RESULTS_FRAGMENT_FILENAME,
        analysis_manifest=prefix + _ANALYSIS_MANIFEST_FILENAME,
    )


def _serialize_analysis_artifact_bodies(
    tables: AnalysisTables,
    results_fragment: str,
) -> _SerializedAnalysisBodies:
    return _SerializedAnalysisBodies(
        label_counts=_serialize_label_counts_csv(tables.label_counts),
        split_remove_vote_counts=_serialize_split_remove_vote_counts_csv(
            tables.split_remove_vote_counts
        ),
        model_metrics=_serialize_model_metrics_csv(tables.model_metrics),
        results_fragment=results_fragment.encode("utf-8"),
    )


def _serialize_label_counts_csv(rows: tuple[LabelCountRow, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["dataset", "label", "count", "dataset_total", "proportion"])
    for row in rows:
        writer.writerow(
            [row.dataset.value, row.label.value, row.count, row.dataset_total, row.proportion]
        )
    return buffer.getvalue().encode("utf-8")


def _serialize_split_remove_vote_counts_csv(
    rows: tuple[SplitRemoveVoteCountRow, ...],
) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["remove_votes", "count", "split_total", "proportion"])
    for row in rows:
        writer.writerow([row.remove_votes, row.count, row.split_total, row.proportion])
    return buffer.getvalue().encode("utf-8")


def _serialize_model_metrics_csv(rows: tuple[ModelMetricRow, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
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
    )
    for row in rows:
        writer.writerow(
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
        )
    return buffer.getvalue().encode("utf-8")


def _write_or_verify_artifact(
    store: CampaignObjectStore,
    key: str,
    body: bytes,
) -> None:
    existing = store.get(key)
    digest = sha256_hex(body)
    if existing is None:
        put_immutable_object(store, key, body)
        return
    if sha256_hex(existing.body) != digest:
        raise ValueError(f"immutable object hash mismatch: {key}")


def _build_analysis_manifest(
    loaded: LoadedAnalysisRun,
    keys: _AnalysisArtifactKeys,
    bodies: _SerializedAnalysisBodies,
) -> AnalysisManifest:
    partitions = partition_prepared_records(loaded.prepared_records)
    return AnalysisManifest(
        schema_version=ANALYSIS_SCHEMA_VERSION,
        run_id=loaded.run_id,
        prepared_input_records_s3_key=loaded.input_manifest.records_s3_key,
        prepared_input_records_sha256=loaded.input_manifest.records_sha256,
        prepared_input_manifest_schema_version=loaded.input_manifest.schema_version,
        input_row_count=len(loaded.prepared_records),
        unanimous_row_count=len(partitions.unanimous_rows),
        split_row_count=len(partitions.split_rows),
        model_runs=_model_run_references(loaded.model_runs),
        label_counts_s3_key=keys.label_counts,
        split_remove_vote_counts_s3_key=keys.split_remove_vote_counts,
        model_metrics_s3_key=keys.model_metrics,
        results_fragment_s3_key=keys.results_fragment,
        analysis_manifest_s3_key=keys.analysis_manifest,
        label_counts_sha256=sha256_hex(bodies.label_counts),
        split_remove_vote_counts_sha256=sha256_hex(bodies.split_remove_vote_counts),
        model_metrics_sha256=sha256_hex(bodies.model_metrics),
        results_fragment_sha256=sha256_hex(bodies.results_fragment),
    )


def _model_run_references(
    model_runs: tuple[LoadedModelRun, ...],
) -> tuple[ModelRunReference, ...]:
    return tuple(
        ModelRunReference(
            model_folder=run.model_folder,
            model_id=run.model_id,
            manifest_s3_key=run.manifest_s3_key,
            manifest_sha256=run.manifest_sha256,
        )
        for run in model_runs
    )


if __name__ == "__main__":
    main()
