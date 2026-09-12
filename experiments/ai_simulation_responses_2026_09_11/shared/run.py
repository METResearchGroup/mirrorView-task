"""CLI entrypoint for the AI simulation responses experiment."""

from __future__ import annotations

import argparse
import io
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import pandas as pd

from data_platform.generate_features.campaign_engine_map import (
    BEDROCK_ENGINE_TYPE,
    OPENAI_ENGINE_TYPE,
)
from data_platform.generate_features.engines.base import RecordLabelFailure
from data_platform.generate_features.models import CampaignRunConfig, FeatureSpec, LabelTask
from data_platform.generate_features.platform_cli import CAMPAIGN_BATCH_SIZE
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
from experiments.ai_simulation_responses_2026_09_11.shared import bedrock_runner, openai_runner
from experiments.ai_simulation_responses_2026_09_11.shared.cohort import (
    build_cohort,
    list_september_csv_keys,
)
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    COHORT_TRIALS_KEY,
    COHORT_USERS_KEY,
    CohortTrial,
    CohortUser,
    EXPERIMENT6_MODEL_ORDER,
    EXPERIMENT_S3_PREFIX,
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA,
    MODEL_FOLDER_BEDROCK_QWEN,
    MODEL_FOLDER_OPENAI,
    OUTPUT_S3_BUCKET,
    POSTS_PER_USER,
    SMOKE_USER_COUNT,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import (
    COST_ESTIMATE_RELATIVE_PATH,
    EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH,
    MODEL_ORDER,
    TokenUsageRecord,
    build_cost_estimate_markdown,
    build_experiment6_cost_markdown,
    build_experiment6_cost_rows,
    build_experiment_sections,
    load_medians_by_model,
    load_medians_for_models,
    load_token_usage,
    median_tokens,
    save_token_usage,
    token_usage_key,
    token_usage_records_from_bedrock,
    token_usage_records_from_openai,
    upload_cost_estimate,
    upload_experiment6_cost_estimate,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import (
    STUDY_SYSTEM_PROMPT,
    STUDY_SYSTEM_PROMPT_SINGLE_PAIR,
    render_single_pair,
    render_user_prompt,
)
from experiments.ai_simulation_responses_2026_09_11.shared.schema import (
    FEATURE_NAME,
    pair_record_id,
    pair_yes_no_spec,
    parse_pair_record_id,
    remove_indexes_spec,
)
from experiments.ai_simulation_responses_2026_09_11.shared.error_analysis import (
    print_error_analysis_summary,
    run_error_analysis,
)
from experiments.ai_simulation_responses_2026_09_11.shared.score import (
    print_experiment6_score_tables,
    print_score_tables,
    score_experiment,
    score_experiment6,
    write_experiment6_results_md,
    write_results_md,
)
from experiments.ai_simulation_responses_2026_09_11.shared.write import (
    require_cohort_keys_absent,
    upload_cohort,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp
from scripts.export_study_results import download_csvs

ATTEMPT_COUNT = 1
BATCH_ID_PREFIX = "part-"
PART_INDEX_WIDTH = 5
REQUEST_ID_SEPARATOR = "-"
SMOKE_FEATURE_NAME = "smoke"
CAMPAIGN_ID = "ai_simulation_responses_2026_09_11"
DATASET_ID = "shared_cohort"
PREPROCESSED_RUN = "cohort"
CAMPAIGN_PLATFORM = "experiment"
LABELS_ROOT_URI = (
    f"s3://{OUTPUT_S3_BUCKET}/{EXPERIMENT_S3_PREFIX}experiment1/outputs"
)
EXPERIMENT2_SETUP_PATH = (
    REPO_ROOT / "experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md"
)
EXPERIMENT1_SETUP_PATH = (
    REPO_ROOT / "experiments/ai_simulation_responses_2026_09_11/experiment1/SETUP.md"
)
EXPERIMENT6_SETUP_PATH = (
    REPO_ROOT / "experiments/ai_simulation_responses_2026_09_11/experiment6/SETUP.md"
)
APPROVAL_RELATIVE_PATH = "experiments/ai_simulation_responses_2026_09_11/APPROVAL.md"
APPROVAL_PATH = REPO_ROOT / APPROVAL_RELATIVE_PATH
EXPERIMENT6_APPROVAL_RELATIVE_PATH = (
    "experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md"
)
EXPERIMENT6_APPROVAL_PATH = REPO_ROOT / EXPERIMENT6_APPROVAL_RELATIVE_PATH
FILLED_EXAMPLE_HEADER = "## Filled example (first cohort user)"
EXPERIMENT6_FILLED_EXAMPLE_HEADER = (
    "## Filled example (first smoke user, pair_index 1)"
)
FINAL_EXISTS_MESSAGE = "final exists"
FULL_MODEL_ENGINE_TYPES = {
    MODEL_FOLDER_OPENAI: OPENAI_ENGINE_TYPE,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA: BEDROCK_ENGINE_TYPE,
    MODEL_FOLDER_BEDROCK_QWEN: BEDROCK_ENGINE_TYPE,
    MODEL_FOLDER_BEDROCK_CLAUDE: BEDROCK_ENGINE_TYPE,
}

MODEL_CONFIGS = (
    (MODEL_FOLDER_OPENAI, OPENAI_ENGINE_TYPE, openai_runner.label_tasks_with_usage),
    (
        MODEL_FOLDER_BEDROCK_MICRO_NOVA,
        BEDROCK_ENGINE_TYPE,
        bedrock_runner.label_tasks_with_usage,
    ),
    (MODEL_FOLDER_BEDROCK_QWEN, BEDROCK_ENGINE_TYPE, bedrock_runner.label_tasks_with_usage),
    (
        MODEL_FOLDER_BEDROCK_CLAUDE,
        BEDROCK_ENGINE_TYPE,
        bedrock_runner.label_tasks_with_usage,
    ),
)
EXPERIMENT6_MODEL_CONFIGS = tuple(
    config for config in MODEL_CONFIGS if config[0] in EXPERIMENT6_MODEL_ORDER
)
MODEL_IDS = {
    MODEL_FOLDER_OPENAI: "gpt-5.4-nano",
    MODEL_FOLDER_BEDROCK_MICRO_NOVA: "us.amazon.nova-micro-v1:0",
    MODEL_FOLDER_BEDROCK_QWEN: "qwen.qwen3-32b-v1:0",
    MODEL_FOLDER_BEDROCK_CLAUDE: "us.anthropic.claude-sonnet-4-6",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse shared runner flags."""
    parser = argparse.ArgumentParser(
        description="AI simulation responses shared runner",
    )
    parser.add_argument("--write-cohort", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--estimate-cost", action="store_true")
    parser.add_argument("--print-experiment-2-prompt", action="store_true")
    parser.add_argument("--experiment", type=int, choices=[1, 2, 3, 4, 5, 6])
    parser.add_argument(
        "--model",
        choices=list(MODEL_ORDER),
    )
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--analyze-errors", action="store_true")
    return parser.parse_args(argv)


def write_cohort_command() -> None:
    """Download September CSVs, confirm cohort, and upload parquet."""
    s3_client = boto3.client("s3")
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    require_cohort_keys_absent(store)
    csv_keys = list_september_csv_keys(s3_client)
    csv_paths = download_csvs(s3_client, csv_keys)
    result = build_cohort(csv_paths)
    upload = upload_cohort(result.users, result.trials, store)
    print(f"user_count={len(result.users)}")
    print(f"trial_rows={len(result.trials)}")
    print(f"dropped_incomplete={result.dropped_incomplete}")
    print(f"dropped_missing_pair_order={result.dropped_missing_pair_order}")
    print(f"dropped_missing_reflection={result.dropped_missing_reflection}")
    print(f"users_s3_uri={upload.users_s3_uri}")
    print(f"trials_s3_uri={upload.trials_s3_uri}")
    print(f"users_sha256={upload.users_sha256}")
    print(f"trials_sha256={upload.trials_sha256}")


def smoke_command() -> None:
    """Label smoke users on all four models with the experiment 1 prompt."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    smoke_subset = select_smoke_users(users)
    for model_folder, engine_type, label_fn in MODEL_CONFIGS:
        summary = run_smoke_model(
            store,
            model_folder,
            engine_type,
            label_fn,
            smoke_subset,
            trials_by_user,
        )
        print_smoke_summary(model_folder, summary)


def estimate_cost_command() -> None:
    """Build COST_ESTIMATE.md from smoke token usage without calling models."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    if store.get(COST_ESTIMATE_RELATIVE_PATH) is not None:
        raise FileExistsError(
            f"Object already exists: s3://{OUTPUT_S3_BUCKET}/{COST_ESTIMATE_RELATIVE_PATH}"
        )
    users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    smoke_paths = smoke_paths_by_model()
    medians_by_model = load_medians_by_model(store, smoke_paths)
    sections = build_experiment_sections(users, trials_by_user, medians_by_model)
    markdown = build_cost_estimate_markdown(sections)
    cost_uri = upload_cost_estimate(store, markdown)
    print(markdown)
    print(f"cost_s3_uri={cost_uri}")


def experiment6_smoke_command() -> None:
    """Label 10 users times 20 pairs on the three experiment 6 models."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    users = select_smoke_users(select_all_users(load_cohort_users()))
    trials_by_user = load_cohort_trials_by_user()
    for model_folder, engine_type, label_fn in EXPERIMENT6_MODEL_CONFIGS:
        summary = run_experiment6_smoke_model(
            store,
            model_folder,
            engine_type,
            label_fn,
            users,
            trials_by_user,
        )
        print_experiment6_smoke_summary(model_folder, summary)
    append_experiment6_filled_example(users[0], trials_by_user[users[0].prolific_id])


def experiment6_estimate_cost_command() -> None:
    """Build experiment6/COST_ESTIMATE.md from pair-level smoke tokens."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    if store.get(EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH) is not None:
        raise FileExistsError(
            "Object already exists: "
            f"s3://{OUTPUT_S3_BUCKET}/{EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH}"
        )
    unique_users = select_all_users(load_cohort_users())
    pair_call_count = len(unique_users) * POSTS_PER_USER
    medians = load_medians_for_models(
        store,
        experiment6_smoke_paths_by_model(),
        EXPERIMENT6_MODEL_ORDER,
    )
    rows = build_experiment6_cost_rows(medians, pair_call_count)
    markdown = build_experiment6_cost_markdown(rows)
    cost_uri = upload_experiment6_cost_estimate(store, markdown)
    print(markdown)
    print(f"cost_s3_uri={cost_uri}")


def run_experiment6_smoke_model(
    store: CampaignObjectStore,
    model_folder: str,
    engine_type: str,
    label_fn: object,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> dict[str, int]:
    """Label one model's experiment 6 smoke pairs and persist token usage."""
    paths = experiment6_smoke_feature_paths(model_folder)
    spec = pair_yes_no_spec(engine_type)  # type: ignore[arg-type]
    ordered_ids, texts = ordered_pair_input(users, trials_by_user)
    campaign = campaign_config_for_experiment(6)
    run_id = run_id_for_feature(campaign.campaign_id, spec.name)
    manifest, manifest_etag = load_or_create_manifest(
        store,
        paths,
        campaign,
        spec,
        expected_row_count=len(ordered_ids),
        engine_type=engine_type,
    )
    if manifest.get("final_parquet"):
        return smoke_summary_from_store(store, paths, len(ordered_ids))
    return _finish_experiment6_smoke(
        store,
        paths,
        spec,
        model_folder,
        engine_type,
        label_fn,
        ordered_ids,
        texts,
        run_id,
        manifest,
        manifest_etag,
    )


def _finish_experiment6_smoke(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    spec: FeatureSpec,
    model_folder: str,
    engine_type: str,
    label_fn: object,
    ordered_ids: list[str],
    texts: dict[str, str],
    run_id: str,
    manifest: dict[str, Any],
    manifest_etag: str,
) -> dict[str, int]:
    """Label the experiment 6 smoke part and consolidate the smoke prefix."""
    manifest_etag = label_smoke_part(
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        campaign_config_for_experiment(6),
        model_folder,
        engine_type,
        label_fn,
        ordered_ids,
        texts,
        run_id,
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
    return smoke_summary_from_store(store, paths, len(ordered_ids))


def print_experiment6_smoke_summary(model_folder: str, summary: dict[str, int]) -> None:
    """Print per-model experiment 6 smoke stdout lines."""
    print(f"model={model_folder}")
    print(f"labeled_pairs={summary['labeled']}")
    print(f"failed_pairs={summary['failed']}")
    print(f"input_tokens={summary['input_tokens']}")
    print(f"output_tokens={summary['output_tokens']}")


def experiment6_smoke_feature_paths(model_folder: str) -> FeaturePaths:
    """Return FeaturePaths for one experiment 6 model's smoke prefix."""
    root_uri = (
        f"s3://{OUTPUT_S3_BUCKET}/{EXPERIMENT_S3_PREFIX}"
        f"experiment6/outputs/{model_folder}"
    )
    return FeaturePaths.from_root_uri(root_uri, SMOKE_FEATURE_NAME)


def experiment6_smoke_paths_by_model() -> dict[str, FeaturePaths]:
    """Return experiment 6 smoke FeaturePaths for the three models."""
    return {
        model_folder: experiment6_smoke_feature_paths(model_folder)
        for model_folder in EXPERIMENT6_MODEL_ORDER
    }


def append_experiment6_filled_example(
    user: CohortUser,
    trials: list[CohortTrial],
) -> None:
    """Append one filled one-pair prompt to experiment 6 SETUP.md."""
    setup_text = EXPERIMENT6_SETUP_PATH.read_text(encoding="utf-8")
    if EXPERIMENT6_FILLED_EXAMPLE_HEADER in setup_text:
        return
    trial = _trial_at_pair_index(trials, 1)
    filled = f"{STUDY_SYSTEM_PROMPT_SINGLE_PAIR}\n\n{render_single_pair(trial)}"
    block = f"\n\n{EXPERIMENT6_FILLED_EXAMPLE_HEADER}\n\n```text\n{filled}\n```\n"
    EXPERIMENT6_SETUP_PATH.write_text(setup_text.rstrip() + block, encoding="utf-8")


def _trial_at_pair_index(trials: list[CohortTrial], pair_index: int) -> CohortTrial:
    """Return the trial with the given study pair index."""
    for trial in unique_pair_trials(trials):
        if trial.pair_index == pair_index:
            return trial
    raise ValueError(f"missing pair_index {pair_index}")


def print_experiment_2_prompt_command() -> None:
    """Print the experiment 2 template and one filled example."""
    users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    first_user = select_smoke_users(users)[0]
    filled = render_user_prompt(2, first_user, trials_by_user[first_user.prolific_id])
    print(STUDY_SYSTEM_PROMPT)
    print()
    print(_experiment_2_template())
    print()
    print(filled)
    append_filled_example_to_setup(filled)


def run_smoke_model(
    store: CampaignObjectStore,
    model_folder: str,
    engine_type: str,
    label_fn: object,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> dict[str, int]:
    """Label one model's smoke subset and persist token usage."""
    paths = smoke_feature_paths(model_folder)
    spec = remove_indexes_spec(engine_type)  # type: ignore[arg-type]
    ordered_ids, texts = ordered_smoke_input(users, trials_by_user)
    campaign = campaign_config()
    run_id = run_id_for_feature(campaign.campaign_id, FEATURE_NAME)
    manifest, manifest_etag = load_or_create_manifest(
        store,
        paths,
        campaign,
        spec,
        expected_row_count=len(ordered_ids),
        engine_type=engine_type,
    )
    if manifest.get("final_parquet"):
        return smoke_summary_from_store(store, paths, len(ordered_ids))
    manifest_etag = label_smoke_part(
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        campaign,
        model_folder,
        engine_type,
        label_fn,
        ordered_ids,
        texts,
        run_id,
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
    return smoke_summary_from_store(store, paths, len(ordered_ids))


def label_smoke_part(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    campaign: CampaignRunConfig,
    model_folder: str,
    engine_type: str,
    label_fn: object,
    ordered_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    """Label the smoke chunk when it is not already in the manifest."""
    part_index = 0
    if _smoke_part_complete(store, paths, manifest, part_index):
        return manifest_etag
    adopted = adopt_unrecorded_batch(
        store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
    )
    if adopted is not None:
        return adopted.manifest_etag
    tasks = [LabelTask(uri=record_id, text=texts[record_id]) for record_id in ordered_ids]
    rows, failures, usages = call_label_fn(label_fn, spec, tasks, model_folder)
    manifest_etag = write_smoke_rows(
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        part_index,
        ordered_ids,
        rows,
        run_id,
        model_folder,
    )
    if failures:
        append_errors(store, paths, error_records(failures, run_id, part_index))
    save_token_usage(store, paths, usages)
    return manifest_etag


def _smoke_part_complete(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    part_index: int,
) -> bool:
    """Return whether the smoke batch and token usage both exist."""
    has_batch = any(int(entry["part_index"]) == part_index for entry in manifest["batches"])
    has_tokens = store.get(token_usage_key(paths)) is not None
    return has_batch and has_tokens


def call_label_fn(
    label_fn: object,
    spec: FeatureSpec,
    tasks: list[LabelTask],
    model_folder: str,
) -> tuple[list[dict], list[RecordLabelFailure], list[TokenUsageRecord]]:
    """Dispatch to the OpenAI or Bedrock smoke label function."""
    if model_folder == MODEL_FOLDER_OPENAI:
        result = label_fn(spec, tasks)  # type: ignore[operator]
        return result.rows, result.failures, token_usage_records_from_openai(result.request_usages)
    model_id = MODEL_IDS[model_folder]
    result = label_fn(spec, tasks, model_id)  # type: ignore[operator]
    return result.rows, result.failures, token_usage_records_from_bedrock(result.request_usages)


def write_smoke_rows(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    part_index: int,
    chunk_ids: list[str],
    rows: list[dict],
    run_id: str,
    model_folder: str,
) -> str:
    """Write one smoke batch when rows exist."""
    if not rows:
        return manifest_etag
    batch_id = f"{BATCH_ID_PREFIX}{part_index:0{PART_INDEX_WIDTH}d}"
    request_ids = {
        record_id: f"{model_folder}{REQUEST_ID_SEPARATOR}{record_id}"
        for record_id in chunk_ids
    }
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


def smoke_summary_from_store(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    expected: int,
) -> dict[str, int]:
    """Summarize labeled, failed, and token totals for one smoke prefix."""
    failed_ids = read_failed_ids(store, paths)
    labeled = expected - len(failed_ids)
    usages = load_token_usage(store, paths)
    medians = median_tokens(usages)
    return {
        "labeled": labeled,
        "failed": len(failed_ids),
        "input_tokens": int(sum(usage.input_tokens for usage in usages)),
        "output_tokens": int(sum(usage.output_tokens for usage in usages)),
        "median_input": int(medians.input_tokens),
        "median_output": int(medians.output_tokens),
    }


def print_smoke_summary(model_folder: str, summary: dict[str, int]) -> None:
    """Print per-model smoke stdout lines."""
    print(f"model={model_folder}")
    print(f"labeled={summary['labeled']}")
    print(f"failed={summary['failed']}")
    print(f"input_tokens={summary['input_tokens']}")
    print(f"output_tokens={summary['output_tokens']}")


def select_smoke_users(users: tuple[CohortUser, ...]) -> tuple[CohortUser, ...]:
    """Return the first smoke users in cohort order."""
    ordered = sorted(users, key=lambda user: (user.source_file_epoch_ms, user.prolific_id))
    count = min(SMOKE_USER_COUNT, len(ordered))
    return tuple(ordered[:count])


def ordered_smoke_input(
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> tuple[list[str], dict[str, str]]:
    """Return smoke ids and experiment 1 prompts."""
    ids = [user.prolific_id for user in users]
    texts = {
        user.prolific_id: render_user_prompt(1, user, trials_by_user[user.prolific_id])
        for user in users
    }
    return ids, texts


def smoke_feature_paths(model_folder: str) -> FeaturePaths:
    """Return FeaturePaths for one model's smoke prefix."""
    root_uri = f"{LABELS_ROOT_URI}/{model_folder}"
    return FeaturePaths.from_root_uri(root_uri, SMOKE_FEATURE_NAME)


def smoke_paths_by_model() -> dict[str, FeaturePaths]:
    """Return smoke FeaturePaths for every model folder."""
    return {model_folder: smoke_feature_paths(model_folder) for model_folder in MODEL_ORDER}


def campaign_config() -> CampaignRunConfig:
    """Return the shared campaign config for smoke labeling."""
    return CampaignRunConfig(
        campaign_id=CAMPAIGN_ID,
        dataset_id=DATASET_ID,
        preprocessed_run=PREPROCESSED_RUN,
        platform=CAMPAIGN_PLATFORM,
        batch_size=CAMPAIGN_BATCH_SIZE,
    )


def load_or_create_manifest(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    campaign: CampaignRunConfig,
    spec: FeatureSpec,
    *,
    expected_row_count: int,
    engine_type: str,
) -> tuple[dict[str, Any], str]:
    """Load an existing manifest or create a fresh one."""
    fresh = new_manifest(
        campaign=campaign,
        spec=spec,
        expected_row_count=expected_row_count,
        engine_type=engine_type,
    )
    manifest, etag = load_manifest(store, paths)
    if manifest is None or etag is None:
        return fresh, save_manifest(store, paths, fresh, None)
    return manifest, etag


def _cohort_local_path(key: str) -> Path:
    """Return the repo-local path for one cohort parquet key."""
    return REPO_ROOT / key


def _default_cohort_store() -> CampaignObjectStore:
    """Return the object store for cohort parquet reads."""
    return CampaignObjectStore(OUTPUT_S3_BUCKET)


def _cache_cohort_parquet(path: Path, body: bytes) -> None:
    """Write downloaded cohort parquet bytes to a local cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _load_cohort_parquet_bytes(key: str) -> bytes:
    """Load cohort parquet bytes from local disk or S3."""
    path = _cohort_local_path(key)
    if path.is_file():
        return path.read_bytes()
    store = _default_cohort_store()
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(f"Missing cohort parquet: {path}")
    _cache_cohort_parquet(path, stored.body)
    return stored.body


def load_cohort_users() -> tuple[CohortUser, ...]:
    """Load cohort users from local parquet or S3."""
    frame = pd.read_parquet(io.BytesIO(_load_cohort_parquet_bytes(COHORT_USERS_KEY)))
    return tuple(CohortUser(**row) for row in frame.to_dict(orient="records"))


def load_cohort_trials_by_user() -> dict[str, list[CohortTrial]]:
    """Load cohort trials grouped by prolific id from local parquet or S3."""
    frame = pd.read_parquet(io.BytesIO(_load_cohort_parquet_bytes(COHORT_TRIALS_KEY)))
    grouped: dict[str, list[CohortTrial]] = defaultdict(list)
    for row in frame.to_dict(orient="records"):
        pair_order = tuple(row["pair_order"])
        trial = CohortTrial(**{**row, "pair_order": pair_order})
        grouped[trial.prolific_id].append(trial)
    return grouped


def error_records(
    failures: list[RecordLabelFailure],
    run_id: str,
    part_index: int,
) -> list[dict[str, Any]]:
    """Format label failures for errors.jsonl."""
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


def _experiment_2_template() -> str:
    """Return the unfilled experiment 2 prompt template block."""
    setup_text = EXPERIMENT2_SETUP_PATH.read_text(encoding="utf-8")
    start = setup_text.index("```text")
    end = setup_text.index("```", start + 7)
    return setup_text[start + len("```text\n") : end].strip()


def append_filled_example_to_setup(filled_prompt: str) -> None:
    """Append one filled experiment 2 prompt example to SETUP.md."""
    setup_text = EXPERIMENT2_SETUP_PATH.read_text(encoding="utf-8")
    if FILLED_EXAMPLE_HEADER in setup_text:
        return
    block = f"\n{FILLED_EXAMPLE_HEADER}\n\n```text\n{filled_prompt}\n```\n"
    EXPERIMENT2_SETUP_PATH.write_text(setup_text.rstrip() + block, encoding="utf-8")


def require_model_approval() -> None:
    """Exit when Step 3 approval is missing."""
    if APPROVAL_PATH.is_file():
        return
    raise SystemExit(
        "Full-cohort labeling requires written approval of "
        f"{COST_ESTIMATE_RELATIVE_PATH} and "
        "experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md. "
        f"Create {APPROVAL_RELATIVE_PATH} after approval."
    )


def require_experiment6_model_approval() -> None:
    """Exit when experiment 6 cost approval is missing."""
    if EXPERIMENT6_APPROVAL_PATH.is_file():
        return
    raise SystemExit(
        "Experiment 6 full-cohort labeling requires written approval of "
        f"{EXPERIMENT6_COST_ESTIMATE_RELATIVE_PATH}. "
        f"Create {EXPERIMENT6_APPROVAL_RELATIVE_PATH} after approval."
    )


def labeling_spec(experiment_number: int, engine_type: str) -> FeatureSpec:
    """Return the feature spec for one experiment's labeling grain."""
    if experiment_number == 6:
        return pair_yes_no_spec(engine_type)  # type: ignore[arg-type]
    return remove_indexes_spec(engine_type)  # type: ignore[arg-type]


def scored_and_failed_users(
    ordered_ids: list[str],
    failed_ids: list[str] | set[str],
) -> tuple[int, int]:
    """Return scored and failed user counts from pair ids."""
    expected_by_user: dict[str, set[int]] = defaultdict(set)
    for record_id in ordered_ids:
        prolific_id, pair_index = parse_pair_record_id(record_id)
        expected_by_user[prolific_id].add(pair_index)
    failed_by_user: dict[str, set[int]] = defaultdict(set)
    for record_id in failed_ids:
        prolific_id, pair_index = parse_pair_record_id(record_id)
        failed_by_user[prolific_id].add(pair_index)
    expected_indexes = set(range(1, POSTS_PER_USER + 1))
    scored_users = 0
    for prolific_id, indexes in expected_by_user.items():
        if indexes == expected_indexes and not failed_by_user[prolific_id]:
            scored_users += 1
    return scored_users, len(expected_by_user) - scored_users


def model_command(experiment_number: int, model_folder: str) -> None:
    """Label the full cohort for one experiment and model."""
    if experiment_number == 6:
        require_experiment6_model_approval()
    else:
        require_model_approval()
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    users = select_all_users(load_cohort_users())
    trials_by_user = load_cohort_trials_by_user()
    summary = run_model_labeling(
        store,
        experiment_number,
        model_folder,
        users,
        trials_by_user,
    )
    print_model_summary(experiment_number, model_folder, summary)


def run_model_labeling(
    store: CampaignObjectStore,
    experiment_number: int,
    model_folder: str,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> dict[str, Any]:
    """Label every cohort user for one experiment and model."""
    setup = _full_label_setup(
        store, experiment_number, model_folder, users, trials_by_user
    )
    if setup["manifest"].get("final_parquet"):
        print(FINAL_EXISTS_MESSAGE)
        return complete_label_summary(store, setup, experiment_number)
    return _label_and_consolidate_full_cohort(store, setup, model_folder, experiment_number)


def _full_label_setup(
    store: CampaignObjectStore,
    experiment_number: int,
    model_folder: str,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> dict[str, Any]:
    """Load manifest and inputs for one full-cohort labeling run."""
    paths = full_feature_paths(experiment_number, model_folder)
    engine_type = FULL_MODEL_ENGINE_TYPES[model_folder]
    spec = labeling_spec(experiment_number, engine_type)
    campaign = campaign_config_for_experiment(experiment_number)
    ordered_ids, texts = ordered_full_input(experiment_number, users, trials_by_user)
    run_id = run_id_for_feature(campaign.campaign_id, spec.name)
    manifest, manifest_etag = load_or_create_manifest(
        store,
        paths,
        campaign,
        spec,
        expected_row_count=len(ordered_ids),
        engine_type=engine_type,
    )
    return {
        "paths": paths,
        "spec": spec,
        "ordered_ids": ordered_ids,
        "texts": texts,
        "run_id": run_id,
        "manifest": manifest,
        "manifest_etag": manifest_etag,
    }


def _label_and_consolidate_full_cohort(
    store: CampaignObjectStore,
    setup: dict[str, Any],
    model_folder: str,
    experiment_number: int,
) -> dict[str, Any]:
    """Label missing parts and consolidate one full-cohort prefix."""
    manifest_etag = label_full_parts(
        store,
        setup["paths"],
        setup["manifest"],
        setup["manifest_etag"],
        setup["spec"],
        model_folder,
        setup["ordered_ids"],
        setup["texts"],
        setup["run_id"],
    )
    consolidate_final(
        store,
        setup["paths"],
        setup["manifest"],
        manifest_etag,
        expected_ids=setup["ordered_ids"],
        failed_ids=read_failed_ids(store, setup["paths"]),
        spec=setup["spec"],
        run_id=setup["run_id"],
    )
    return complete_label_summary(store, setup, experiment_number)


def label_full_parts(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    model_folder: str,
    ordered_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    """Label every part that is not already in the manifest."""
    written_parts = {int(entry["part_index"]) for entry in manifest["batches"]}
    for part_index, chunk_ids in enumerate(_chunks(ordered_ids, CAMPAIGN_BATCH_SIZE)):
        if part_index in written_parts:
            continue
        manifest_etag = label_full_part(
            store,
            paths,
            manifest,
            manifest_etag,
            spec,
            model_folder,
            part_index,
            chunk_ids,
            texts,
            run_id,
        )
    return manifest_etag


def label_full_part(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    model_folder: str,
    part_index: int,
    chunk_ids: list[str],
    texts: dict[str, str],
    run_id: str,
) -> str:
    """Label one full-cohort part when it is not already recorded."""
    adopted = adopt_unrecorded_batch(
        store, paths, manifest, manifest_etag, part_index=part_index, run_id=run_id
    )
    if adopted is not None:
        return adopted.manifest_etag
    tasks = [LabelTask(uri=record_id, text=texts[record_id]) for record_id in chunk_ids]
    rows, failures = call_full_label_fn(model_folder, spec, tasks)
    return _persist_full_part_rows(
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        model_folder,
        part_index,
        chunk_ids,
        rows,
        failures,
        run_id,
    )


def _persist_full_part_rows(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    spec: FeatureSpec,
    model_folder: str,
    part_index: int,
    chunk_ids: list[str],
    rows: list[dict],
    failures: list[RecordLabelFailure],
    run_id: str,
) -> str:
    """Write one full-cohort batch and append any label failures."""
    manifest_etag = write_smoke_rows(
        store,
        paths,
        manifest,
        manifest_etag,
        spec,
        part_index,
        chunk_ids,
        rows,
        run_id,
        model_folder,
    )
    if failures:
        append_errors(store, paths, error_records(failures, run_id, part_index))
    return manifest_etag


def call_full_label_fn(
    model_folder: str,
    spec: FeatureSpec,
    tasks: list[LabelTask],
) -> tuple[list[dict], list[RecordLabelFailure]]:
    """Dispatch to the OpenAI or Bedrock full-cohort label function."""
    if model_folder == MODEL_FOLDER_OPENAI:
        return openai_runner.label_tasks(spec, tasks)
    return bedrock_runner.label_tasks(spec, tasks, MODEL_IDS[model_folder])


def complete_label_summary(
    store: CampaignObjectStore,
    setup: dict[str, Any],
    experiment_number: int,
) -> dict[str, Any]:
    """Summarize labeled rows and, for experiment 6, scored users."""
    summary = label_summary_from_store(
        store, setup["paths"], len(setup["ordered_ids"])
    )
    if experiment_number != 6:
        return summary
    failed_ids = read_failed_ids(store, setup["paths"])
    scored_users, failed_users = scored_and_failed_users(
        setup["ordered_ids"], failed_ids
    )
    summary["scored_users"] = scored_users
    summary["failed_users"] = failed_users
    return summary


def label_summary_from_store(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    expected: int,
) -> dict[str, Any]:
    """Summarize labeled and failed counts for one full-cohort prefix."""
    failed_ids = read_failed_ids(store, paths)
    return {
        "labeled": expected - len(failed_ids),
        "failed": len(failed_ids),
        "final_uri": paths.uri(paths.final_key),
    }


def print_model_summary(
    experiment_number: int,
    model_folder: str,
    summary: dict[str, Any],
) -> None:
    """Print per-model full-cohort stdout lines."""
    print(f"experiment={experiment_number}")
    print(f"model={model_folder}")
    if experiment_number == 6:
        print(f"labeled_pairs={summary['labeled']}")
        print(f"failed_pairs={summary['failed']}")
        print(f"scored_users={summary['scored_users']}")
        print(f"failed_users={summary['failed_users']}")
    else:
        print(f"labeled={summary['labeled']}")
        print(f"failed={summary['failed']}")
    print(f"final_uri={summary['final_uri']}")


def select_all_users(users: tuple[CohortUser, ...]) -> tuple[CohortUser, ...]:
    """Return unique cohort users in cohort order, keeping the earliest session."""
    ordered = sorted(users, key=lambda user: (user.source_file_epoch_ms, user.prolific_id))
    seen: set[str] = set()
    unique: list[CohortUser] = []
    for user in ordered:
        if user.prolific_id in seen:
            continue
        seen.add(user.prolific_id)
        unique.append(user)
    return tuple(unique)


def reject_experiment6_claude(experiment_number: int, model_folder: str) -> None:
    """Exit when experiment 6 is asked to label with Claude."""
    if experiment_number == 6 and model_folder == MODEL_FOLDER_BEDROCK_CLAUDE:
        raise SystemExit("Claude is excluded from experiment 6")


def ordered_full_input(
    experiment_number: int,
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> tuple[list[str], dict[str, str]]:
    """Return full-cohort ids and rendered prompts for one experiment."""
    if experiment_number == 6:
        return ordered_pair_input(users, trials_by_user)
    ids = [user.prolific_id for user in users]
    texts = {
        user.prolific_id: render_user_prompt(
            experiment_number,
            user,
            trials_by_user[user.prolific_id],
        )
        for user in users
    }
    return ids, texts


def ordered_pair_input(
    users: tuple[CohortUser, ...],
    trials_by_user: dict[str, list[CohortTrial]],
) -> tuple[list[str], dict[str, str]]:
    """Return one record id and one-pair prompt per user-pair."""
    ids: list[str] = []
    texts: dict[str, str] = {}
    for user in users:
        for trial in unique_pair_trials(trials_by_user[user.prolific_id]):
            record_id = pair_record_id(user.prolific_id, trial.pair_index)
            ids.append(record_id)
            texts[record_id] = render_single_pair(trial)
    return ids, texts


def unique_pair_trials(trials: list[CohortTrial]) -> list[CohortTrial]:
    """Return pair_index 1 to 20, keeping the earliest trial for duplicates."""
    by_index: dict[int, CohortTrial] = {}
    for trial in sorted(trials, key=lambda item: item.trial_index):
        if trial.pair_index not in by_index:
            by_index[trial.pair_index] = trial
    return [by_index[index] for index in sorted(by_index)[:POSTS_PER_USER]]


def full_labels_root_uri(experiment_number: int) -> str:
    """Return the S3 root for one experiment's model outputs."""
    return (
        f"s3://{OUTPUT_S3_BUCKET}/{EXPERIMENT_S3_PREFIX}"
        f"experiment{experiment_number}/outputs/"
    )


def full_feature_paths(experiment_number: int, model_folder: str) -> FeaturePaths:
    """Return FeaturePaths for one experiment and model full-cohort prefix."""
    return FeaturePaths.from_root_uri(full_labels_root_uri(experiment_number), model_folder)


def campaign_config_for_experiment(experiment_number: int) -> CampaignRunConfig:
    """Return the campaign config for one experiment's full-cohort labeling."""
    return CampaignRunConfig(
        campaign_id=f"{CAMPAIGN_ID}_experiment{experiment_number}",
        dataset_id=DATASET_ID,
        preprocessed_run=PREPROCESSED_RUN,
        platform=CAMPAIGN_PLATFORM,
        batch_size=CAMPAIGN_BATCH_SIZE,
    )


def _chunks(ids: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(ids), size):
        yield ids[start : start + size]


def analyze_errors_command() -> None:
    """Rank false negatives, false positives, and lowest-F1 users."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    all_users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    result = run_error_analysis(store, all_users, trials_by_user)
    print_error_analysis_summary(result)


def score_command(experiment_number: int) -> None:
    """Score labeled models for one experiment and write RESULTS.md."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    if experiment_number == 6:
        score_experiment6_command(store)
        return
    for model_folder in MODEL_ORDER:
        paths = full_feature_paths(experiment_number, model_folder)
        if store.get(paths.final_key) is None:
            raise SystemExit(paths.uri(paths.final_key))
    all_users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    result = score_experiment(experiment_number, all_users, trials_by_user, store)
    print_score_tables(result)
    results_s3_uri = write_results_md(result, store)
    print(f"results_s3_uri={results_s3_uri}")


def score_experiment6_command(store: CampaignObjectStore) -> None:
    """Score experiment 6 three-model finals and write RESULTS.md."""
    for model_folder in EXPERIMENT6_MODEL_ORDER:
        paths = full_feature_paths(6, model_folder)
        if store.get(paths.final_key) is None:
            raise SystemExit(paths.uri(paths.final_key))
    all_users = load_cohort_users()
    trials_by_user = load_cohort_trials_by_user()
    result = score_experiment6(all_users, trials_by_user, store)
    print_experiment6_score_tables(result)
    results_s3_uri = write_experiment6_results_md(result, store)
    print(f"results_s3_uri={results_s3_uri}")


def update_experiment1_setup(smoke_user_count: int) -> None:
    """Record smoke user count and smoke URIs in experiment1 SETUP.md."""
    lines = [
        "",
        "## Smoke (Step 2)",
        "",
        f"Smoke user count: {smoke_user_count}",
        "",
        "Smoke S3 prefixes:",
        "",
    ]
    for model_folder in MODEL_ORDER:
        paths = smoke_feature_paths(model_folder)
        lines.append(f"- `{model_folder}`: `{paths.uri(paths.prefix)}`")
    lines.append("")
    setup_text = EXPERIMENT1_SETUP_PATH.read_text(encoding="utf-8")
    marker = "## Smoke (Step 2)"
    if marker in setup_text:
        return
    EXPERIMENT1_SETUP_PATH.write_text(setup_text.rstrip() + "\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    """Dispatch shared runner commands."""
    args = parse_args(argv)
    if args.write_cohort:
        write_cohort_command()
        return
    if args.smoke:
        if args.experiment == 6:
            experiment6_smoke_command()
            return
        smoke_command()
        users = load_cohort_users()
        update_experiment1_setup(len(select_smoke_users(users)))
        return
    if args.estimate_cost:
        if args.experiment == 6:
            experiment6_estimate_cost_command()
            return
        estimate_cost_command()
        return
    if args.print_experiment_2_prompt:
        print_experiment_2_prompt_command()
        return
    if args.model:
        if args.experiment is None:
            raise SystemExit("--model requires --experiment")
        reject_experiment6_claude(args.experiment, args.model)
        if args.experiment == 6:
            model_command(args.experiment, args.model)
            return
        if args.experiment not in (1, 2, 3, 4):
            raise SystemExit("--model supports experiments 1 through 4 only")
        model_command(args.experiment, args.model)
        return
    if args.score:
        if args.experiment is None:
            raise SystemExit("--score requires --experiment")
        if args.experiment == 6:
            score_command(6)
            return
        if args.experiment not in (1, 2, 3, 4):
            raise SystemExit("--score supports experiments 1 through 4 only")
        score_command(args.experiment)
        return
    if args.analyze_errors:
        analyze_errors_command()
        return
    if args.experiment == 5:
        raise SystemExit("experiment5 supports --analyze-errors only")
    if args.experiment == 6:
        raise SystemExit(
            "experiment 6 requires --smoke, --estimate-cost, --model, or --score"
        )
    raise SystemExit("No command selected")


if __name__ == "__main__":
    main()
