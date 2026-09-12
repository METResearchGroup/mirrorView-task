"""Scoring helpers for experiments 1 through 4."""

from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import mean

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    read_failed_ids,
    s3_uri,
)
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
    EXPERIMENT_S3_PREFIX,
    OUTPUT_S3_BUCKET,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import MODEL_ORDER
from experiments.ai_simulation_responses_2026_09_11.shared.schema import expand_remove_indexes
from experiments.ai_simulation_responses_2026_09_11.shared.write import put_new_mirrored

PARTY_GROUPS = ("democrat", "republican")
STANCE_VALUES = ("left", "right")
TOXICITY_VALUES = (
    "sample_low_toxicity",
    "sample_middle_toxicity",
    "sample_high_toxicity",
)
@dataclass(frozen=True)
class MetricBundle:
    """Accuracy, precision, recall, and F1 for one slice."""

    accuracy: float
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class PooledMetricBundle(MetricBundle):
    """Pooled metrics plus baseline remove rate."""

    baseline_remove_rate: float


@dataclass(frozen=True)
class UserScoreRow:
    """One user's gold and predicted labels."""

    prolific_id: str
    party_group: str
    gold: tuple[int, ...]
    pred: tuple[int, ...]


@dataclass(frozen=True)
class TrialScoreRow:
    """One trial's gold and predicted labels."""

    prolific_id: str
    sampled_stance: str
    sample_toxicity_type: str
    gold: int
    pred: int


@dataclass(frozen=True)
class ModelScoreResult:
    """Scored metrics for one model."""

    model: str
    scored_users: int
    failed_users: int
    user_level: MetricBundle
    scored_pairs: int
    post_level: PooledMetricBundle
    party: dict[str, tuple[int, MetricBundle]]
    toxicity: dict[str, tuple[int, PooledMetricBundle]]
    stance: dict[str, tuple[int, PooledMetricBundle]]


@dataclass(frozen=True)
class ExperimentScoreResult:
    """Scored metrics for one experiment."""

    experiment_number: int
    cohort_user_rows: int
    unique_prolific_ids: int
    duplicate_prolific_ids: tuple[str, ...]
    models: tuple[ModelScoreResult, ...]


def user_metrics(gold: list[int], pred: list[int]) -> MetricBundle:
    """Return user-level metrics with remove as the positive class."""
    return MetricBundle(
        accuracy=float(accuracy_score(gold, pred)),
        precision=float(precision_score(gold, pred, zero_division=0)),
        recall=float(recall_score(gold, pred, zero_division=0)),
        f1=float(f1_score(gold, pred, zero_division=0)),
    )


def pooled_metrics(gold: list[int], pred: list[int]) -> PooledMetricBundle:
    """Return pooled metrics plus baseline remove rate."""
    metrics = user_metrics(gold, pred)
    return PooledMetricBundle(
        accuracy=metrics.accuracy,
        precision=metrics.precision,
        recall=metrics.recall,
        f1=metrics.f1,
        baseline_remove_rate=float(sum(gold) / len(gold)),
    )


def mean_user_metrics(user_rows: list[UserScoreRow]) -> MetricBundle:
    """Return the mean of per-user metrics."""
    if not user_rows:
        return _zero_metrics()
    per_user = [user_metrics(list(row.gold), list(row.pred)) for row in user_rows]
    return MetricBundle(
        accuracy=float(mean(metric.accuracy for metric in per_user)),
        precision=float(mean(metric.precision for metric in per_user)),
        recall=float(mean(metric.recall for metric in per_user)),
        f1=float(mean(metric.f1 for metric in per_user)),
    )


def slice_tables(
    user_rows: list[UserScoreRow],
    trial_rows: list[TrialScoreRow],
) -> dict[str, dict[str, MetricBundle | PooledMetricBundle]]:
    """Build party, toxicity, and stance metric tables."""
    return {
        "party": _party_table(user_rows),
        "toxicity": _trial_table(trial_rows, "sample_toxicity_type", TOXICITY_VALUES),
        "stance": _trial_table(trial_rows, "sampled_stance", STANCE_VALUES),
    }


