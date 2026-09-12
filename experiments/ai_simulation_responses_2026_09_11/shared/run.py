"""CLI entrypoint for the AI simulation responses experiment."""

from __future__ import annotations

import argparse

import boto3

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.ai_simulation_responses_2026_09_11.shared.cohort import (
    build_cohort,
    list_september_csv_keys,
)
from experiments.ai_simulation_responses_2026_09_11.shared.constants import OUTPUT_S3_BUCKET
from experiments.ai_simulation_responses_2026_09_11.shared.write import (
    require_cohort_keys_absent,
    upload_cohort,
)
from scripts.export_study_results import download_csvs


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
        choices=[
            "openai",
            "bedrock_micro_nova",
            "bedrock_qwen",
            "bedrock_claude",
        ],
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


def main(argv: list[str] | None = None) -> None:
    """Dispatch shared runner commands."""
    args = parse_args(argv)
    if args.write_cohort:
        write_cohort_command()
        return
    if args.smoke or args.estimate_cost or args.print_experiment_2_prompt:
        raise NotImplementedError
    if args.score or args.analyze_errors or args.experiment is not None:
        raise NotImplementedError
    raise SystemExit("No command selected")


if __name__ == "__main__":
    main()
