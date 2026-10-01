"""Load inference outputs, calculate Study 2 metrics, and write analysis artifacts.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --run-id RUN_ID
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from pydantic import BaseModel, ConfigDict, Field

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    InputManifest,
    ModelRunManifest,
    PredictionRecord,
    Study2InputRecord,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPECTED_SPLIT_RECORD_COUNT,
    EXPECTED_TOTAL_RECORD_COUNT,
    EXPECTED_UNANIMOUS_RECORD_COUNT,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    validate_path_segment,
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
    raise NotImplementedError


def build_classification_metrics(confusion: ConfusionCounts) -> ClassificationMetrics:
    """Derive F1, accuracy, recall, and precision from confusion counts."""
    raise NotImplementedError


def build_model_metric_row(
    dataset: AnalysisDataset,
    model_folder: str,
    rows: tuple[Study2InputRecord, ...],
    predictions_by_post_id: dict[str, bool],
) -> ModelMetricRow:
    """Build one model metric row for one dataset partition."""
    raise NotImplementedError


def build_model_metrics_table(
    partitions: PreparedInputPartitions,
    model_runs: tuple[LoadedModelRun, ...],
) -> tuple[ModelMetricRow, ...]:
    """Build the standardized twelve-row model metric table."""
    raise NotImplementedError


def load_run_inputs(store: CampaignObjectStore, run_id: str) -> LoadedAnalysisRun:
    """Load prepared input and four completed model outputs for one run."""
    raise NotImplementedError


def validate_run_inputs(loaded: LoadedAnalysisRun) -> None:
    """Reject incomplete or mismatched inputs before calculation."""
    raise NotImplementedError


def calculate_analysis_tables(loaded: LoadedAnalysisRun) -> AnalysisTables:
    """Build label, vote, and metric tables from validated inputs."""
    raise NotImplementedError


def write_analysis_bundle(
    store: CampaignObjectStore,
    loaded: LoadedAnalysisRun,
    tables: AnalysisTables,
    results_fragment: str,
) -> str:
    """Serialize tables and write the immutable analysis bundle."""
    raise NotImplementedError


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
    raise NotImplementedError


if __name__ == "__main__":
    main()
