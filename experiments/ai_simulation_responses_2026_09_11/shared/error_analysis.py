"""Error-rate ranking and prediction variance for experiment 5."""

from __future__ import annotations

import io
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

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
    POSTS_PER_USER,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import MODEL_ORDER
from experiments.ai_simulation_responses_2026_09_11.shared.schema import expand_remove_indexes
from experiments.ai_simulation_responses_2026_09_11.shared.score import (
    STANCE_VALUES,
    TOXICITY_VALUES,
    _deduplicate_users,
    _duplicate_prolific_ids,
    _full_feature_paths,
    _load_final_labels,
    _prediction_by_user,
    _trials_for_user,
    user_metrics,
)
from experiments.ai_simulation_responses_2026_09_11.shared.write import put_new_mirrored

FALSE_NEGATIVE_CSV = (
    f"{EXPERIMENT_S3_PREFIX}experiment5/outputs/false_negative_posts.csv"
)
FALSE_POSITIVE_CSV = (
    f"{EXPERIMENT_S3_PREFIX}experiment5/outputs/false_positive_posts.csv"
)
LOWEST_F1_USERS_CSV = (
    f"{EXPERIMENT_S3_PREFIX}experiment5/outputs/lowest_f1_users.csv"
)
RESULTS_MD = f"{EXPERIMENT_S3_PREFIX}experiment5/RESULTS.md"
EXPERIMENT_NUMBERS = (1, 2, 3, 4)
FN_POST_TARGET = 75
FP_POST_TARGET = 75
WORST_USER_TARGET = 100


@dataclass(frozen=True)
class ScoredCell:
    """One scored model-experiment prediction on one user-pair."""

    experiment_number: int
    model: str
    prolific_id: str
    pair_index: int
    post_id: str
    gold: int
    pred: int
    sampled_stance: str
    sample_toxicity_type: str


@dataclass(frozen=True)
class RankedPost:
    """One ranked post with an error rate."""

    prolific_id: str
    pair_index: int
    post_id: str
    error_rate: float
    gold: int
    sampled_stance: str
    sample_toxicity_type: str


@dataclass(frozen=True)
class RankedUser:
    """One ranked user with mean F1 across model-experiment cells."""

    prolific_id: str
    mean_f1: float
    party_group: str
    political_ideology: str
    age: str
    education: str
    gold_remove_rate: float
    scored_cells: int


@dataclass(frozen=True)
class DistributionSummary:
    """Summary statistics for one distribution."""

    mean: float
    median: float
    p25: float
    p75: float


@dataclass(frozen=True)
class ErrorAnalysisResult:
    """Outputs from one experiment 5 error analysis run."""

    cohort_user_rows: int
    unique_prolific_ids: int
    duplicate_prolific_ids: tuple[str, ...]
    false_negative_posts: tuple[RankedPost, ...]
    false_positive_posts: tuple[RankedPost, ...]
    lowest_f1_users: tuple[RankedUser, ...]
    toxicity_comparison: dict[str, tuple[int, int]]
    stance_comparison: dict[str, tuple[int, int]]
    within_user_variance: dict[str, DistributionSummary]
    across_model_variance: DistributionSummary
    false_negative_shortfall: int
    false_positive_shortfall: int
    worst_user_shortfall: int
    results_s3_uri: str
    false_negative_s3_uri: str
    false_positive_s3_uri: str
    lowest_f1_users_s3_uri: str


def require_all_finals(store: CampaignObjectStore) -> None:
    """Exit non-zero when any experiment 1-4 final parquet is missing."""
    missing: list[str] = []
    for experiment_number in EXPERIMENT_NUMBERS:
        for model_folder in MODEL_ORDER:
            paths = _full_feature_paths(experiment_number, model_folder)
            if store.get(paths.final_key) is None:
                missing.append(paths.uri(paths.final_key))
    if missing:
        raise SystemExit("\n".join(missing))


