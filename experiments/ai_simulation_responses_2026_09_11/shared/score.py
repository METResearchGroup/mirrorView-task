"""Scoring helpers for experiments 1 through 4."""

from __future__ import annotations

import io
import statistics
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
    EXPERIMENT6_MODEL_ORDER,
    EXPERIMENT_S3_PREFIX,
    OUTPUT_S3_BUCKET,
    POSTS_PER_USER,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import MODEL_ORDER
from experiments.ai_simulation_responses_2026_09_11.shared.schema import (
    expand_remove_indexes,
    parse_pair_record_id,
    stitch_pair_predictions,
)
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
    """Pooled metrics plus baseline and predicted remove rates."""

    baseline_remove_rate: float
    predicted_remove_rate: float


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
    user_rows: tuple[UserScoreRow, ...]


@dataclass(frozen=True)
class ExperimentScoreResult:
    """Scored metrics for one experiment."""

    experiment_number: int
    cohort_user_rows: int
    unique_prolific_ids: int
    duplicate_prolific_ids: tuple[str, ...]
    models: tuple[ModelScoreResult, ...]


@dataclass(frozen=True)
class CompareRow:
    """Experiment 6 vs experiment 1 metrics on the shared scored users."""

    model: str
    n_users: int
    exp1_user_f1: float
    exp6_user_f1: float
    exp1_post_f1: float
    exp6_post_f1: float
    exp1_accuracy: float
    exp6_accuracy: float
    exp1_precision: float
    exp6_precision: float
    exp1_recall: float
    exp6_recall: float
    exp1_predicted_remove_rate: float
    exp6_predicted_remove_rate: float
    gold_remove_rate: float
    agreement_rate: float


@dataclass(frozen=True)
class VarianceRow:
    """Within-user variance of per-pair correctness for one model and experiment."""

    model: str
    experiment_number: int
    mean: float
    median: float
    p25: float
    p75: float