def score_experiment(
    experiment_number: int,
    all_users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> ExperimentScoreResult:
    """Score all four models for one experiment."""
    users = _deduplicate_users(all_users)
    gold_by_user = _gold_by_user(trials_by_user)
    model_results = tuple(
        _score_model(
            experiment_number,
            model_folder,
            users,
            gold_by_user,
            trials_by_user,
            store,
        )
        for model_folder in MODEL_ORDER
    )
    return ExperimentScoreResult(
        experiment_number=experiment_number,
        cohort_user_rows=len(all_users),
        unique_prolific_ids=len(users),
        duplicate_prolific_ids=_duplicate_prolific_ids(all_users),
        models=model_results,
    )


def write_results_md(
    result: ExperimentScoreResult,
    store: CampaignObjectStore,
) -> str:
    """Write RESULTS.md locally and on S3, then return the S3 URI."""
    relative_path = (
        f"{EXPERIMENT_S3_PREFIX}experiment{result.experiment_number}/RESULTS.md"
    )
    markdown = _results_markdown(result)
    put_new_mirrored(store, relative_path, markdown.encode("utf-8"))
    return s3_uri(OUTPUT_S3_BUCKET, relative_path)


def print_score_tables(result: ExperimentScoreResult) -> None:
    """Print user-level and post-level tables to stdout."""
    print(_user_level_table(result))
    print()
    print(_post_level_table(result))


def _score_model(
    experiment_number: int,
    model_folder: str,
    users: tuple[CohortUser, ...],
    gold_by_user: dict[str, list[int]],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> ModelScoreResult:
    paths = _full_feature_paths(experiment_number, model_folder)
    labels = _load_final_labels(store, paths)
    failed_ids = read_failed_ids(store, paths)
    predictions = _prediction_by_user(labels)
    user_rows: list[UserScoreRow] = []
    trial_rows: list[TrialScoreRow] = []
    failed_users = 0
    for user in users:
        prolific_id = user.prolific_id
        if prolific_id in failed_ids:
            failed_users += 1
            continue
        if prolific_id not in predictions:
            failed_users += 1
            continue
        try:
            pred = tuple(expand_remove_indexes(predictions[prolific_id]))
        except ValueError:
            failed_users += 1
            continue
        gold = tuple(gold_by_user[prolific_id])
        user_rows.append(
            UserScoreRow(
                prolific_id=prolific_id,
                party_group=user.party_group,
                gold=gold,
                pred=pred,
            )
        )
        trial_rows.extend(
            _trial_score_rows(user.prolific_id, trials_by_user[prolific_id], pred)
        )
    slices = slice_tables(user_rows, trial_rows)
    pooled_gold = [value for row in user_rows for value in row.gold]
    pooled_pred = [value for row in user_rows for value in row.pred]
    return ModelScoreResult(
        model=model_folder,
        scored_users=len(user_rows),
        failed_users=failed_users,
        user_level=mean_user_metrics(user_rows),
        scored_pairs=len(trial_rows),
        post_level=pooled_metrics(pooled_gold, pooled_pred) if pooled_gold else _zero_pooled_metrics(),
        party=_party_counts(user_rows, slices["party"]),
        toxicity=_trial_counts(
            trial_rows,
            slices["toxicity"],
            TOXICITY_VALUES,
            "sample_toxicity_type",
        ),
        stance=_trial_counts(
            trial_rows,
            slices["stance"],
            STANCE_VALUES,
            "sampled_stance",
        ),
    )


def _gold_by_user(trials_by_user: dict[str, list[CohortTrial]]) -> dict[str, list[int]]:
    gold_by_user: dict[str, list[int]] = {}
    for prolific_id, trials in trials_by_user.items():
        ordered = sorted(trials, key=lambda trial: trial.trial_index)
        gold_by_user[prolific_id] = [trial.gold_remove for trial in ordered]
    return gold_by_user


def _trial_score_rows(
    prolific_id: str,
    trials: list[CohortTrial],
    pred: tuple[int, ...],
) -> list[TrialScoreRow]:
    ordered = sorted(trials, key=lambda trial: trial.trial_index)
    rows: list[TrialScoreRow] = []
    for trial in ordered:
        pair_index = trial.pair_index - 1
        rows.append(
            TrialScoreRow(
                prolific_id=prolific_id,
                sampled_stance=trial.sampled_stance,
                sample_toxicity_type=trial.sample_toxicity_type,
                gold=trial.gold_remove,
                pred=pred[pair_index],
            )
        )
    return rows


def _load_final_labels(store: CampaignObjectStore, paths: FeaturePaths) -> pd.DataFrame:
    stored = store.get(paths.final_key)
    if stored is None:
        raise FileNotFoundError(paths.uri(paths.final_key))
    return pd.read_parquet(io.BytesIO(stored.body))


def _prediction_by_user(labels: pd.DataFrame) -> dict[str, list[int]]:
    predictions: dict[str, list[int]] = {}
    for row in labels.to_dict(orient="records"):
        prolific_id = str(row["source_record_id"])
        remove_indexes = row["remove_pair_indexes"]
        if remove_indexes is None:
            remove_indexes = []
        predictions[prolific_id] = list(remove_indexes)
    return predictions


def _full_feature_paths(experiment_number: int, model_folder: str) -> FeaturePaths:
    root_uri = (
        f"s3://{OUTPUT_S3_BUCKET}/{EXPERIMENT_S3_PREFIX}"
        f"experiment{experiment_number}/outputs/"
    )
    return FeaturePaths.from_root_uri(root_uri, model_folder)


def _deduplicate_users(users: tuple[CohortUser, ...]) -> tuple[CohortUser, ...]:
    ordered = sorted(users, key=lambda user: (user.source_file_epoch_ms, user.prolific_id))
    seen: set[str] = set()
    unique: list[CohortUser] = []
    for user in ordered:
        if user.prolific_id in seen:
            continue
        seen.add(user.prolific_id)
        unique.append(user)
    return tuple(unique)


def _duplicate_prolific_ids(users: tuple[CohortUser, ...]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for user in users:
        counts[user.prolific_id] = counts.get(user.prolific_id, 0) + 1
    return tuple(
        prolific_id
        for prolific_id in sorted(counts)
        if counts[prolific_id] > 1
    )


def _party_table(user_rows: list[UserScoreRow]) -> dict[str, MetricBundle]:
    table: dict[str, MetricBundle] = {}
    for party in PARTY_GROUPS:
        rows = [row for row in user_rows if row.party_group == party]
        table[party] = mean_user_metrics(rows)
    return table


def _trial_table(
    trial_rows: list[TrialScoreRow],
    field_name: str,
    values: tuple[str, ...],
) -> dict[str, PooledMetricBundle]:
    table: dict[str, PooledMetricBundle] = {}
    for value in values:
        rows = [row for row in trial_rows if getattr(row, field_name) == value]
        gold = [row.gold for row in rows]
        pred = [row.pred for row in rows]
        table[value] = pooled_metrics(gold, pred) if gold else _zero_pooled_metrics()
    return table


def _party_counts(
    user_rows: list[UserScoreRow],
    table: dict[str, MetricBundle],
) -> dict[str, tuple[int, MetricBundle]]:
    counts: dict[str, tuple[int, MetricBundle]] = {}
    for party in PARTY_GROUPS:
        scored_users = sum(1 for row in user_rows if row.party_group == party)
        counts[party] = (scored_users, table[party])
    return counts


def _trial_counts(
    trial_rows: list[TrialScoreRow],
    table: dict[str, PooledMetricBundle],
    values: tuple[str, ...],
    field_name: str,
) -> dict[str, tuple[int, PooledMetricBundle]]:
    counts: dict[str, tuple[int, PooledMetricBundle]] = {}
    for value in values:
        scored_pairs = sum(
            1 for row in trial_rows if getattr(row, field_name) == value
        )
        counts[value] = (scored_pairs, table[value])
    return counts


def _results_markdown(result: ExperimentScoreResult) -> str:
    duplicate_text = ", ".join(result.duplicate_prolific_ids) or "none"
    lines = [
        f"# Experiment {result.experiment_number} results",
        "",
        "## Cohort",
        "",
        (
            f"{result.unique_prolific_ids} unique prolific_ids from "
            f"{result.cohort_user_rows} cohort user rows. "
            f"Duplicate prolific_ids: {duplicate_text}."
        ),
        "",
        "## User-level",
        "",
        _user_level_table(result),
        "",
        *_model_count_lines(result, "scored_users"),
        "",
        "## Post-level",
        "",
        _post_level_table(result),
        "",
        *_model_count_lines(result, "scored_pairs"),
        "",
    ]
    lines.extend(_party_sections(result))
    lines.extend(_trial_sections(result, "toxicity", TOXICITY_VALUES))
    lines.extend(_trial_sections(result, "stance", STANCE_VALUES))
    return "\n".join(lines).rstrip() + "\n"


def _user_level_table(result: ExperimentScoreResult) -> str:
    header = (
        "| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    rows = [
        _metric_row(
            model.model,
            model.scored_users,
            model.user_level,
            include_baseline=False,
        )
        for model in result.models
    ]
    return "\n".join([header, separator, *rows])


def _post_level_table(result: ExperimentScoreResult) -> str:
    header = (
        "| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    rows = [
        _pooled_row(model.model, model.scored_pairs, model.post_level)
        for model in result.models
    ]
    return "\n".join([header, separator, *rows])


def _party_sections(result: ExperimentScoreResult) -> list[str]:
    lines: list[str] = []
    for party in PARTY_GROUPS:
        lines.extend(
            [
                f"## Party: party_group={party}",
                "",
                _party_table_markdown(result, party),
                "",
                *_party_count_lines(result, party),
                "",
            ]
        )
    return lines


def _party_table_markdown(result: ExperimentScoreResult, party: str) -> str:
    header = (
        "| model | n_users | mean accuracy | mean precision | mean recall | mean F1 |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    rows = [
        _metric_row(
            model.model,
            model.party[party][0],
            model.party[party][1],
            include_baseline=False,
        )
        for model in result.models
    ]
    return "\n".join([header, separator, *rows])


def _trial_sections(
    result: ExperimentScoreResult,
    section_name: str,
    values: tuple[str, ...],
) -> list[str]:
    lines: list[str] = []
    table_attr = section_name
    for value in values:
        lines.extend(
            [
                f"## {section_name.title()}: {value}",
                "",
                _trial_table_markdown(result, table_attr, value),
                "",
                *_trial_count_lines(result, table_attr, value),
                "",
            ]
        )
    return lines


def _trial_table_markdown(
    result: ExperimentScoreResult,
    table_attr: str,
    value: str,
) -> str:
    header = (
        "| model | n_pairs | baseline remove rate | accuracy | precision | recall | F1 |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    rows = []
    for model in result.models:
        table = getattr(model, table_attr)
        scored_pairs, metrics = table[value]
        rows.append(_pooled_row(model.model, scored_pairs, metrics))
    return "\n".join([header, separator, *rows])


def _metric_row(
    model: str,
    count: int,
    metrics: MetricBundle,
    *,
    include_baseline: bool,
) -> str:
    if include_baseline:
        raise ValueError("baseline is only for pooled rows")
    return (
        f"| {model} | {count} | "
        f"{metrics.accuracy:.4f} | {metrics.precision:.4f} | "
        f"{metrics.recall:.4f} | {metrics.f1:.4f} |"
    )


def _pooled_row(model: str, count: int, metrics: PooledMetricBundle) -> str:
    return (
        f"| {model} | {count} | {metrics.baseline_remove_rate:.4f} | "
        f"{metrics.accuracy:.4f} | {metrics.precision:.4f} | "
        f"{metrics.recall:.4f} | {metrics.f1:.4f} |"
    )


def _model_count_lines(result: ExperimentScoreResult, count_name: str) -> list[str]:
    lines: list[str] = []
    for model in result.models:
        count = model.scored_users if count_name == "scored_users" else model.scored_pairs
        lines.append(
            f"{count_name} {model.model}={count} failed_users={model.failed_users}"
        )
    return lines


def _party_count_lines(result: ExperimentScoreResult, party: str) -> list[str]:
    lines: list[str] = []
    for model in result.models:
        scored_users, _ = model.party[party]
        lines.append(
            f"scored_users {model.model}={scored_users} failed_users={model.failed_users}"
        )
    return lines


def _trial_count_lines(
    result: ExperimentScoreResult,
    table_attr: str,
    value: str,
) -> list[str]:
    lines: list[str] = []
    for model in result.models:
        table = getattr(model, table_attr)
        scored_pairs, _ = table[value]
        lines.append(
            f"scored_pairs {model.model}={scored_pairs} failed_users={model.failed_users}"
        )
    return lines


def _zero_metrics() -> MetricBundle:
    return MetricBundle(accuracy=0.0, precision=0.0, recall=0.0, f1=0.0)


def _zero_pooled_metrics() -> PooledMetricBundle:
    return PooledMetricBundle(
        accuracy=0.0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        baseline_remove_rate=0.0,
    )