def collect_scored_cells(
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> list[ScoredCell]:
    """Pool scored predictions across experiments 1-4 and all four models."""
    deduped = _deduplicate_users(users)
    cells: list[ScoredCell] = []
    for experiment_number in EXPERIMENT_NUMBERS:
        for model_folder in MODEL_ORDER:
            cells.extend(
                _scored_cells_for_model(
                    experiment_number,
                    model_folder,
                    deduped,
                    trials_by_user,
                    store,
                )
            )
    return cells


def rank_false_negative_posts(
    cells: Iterable[ScoredCell],
    *,
    k: int = FN_POST_TARGET,
) -> tuple[tuple[RankedPost, ...], int]:
    """Rank posts by false-negative rate, highest first."""
    grouped: dict[tuple[str, int, str], list[ScoredCell]] = defaultdict(list)
    for cell in cells:
        key = (cell.prolific_id, cell.pair_index, cell.post_id)
        grouped[key].append(cell)
    ranked: list[RankedPost] = []
    for (prolific_id, pair_index, post_id), group in grouped.items():
        total = len(group)
        if total == 0:
            continue
        fn_count = sum(1 for cell in group if cell.gold == 1 and cell.pred == 0)
        rate = fn_count / total
        if rate <= 0:
            continue
        sample = group[0]
        ranked.append(
            RankedPost(
                prolific_id=prolific_id,
                pair_index=pair_index,
                post_id=post_id,
                error_rate=rate,
                gold=sample.gold,
                sampled_stance=sample.sampled_stance,
                sample_toxicity_type=sample.sample_toxicity_type,
            )
        )
    ranked.sort(key=lambda row: (-row.error_rate, row.post_id))
    shortfall = max(0, k - len(ranked))
    return tuple(ranked[:k]), shortfall


def rank_false_positive_posts(
    cells: Iterable[ScoredCell],
    *,
    k: int = FP_POST_TARGET,
) -> tuple[tuple[RankedPost, ...], int]:
    """Rank posts by false-positive rate, highest first."""
    grouped: dict[tuple[str, int, str], list[ScoredCell]] = defaultdict(list)
    for cell in cells:
        key = (cell.prolific_id, cell.pair_index, cell.post_id)
        grouped[key].append(cell)
    ranked: list[RankedPost] = []
    for (prolific_id, pair_index, post_id), group in grouped.items():
        total = len(group)
        if total == 0:
            continue
        fp_count = sum(1 for cell in group if cell.gold == 0 and cell.pred == 1)
        rate = fp_count / total
        if rate <= 0:
            continue
        sample = group[0]
        ranked.append(
            RankedPost(
                prolific_id=prolific_id,
                pair_index=pair_index,
                post_id=post_id,
                error_rate=rate,
                gold=sample.gold,
                sampled_stance=sample.sampled_stance,
                sample_toxicity_type=sample.sample_toxicity_type,
            )
        )
    ranked.sort(key=lambda row: (-row.error_rate, row.post_id))
    shortfall = max(0, k - len(ranked))
    return tuple(ranked[:k]), shortfall


def rank_worst_users(
    cells: Iterable[ScoredCell],
    users_by_id: dict[str, CohortUser],
    *,
    k: int = WORST_USER_TARGET,
) -> tuple[tuple[RankedUser, ...], int]:
    """Rank users by mean user-level F1 across model-experiment cells."""
    by_user_model: dict[tuple[str, int, str], list[ScoredCell]] = defaultdict(list)
    for cell in cells:
        key = (cell.prolific_id, cell.experiment_number, cell.model)
        by_user_model[key].append(cell)
    mean_f1_by_user: dict[str, tuple[float, int]] = {}
    gold_by_user: dict[str, list[int]] = {}
    for (prolific_id, _experiment, _model), group in by_user_model.items():
        gold = [cell.gold for cell in sorted(group, key=lambda item: item.pair_index)]
        pred = [cell.pred for cell in sorted(group, key=lambda item: item.pair_index)]
        if prolific_id not in gold_by_user:
            gold_by_user[prolific_id] = gold
        f1 = user_metrics(gold, pred).f1
        current = mean_f1_by_user.get(prolific_id)
        if current is None:
            mean_f1_by_user[prolific_id] = (f1, 1)
        else:
            total_f1, count = current
            mean_f1_by_user[prolific_id] = (total_f1 + f1, count + 1)
    ranked: list[RankedUser] = []
    for prolific_id, (total_f1, count) in mean_f1_by_user.items():
        user = users_by_id[prolific_id]
        gold_values = gold_by_user[prolific_id]
        ranked.append(
            RankedUser(
                prolific_id=prolific_id,
                mean_f1=total_f1 / count,
                party_group=user.party_group,
                political_ideology=user.political_ideology,
                age=user.age,
                education=user.education,
                gold_remove_rate=sum(gold_values) / len(gold_values),
                scored_cells=count,
            )
        )
    ranked.sort(key=lambda row: (row.mean_f1, row.prolific_id))
    shortfall = max(0, k - len(ranked))
    return tuple(ranked[:k]), shortfall


def compare_field_counts(
    selected: tuple[RankedPost, ...],
    cohort_trials: tuple[CohortTrial, ...],
    field_name: str,
    values: tuple[str, ...],
) -> dict[str, tuple[int, int]]:
    """Compare field counts in selected posts vs remaining cohort posts."""
    selected_keys = {
        (row.prolific_id, row.pair_index, row.post_id) for row in selected
    }
    selected_counts = {value: 0 for value in values}
    remaining_counts = {value: 0 for value in values}
    for trial in cohort_trials:
        key = (trial.prolific_id, trial.pair_index, trial.post_id)
        field_value = getattr(trial, field_name)
        if key in selected_keys:
            selected_counts[field_value] = selected_counts.get(field_value, 0) + 1
        else:
            remaining_counts[field_value] = remaining_counts.get(field_value, 0) + 1
    return {
        value: (selected_counts.get(value, 0), remaining_counts.get(value, 0))
        for value in values
    }


def within_user_variance_by_model(
    cells: Iterable[ScoredCell],
) -> dict[str, DistributionSummary]:
    """Summarize per-user correctness variance on experiment 1, one row per model."""
    by_model_user: dict[tuple[str, str], list[ScoredCell]] = defaultdict(list)
    for cell in cells:
        if cell.experiment_number != 1:
            continue
        by_model_user[(cell.model, cell.prolific_id)].append(cell)
    summaries: dict[str, DistributionSummary] = {}
    for model_folder in MODEL_ORDER:
        user_variances: list[float] = []
        for (model, prolific_id), group in by_model_user.items():
            if model != model_folder:
                continue
            ordered = sorted(group, key=lambda item: item.pair_index)
            correctness = [
                1.0 if item.gold == item.pred else 0.0 for item in ordered
            ]
            if len(correctness) < 2:
                continue
            user_variances.append(statistics.pvariance(correctness))
        summaries[model_folder] = distribution_summary(user_variances)
    return summaries


def across_model_variance_summary(
    cells: Iterable[ScoredCell],
) -> DistributionSummary:
    """Summarize stdev of experiment 1 remove predictions across four models."""
    by_user_pair: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for cell in cells:
        if cell.experiment_number != 1:
            continue
        by_user_pair[(cell.prolific_id, cell.pair_index)][cell.model] = cell.pred
    stdevs: list[float] = []
    for predictions in by_user_pair.values():
        if len(predictions) != len(MODEL_ORDER):
            continue
        values = [float(predictions[model]) for model in MODEL_ORDER]
        if len(set(values)) <= 1:
            stdevs.append(0.0)
        else:
            stdevs.append(statistics.stdev(values))
    return distribution_summary(stdevs)


def distribution_summary(values: list[float]) -> DistributionSummary:
    """Return mean, median, p25, and p75 for one distribution."""
    if not values:
        return DistributionSummary(0.0, 0.0, 0.0, 0.0)
    ordered = sorted(values)
    quartiles = statistics.quantiles(ordered, n=4)
    return DistributionSummary(
        mean=float(statistics.mean(ordered)),
        median=float(statistics.median(ordered)),
        p25=float(quartiles[0]),
        p75=float(quartiles[2]),
    )


def run_error_analysis(
    store: CampaignObjectStore,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> ErrorAnalysisResult:
    """Run experiment 5 error analysis and upload outputs."""
    require_all_finals(store)
    cells = collect_scored_cells(users, trials_by_user, store)
    deduped = _deduplicate_users(users)
    users_by_id = {user.prolific_id: user for user in deduped}
    cohort_trials = tuple(
        trial
        for user in deduped
        for trial in _trials_for_user(user, trials_by_user)
    )
    false_negative_posts, fn_shortfall = rank_false_negative_posts(cells)
    false_positive_posts, fp_shortfall = rank_false_positive_posts(cells)
    lowest_f1_users, user_shortfall = rank_worst_users(cells, users_by_id)
    combined_posts = false_negative_posts + false_positive_posts
    toxicity_comparison = compare_field_counts(
        combined_posts,
        cohort_trials,
        "sample_toxicity_type",
        TOXICITY_VALUES,
    )
    stance_comparison = compare_field_counts(
        combined_posts,
        cohort_trials,
        "sampled_stance",
        STANCE_VALUES,
    )
    within_user_variance = within_user_variance_by_model(cells)
    across_model_variance = across_model_variance_summary(cells)
    markdown = _results_markdown(
        cohort_user_rows=len(users),
        unique_prolific_ids=len(deduped),
        duplicate_prolific_ids=_duplicate_prolific_ids(users),
        false_negative_posts=false_negative_posts,
        false_positive_posts=false_positive_posts,
        lowest_f1_users=lowest_f1_users,
        toxicity_comparison=toxicity_comparison,
        stance_comparison=stance_comparison,
        within_user_variance=within_user_variance,
        across_model_variance=across_model_variance,
        false_negative_shortfall=fn_shortfall,
        false_positive_shortfall=fp_shortfall,
        worst_user_shortfall=user_shortfall,
    )
    results_s3_uri = _upload_text(store, RESULTS_MD, markdown)
    false_negative_s3_uri = _upload_csv(
        store,
        FALSE_NEGATIVE_CSV,
        _posts_csv(false_negative_posts, "fn_rate"),
    )
    false_positive_s3_uri = _upload_csv(
        store,
        FALSE_POSITIVE_CSV,
        _posts_csv(false_positive_posts, "fp_rate"),
    )
    lowest_f1_users_s3_uri = _upload_csv(
        store,
        LOWEST_F1_USERS_CSV,
        _users_csv(lowest_f1_users),
    )
    return ErrorAnalysisResult(
        cohort_user_rows=len(users),
        unique_prolific_ids=len(deduped),
        duplicate_prolific_ids=_duplicate_prolific_ids(users),
        false_negative_posts=false_negative_posts,
        false_positive_posts=false_positive_posts,
        lowest_f1_users=lowest_f1_users,
        toxicity_comparison=toxicity_comparison,
        stance_comparison=stance_comparison,
        within_user_variance=within_user_variance,
        across_model_variance=across_model_variance,
        false_negative_shortfall=fn_shortfall,
        false_positive_shortfall=fp_shortfall,
        worst_user_shortfall=user_shortfall,
        results_s3_uri=results_s3_uri,
        false_negative_s3_uri=false_negative_s3_uri,
        false_positive_s3_uri=false_positive_s3_uri,
        lowest_f1_users_s3_uri=lowest_f1_users_s3_uri,
    )


def print_error_analysis_summary(result: ErrorAnalysisResult) -> None:
    """Print counts, shortfalls, and S3 URIs for experiment 5."""
    print(f"false_negative_posts={len(result.false_negative_posts)}")
    if result.false_negative_shortfall:
        print(f"false_negative_shortfall={result.false_negative_shortfall}")
    print(f"false_positive_posts={len(result.false_positive_posts)}")
    if result.false_positive_shortfall:
        print(f"false_positive_shortfall={result.false_positive_shortfall}")
    print(f"lowest_f1_users={len(result.lowest_f1_users)}")
    if result.worst_user_shortfall:
        print(f"worst_user_shortfall={result.worst_user_shortfall}")
    print(f"results_s3_uri={result.results_s3_uri}")
    print(f"false_negative_s3_uri={result.false_negative_s3_uri}")
    print(f"false_positive_s3_uri={result.false_positive_s3_uri}")
    print(f"lowest_f1_users_s3_uri={result.lowest_f1_users_s3_uri}")


def _scored_cells_for_model(
    experiment_number: int,
    model_folder: str,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
    store: CampaignObjectStore,
) -> list[ScoredCell]:
    paths = _full_feature_paths(experiment_number, model_folder)
    labels = _load_final_labels(store, paths)
    failed_ids = read_failed_ids(store, paths)
    predictions = _prediction_by_user(labels)
    cells: list[ScoredCell] = []
    for user in users:
        prolific_id = user.prolific_id
        if prolific_id in failed_ids or prolific_id not in predictions:
            continue
        try:
            pred = expand_remove_indexes(predictions[prolific_id])
        except ValueError:
            continue
        trials = _trials_for_user(user, trials_by_user)
        if len(trials) != POSTS_PER_USER:
            continue
        for trial, prediction in zip(trials, pred, strict=True):
            cells.append(
                ScoredCell(
                    experiment_number=experiment_number,
                    model=model_folder,
                    prolific_id=prolific_id,
                    pair_index=trial.pair_index,
                    post_id=trial.post_id,
                    gold=trial.gold_remove,
                    pred=prediction,
                    sampled_stance=trial.sampled_stance,
                    sample_toxicity_type=trial.sample_toxicity_type,
                )
            )
    return cells


def _posts_csv(posts: tuple[RankedPost, ...], rate_column: str) -> bytes:
    rows = [
        {
            "prolific_id": post.prolific_id,
            "pair_index": post.pair_index,
            "post_id": post.post_id,
            rate_column: post.error_rate,
            "gold": post.gold,
            "sampled_stance": post.sampled_stance,
            "sample_toxicity_type": post.sample_toxicity_type,
        }
        for post in posts
    ]
    frame = pd.DataFrame(rows)
    return _csv_bytes(frame)


def _users_csv(users: tuple[RankedUser, ...]) -> bytes:
    rows = [
        {
            "prolific_id": user.prolific_id,
            "mean_f1": user.mean_f1,
            "party_group": user.party_group,
            "political_ideology": user.political_ideology,
            "age": user.age,
            "education": user.education,
            "gold_remove_rate": user.gold_remove_rate,
            "scored_cells": user.scored_cells,
        }
        for user in users
    ]
    frame = pd.DataFrame(rows)
    return _csv_bytes(frame)


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _upload_text(store: CampaignObjectStore, relative_path: str, text: str) -> str:
    put_new_mirrored(store, relative_path, text.encode("utf-8"))
    return s3_uri(OUTPUT_S3_BUCKET, relative_path)


def _upload_csv(store: CampaignObjectStore, relative_path: str, body: bytes) -> str:
    put_new_mirrored(store, relative_path, body)
    return s3_uri(OUTPUT_S3_BUCKET, relative_path)


def _results_markdown(
    *,
    cohort_user_rows: int,
    unique_prolific_ids: int,
    duplicate_prolific_ids: tuple[str, ...],
    false_negative_posts: tuple[RankedPost, ...],
    false_positive_posts: tuple[RankedPost, ...],
    lowest_f1_users: tuple[RankedUser, ...],
    toxicity_comparison: dict[str, tuple[int, int]],
    stance_comparison: dict[str, tuple[int, int]],
    within_user_variance: dict[str, DistributionSummary],
    across_model_variance: DistributionSummary,
    false_negative_shortfall: int,
    false_positive_shortfall: int,
    worst_user_shortfall: int,
) -> str:
    duplicate_text = ", ".join(duplicate_prolific_ids) or "none"
    lines = [
        "# Experiment 5 results",
        "",
        "## Cohort",
        "",
        (
            f"{unique_prolific_ids} unique prolific_ids from "
            f"{cohort_user_rows} cohort user rows. "
            f"Duplicate prolific_ids: {duplicate_text}."
        ),
        "",
        "## Ranked posts",
        "",
        (
            f"False-negative posts: {len(false_negative_posts)} "
            f"(target {FN_POST_TARGET}"
            + (f", shortfall {false_negative_shortfall}" if false_negative_shortfall else "")
            + ")."
        ),
        (
            f"False-positive posts: {len(false_positive_posts)} "
            f"(target {FP_POST_TARGET}"
            + (f", shortfall {false_positive_shortfall}" if false_positive_shortfall else "")
            + ")."
        ),
        "",
        "## Toxicity and stance in combined 150 posts",
        "",
        _comparison_table(
            "sample_toxicity_type",
            TOXICITY_VALUES,
            toxicity_comparison,
        ),
        "",
        _comparison_table(
            "sampled_stance",
            STANCE_VALUES,
            stance_comparison,
        ),
        "",
        "## Lowest-F1 users",
        "",
        (
            f"Users ranked: {len(lowest_f1_users)} "
            f"(target {WORST_USER_TARGET}"
            + (f", shortfall {worst_user_shortfall}" if worst_user_shortfall else "")
            + ")."
        ),
        "",
        _user_description_table(lowest_f1_users),
        "",
        "## Within-user variance (experiment 1)",
        "",
        _variance_table(within_user_variance),
        "",
        "## Across-model variance (experiment 1)",
        "",
        _distribution_row("all user-pairs", across_model_variance),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _comparison_table(
    label: str,
    values: tuple[str, ...],
    comparison: dict[str, tuple[int, int]],
) -> str:
    header = f"| {label} | combined 150 | remaining cohort posts |"
    separator = "| --- | ---: | ---: |"
    rows = [
        f"| {value} | {comparison[value][0]} | {comparison[value][1]} |"
        for value in values
    ]
    return "\n".join([header, separator, *rows])


def _user_description_table(users: tuple[RankedUser, ...]) -> str:
    header = (
        "| prolific_id | mean F1 | party_group | political_ideology | age | "
        "education | gold remove rate | scored cells |"
    )
    separator = "| --- | ---: | --- | --- | --- | --- | ---: | ---: |"
    rows = [
        (
            f"| {user.prolific_id} | {user.mean_f1:.4f} | {user.party_group} | "
            f"{user.political_ideology} | {user.age} | {user.education} | "
            f"{user.gold_remove_rate:.4f} | {user.scored_cells} |"
        )
        for user in users
    ]
    return "\n".join([header, separator, *rows])


def _variance_table(summaries: dict[str, DistributionSummary]) -> str:
    header = "| model | mean | median | p25 | p75 |"
    separator = "| --- | ---: | ---: | ---: | ---: |"
    rows = [
        _distribution_row(model, summaries[model])
        for model in MODEL_ORDER
    ]
    return "\n".join([header, separator, *rows])


def _distribution_row(label: str, summary: DistributionSummary) -> str:
    return (
        f"| {label} | {summary.mean:.4f} | {summary.median:.4f} | "
        f"{summary.p25:.4f} | {summary.p75:.4f} |"
    )