@dataclass(frozen=True)
class Experiment6ScoreResult:
    """Experiment 6 metrics plus the experiment 1 comparison."""

    cohort_user_rows: int
    unique_prolific_ids: int
    duplicate_prolific_ids: tuple[str, ...]
    models: tuple[ModelScoreResult, ...]
    compare_rows: tuple[CompareRow, ...]
    variance_rows: tuple[VarianceRow, ...]


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
        predicted_remove_rate=float(sum(pred) / len(pred)),
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
    model_results = tuple(
        _score_model(
            experiment_number,
            model_folder,
            users,
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


def models_for_experiment(experiment_number: int) -> tuple[str, ...]:
    """Return the model folders scored for one experiment."""
    if experiment_number == 6:
        return EXPERIMENT6_MODEL_ORDER
    return MODEL_ORDER


def pair_predictions_by_user(labels: pd.DataFrame) -> dict[str, list[int]]:
    """Stitch pair-level yes/no rows into user-level remove indexes."""
    rows: list[tuple[str, int, str]] = []
    for row in labels.to_dict(orient="records"):
        prolific_id, pair_index = parse_pair_record_id(str(row["source_record_id"]))
        rows.append((prolific_id, pair_index, str(row["remove"])))
    return stitch_pair_predictions(rows)


def agreement_rate(pred_a: tuple[int, ...], pred_b: tuple[int, ...]) -> float:
    """Return the share of pairs where two prediction lists match."""
    if not pred_a:
        return 0.0
    matches = sum(left == right for left, right in zip(pred_a, pred_b, strict=True))
    return matches / len(pred_a)


def score_experiment6(
    all_users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> Experiment6ScoreResult:
    """Score experiment 6 models and compare them to experiment 1."""
    users = _deduplicate_users(all_users)
    exp6_models = tuple(
        _score_model_experiment6(model_folder, users, trials_by_user, store)
        for model_folder in EXPERIMENT6_MODEL_ORDER
    )
    exp1_models = tuple(
        _score_model(1, model_folder, users, trials_by_user, store)
        for model_folder in EXPERIMENT6_MODEL_ORDER
    )
    compare_rows = tuple(
        _compare_row(exp1_model, exp6_model)
        for exp1_model, exp6_model in zip(exp1_models, exp6_models, strict=True)
    )
    variance_rows = tuple(
        row
        for exp1_model, exp6_model in zip(exp1_models, exp6_models, strict=True)
        for row in _variance_rows_for_model(exp1_model, exp6_model)
    )
    return Experiment6ScoreResult(
        cohort_user_rows=len(all_users),
        unique_prolific_ids=len(users),
        duplicate_prolific_ids=_duplicate_prolific_ids(all_users),
        models=exp6_models,
        compare_rows=compare_rows,
        variance_rows=variance_rows,
    )


def write_experiment6_results_md(
    result: Experiment6ScoreResult,
    store: CampaignObjectStore,
) -> str:
    """Write experiment6/RESULTS.md locally and on S3."""
    relative_path = f"{EXPERIMENT_S3_PREFIX}experiment6/RESULTS.md"
    markdown = _experiment6_results_markdown(result)
    put_new_mirrored(store, relative_path, markdown.encode("utf-8"))
    return s3_uri(OUTPUT_S3_BUCKET, relative_path)


def print_experiment6_score_tables(result: Experiment6ScoreResult) -> None:
    """Print experiment 6 user-level, post-level, and compare tables."""
    wrapper = _experiment6_as_score_result(result)
    print(_user_level_table(wrapper))
    print()
    print(_post_level_table_with_predicted_rate(wrapper))
    print()
    print(_compare_table(result.compare_rows))


def _score_model_experiment6(
    model_folder: str,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> ModelScoreResult:
    paths = _full_feature_paths(6, model_folder)
    labels = _load_final_labels(store, paths)
    failed_ids = read_failed_ids(store, paths)
    failed_users_from_errors = _failed_users_from_pair_ids(failed_ids)
    predictions = pair_predictions_by_user(labels)
    user_rows: list[UserScoreRow] = []
    trial_rows: list[TrialScoreRow] = []
    failed_users = 0
    for user in users:
        prolific_id = user.prolific_id
        if prolific_id in failed_users_from_errors or prolific_id not in predictions:
            failed_users += 1
            continue
        try:
            pred = tuple(expand_remove_indexes(predictions[prolific_id]))
        except ValueError:
            failed_users += 1
            continue
        user_trials = _trials_by_pair_index(trials_by_user[prolific_id])
        if len(user_trials) != POSTS_PER_USER:
            failed_users += 1
            continue
        gold = tuple(trial.gold_remove for trial in user_trials)
        user_rows.append(
            UserScoreRow(
                prolific_id=prolific_id,
                party_group=user.party_group,
                gold=gold,
                pred=pred,
            )
        )
        trial_rows.extend(_trial_score_rows(prolific_id, user_trials, pred))
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
        user_rows=tuple(user_rows),
    )


def _failed_users_from_pair_ids(failed_ids: list[str]) -> set[str]:
    failed_users: set[str] = set()
    for record_id in failed_ids:
        prolific_id, _ = parse_pair_record_id(record_id)
        failed_users.add(prolific_id)
    return failed_users


def _trials_by_pair_index(trials: list[CohortTrial]) -> list[CohortTrial]:
    by_index: dict[int, CohortTrial] = {}
    for trial in sorted(trials, key=lambda item: item.trial_index):
        if trial.pair_index not in by_index:
            by_index[trial.pair_index] = trial
    return [by_index[index] for index in sorted(by_index)[:POSTS_PER_USER]]


def _compare_row(exp1: ModelScoreResult, exp6: ModelScoreResult) -> CompareRow:
    exp1_by_id = {row.prolific_id: row for row in exp1.user_rows}
    exp6_by_id = {row.prolific_id: row for row in exp6.user_rows}
    shared_ids = sorted(set(exp1_by_id) & set(exp6_by_id))
    shared_exp1 = [exp1_by_id[pid] for pid in shared_ids]
    shared_exp6 = [exp6_by_id[pid] for pid in shared_ids]
    exp1_pooled_gold = [value for row in shared_exp1 for value in row.gold]
    exp1_pooled_pred = [value for row in shared_exp1 for value in row.pred]
    exp6_pooled_pred = [value for row in shared_exp6 for value in row.pred]
    exp1_post = pooled_metrics(exp1_pooled_gold, exp1_pooled_pred) if exp1_pooled_gold else _zero_pooled_metrics()
    exp6_post = pooled_metrics(exp1_pooled_gold, exp6_pooled_pred) if exp1_pooled_gold else _zero_pooled_metrics()
    matches = 0
    total = 0
    for left, right in zip(shared_exp1, shared_exp6, strict=True):
        for pred_a, pred_b in zip(left.pred, right.pred, strict=True):
            total += 1
            if pred_a == pred_b:
                matches += 1
    return CompareRow(
        model=exp1.model,
        n_users=len(shared_ids),
        exp1_user_f1=mean_user_metrics(shared_exp1).f1 if shared_exp1 else 0.0,
        exp6_user_f1=mean_user_metrics(shared_exp6).f1 if shared_exp6 else 0.0,
        exp1_post_f1=exp1_post.f1,
        exp6_post_f1=exp6_post.f1,
        exp1_accuracy=exp1_post.accuracy,
        exp6_accuracy=exp6_post.accuracy,
        exp1_precision=exp1_post.precision,
        exp6_precision=exp6_post.precision,
        exp1_recall=exp1_post.recall,
        exp6_recall=exp6_post.recall,
        exp1_predicted_remove_rate=exp1_post.predicted_remove_rate,
        exp6_predicted_remove_rate=exp6_post.predicted_remove_rate,
        gold_remove_rate=exp1_post.baseline_remove_rate,
        agreement_rate=(matches / total) if total else 0.0,
    )


def _variance_rows_for_model(
    exp1: ModelScoreResult,
    exp6: ModelScoreResult,
) -> tuple[VarianceRow, VarianceRow]:
    exp1_by_id = {row.prolific_id: row for row in exp1.user_rows}
    exp6_by_id = {row.prolific_id: row for row in exp6.user_rows}
    shared_ids = set(exp1_by_id) & set(exp6_by_id)
    return (
        _variance_row(exp1.model, 1, [exp1_by_id[pid] for pid in shared_ids]),
        _variance_row(exp6.model, 6, [exp6_by_id[pid] for pid in shared_ids]),
    )


def _variance_row(
    model: str,
    experiment_number: int,
    user_rows: list[UserScoreRow],
) -> VarianceRow:
    variances: list[float] = []
    for row in user_rows:
        correctness = [
            1.0 if gold == pred else 0.0 for gold, pred in zip(row.gold, row.pred, strict=True)
        ]
        if len(correctness) < 2:
            continue
        variances.append(statistics.pvariance(correctness))
    if len(variances) < 2:
        value = float(variances[0]) if variances else 0.0
        return VarianceRow(model, experiment_number, value, value, value, value)
    ordered = sorted(variances)
    quartiles = statistics.quantiles(ordered, n=4)
    return VarianceRow(
        model=model,
        experiment_number=experiment_number,
        mean=float(statistics.mean(ordered)),
        median=float(statistics.median(ordered)),
        p25=float(quartiles[0]),
        p75=float(quartiles[2]),
    )


def _experiment6_as_score_result(result: Experiment6ScoreResult) -> ExperimentScoreResult:
    return ExperimentScoreResult(
        experiment_number=6,
        cohort_user_rows=result.cohort_user_rows,
        unique_prolific_ids=result.unique_prolific_ids,
        duplicate_prolific_ids=result.duplicate_prolific_ids,
        models=result.models,
    )


def _experiment6_results_markdown(result: Experiment6ScoreResult) -> str:
    wrapper = _experiment6_as_score_result(result)
    duplicate_text = ", ".join(result.duplicate_prolific_ids) or "none"
    lines = [
        "# Experiment 6 results",
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
        _user_level_table(wrapper),
        "",
        *_model_count_lines(wrapper, "scored_users"),
        "",
        "## Post-level",
        "",
        _post_level_table_with_predicted_rate(wrapper),
        "",
        *_model_count_lines(wrapper, "scored_pairs"),
        "",
    ]
    lines.extend(_party_sections(wrapper))
    lines.extend(_trial_sections(wrapper, "toxicity", TOXICITY_VALUES))
    lines.extend(_trial_sections(wrapper, "stance", STANCE_VALUES))
    lines.extend(
        [
            "## Comparison against experiment 1",
            "",
            "Users scored in both experiment 1 and experiment 6 for that model.",
            "",
            _compare_table(result.compare_rows),
            "",
            "## Within-user variance of per-pair correctness",
            "",
            "Population variance of per-pair correctness on the intersection users.",
            "",
            _variance_table(result.variance_rows),
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _post_level_table_with_predicted_rate(result: ExperimentScoreResult) -> str:
    header = (
        "| model | n_pairs | baseline remove rate | predicted remove rate | "
        "accuracy | precision | recall | F1 |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    rows = [
        (
            f"| {model.model} | {model.scored_pairs} | "
            f"{model.post_level.baseline_remove_rate:.4f} | "
            f"{model.post_level.predicted_remove_rate:.4f} | "
            f"{model.post_level.accuracy:.4f} | {model.post_level.precision:.4f} | "
            f"{model.post_level.recall:.4f} | {model.post_level.f1:.4f} |"
        )
        for model in result.models
    ]
    return "\n".join([header, separator, *rows])


def _compare_table(rows: tuple[CompareRow, ...]) -> str:
    header = (
        "| model | n_users | exp1 user F1 | exp6 user F1 | exp1 post F1 | exp6 post F1 | "
        "exp1 accuracy | exp6 accuracy | exp1 precision | exp6 precision | "
        "exp1 recall | exp6 recall | exp1 pred remove | exp6 pred remove | "
        "gold remove | agreement |"
    )
    separator = (
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: |"
    )
    body = [
        (
            f"| {row.model} | {row.n_users} | "
            f"{row.exp1_user_f1:.4f} | {row.exp6_user_f1:.4f} | "
            f"{row.exp1_post_f1:.4f} | {row.exp6_post_f1:.4f} | "
            f"{row.exp1_accuracy:.4f} | {row.exp6_accuracy:.4f} | "
            f"{row.exp1_precision:.4f} | {row.exp6_precision:.4f} | "
            f"{row.exp1_recall:.4f} | {row.exp6_recall:.4f} | "
            f"{row.exp1_predicted_remove_rate:.4f} | {row.exp6_predicted_remove_rate:.4f} | "
            f"{row.gold_remove_rate:.4f} | {row.agreement_rate:.4f} |"
        )
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _variance_table(rows: tuple[VarianceRow, ...]) -> str:
    header = "| model | experiment | mean | median | p25 | p75 |"
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    body = [
        (
            f"| {row.model} | {row.experiment_number} | "
            f"{row.mean:.4f} | {row.median:.4f} | {row.p25:.4f} | {row.p75:.4f} |"
        )
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _score_model(
    experiment_number: int,
    model_folder: str,
    users: tuple[CohortUser, ...],
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
        user_trials = _trials_for_user(user, trials_by_user)
        gold = tuple(trial.gold_remove for trial in user_trials)
        user_rows.append(
            UserScoreRow(
                prolific_id=prolific_id,
                party_group=user.party_group,
                gold=gold,
                pred=pred,
            )
        )
        trial_rows.extend(_trial_score_rows(user.prolific_id, user_trials, pred))
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
        user_rows=tuple(user_rows),
    )


def _trials_for_user(
    user: CohortUser,
    trials_by_user: dict[str, list[CohortTrial]],
) -> list[CohortTrial]:
    trials = list(trials_by_user[user.prolific_id])
    if len(trials) > POSTS_PER_USER:
        trials = trials[:POSTS_PER_USER]
    return sorted(trials, key=lambda trial: trial.trial_index)


def _trial_score_rows(
    prolific_id: str,
    trials: list[CohortTrial],
    pred: tuple[int, ...],
) -> list[TrialScoreRow]:
    ordered = trials
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
        predicted_remove_rate=0.0,
    )
