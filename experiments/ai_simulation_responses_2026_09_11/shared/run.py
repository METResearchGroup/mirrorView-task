"""CLI entrypoint for the AI simulation responses experiment."""

from __future__ import annotations

import argparse
from collections import defaultdict
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
    EXPERIMENT_S3_PREFIX,
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_BEDROCK_MICRO_NOVA,
    MODEL_FOLDER_BEDROCK_QWEN,
    MODEL_FOLDER_OPENAI,
    OUTPUT_S3_BUCKET,
    SMOKE_USER_COUNT,
)
from experiments.ai_simulation_responses_2026_09_11.shared.cost import (
    COST_ESTIMATE_RELATIVE_PATH,
    MODEL_ORDER,
    TokenUsageRecord,
    build_cost_estimate_markdown,
    build_experiment_sections,
    load_medians_by_model,
    load_token_usage,
    median_tokens,
    save_token_usage,
    token_usage_records_from_bedrock,
    token_usage_records_from_openai,
    upload_cost_estimate,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import (
    STUDY_SYSTEM_PROMPT,
    render_user_prompt,
)
from experiments.ai_simulation_responses_2026_09_11.shared.schema import remove_indexes_spec
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
FILLED_EXAMPLE_HEADER = "## Filled example (first cohort user)"

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
    parser.add_argument("--experiment", type=int, choices=[1, 2, 3, 4, 5])
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
    run_id = run_id_for_feature(campaign.campaign_id, SMOKE_FEATURE_NAME)
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
    if any(int(entry["part_index"]) == part_index for entry in manifest["batches"]):
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


def load_cohort_users() -> tuple[CohortUser, ...]:
    """Load cohort users from local parquet."""
    path = REPO_ROOT / COHORT_USERS_KEY
    if not path.exists():
        raise FileNotFoundError(f"Missing cohort users parquet: {path}")
    frame = pd.read_parquet(path)
    return tuple(CohortUser(**row) for row in frame.to_dict(orient="records"))


def load_cohort_trials_by_user() -> dict[str, list[CohortTrial]]:
    """Load cohort trials grouped by prolific id."""
    path = REPO_ROOT / COHORT_TRIALS_KEY
    if not path.exists():
        raise FileNotFoundError(f"Missing cohort trials parquet: {path}")
    frame = pd.read_parquet(path)
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
        smoke_command()
        users = load_cohort_users()
        update_experiment1_setup(len(select_smoke_users(users)))
        return
    if args.estimate_cost:
        estimate_cost_command()
        return
    if args.print_experiment_2_prompt:
        print_experiment_2_prompt_command()
        return
    if args.score or args.analyze_errors or args.experiment is not None:
        raise NotImplementedError
    raise SystemExit("No command selected")


if __name__ == "__main__":
    main()
