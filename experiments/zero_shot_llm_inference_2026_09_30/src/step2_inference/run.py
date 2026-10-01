"""Resumable per-model Bedrock inference for Study 2 zero-shot runs.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step2_inference.run --help
"""

from __future__ import annotations

import argparse

from data_platform.generate_features.engines.bedrock_engine import (
    BedrockRuntimeClient,
    create_bedrock_runtime_client,
)
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import DEFAULT_S3_REGION

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import EXPERIMENT_S3_BUCKET
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import apply_lab_aws_credentials_when_unset


def run_model_inference(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    run_id: str,
    model_folder: str,
    limit: int | None,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> None:
    """Execute one resumable inference pass for a single model folder."""
    _load_prepared_input(store)
    _load_resume_state(store, run_id, model_folder, limit)
    _run_pending_batches(
        store,
        client,
        run_id,
        model_folder,
        batch_size,
        max_concurrency,
        max_tokens,
    )
    _write_model_manifest(store, run_id, model_folder)


def _load_prepared_input(store: CampaignObjectStore) -> None:
    raise NotImplementedError


def _load_resume_state(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
    limit: int | None,
) -> None:
    raise NotImplementedError


def _run_pending_batches(
    store: CampaignObjectStore,
    client: BedrockRuntimeClient,
    run_id: str,
    model_folder: str,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
) -> None:
    raise NotImplementedError


def _write_model_manifest(
    store: CampaignObjectStore,
    run_id: str,
    model_folder: str,
) -> None:
    raise NotImplementedError


def main() -> None:
    """Parse CLI arguments and run one model inference task."""
    apply_lab_aws_credentials_when_unset()
    args = _parse_args()
    store = CampaignObjectStore(EXPERIMENT_S3_BUCKET, DEFAULT_S3_REGION)
    client = create_bedrock_runtime_client()
    run_model_inference(
        store,
        client,
        args.run_id,
        args.model,
        args.limit,
        args.batch_size,
        args.max_concurrency,
        args.max_tokens,
    )


def _parse_args() -> argparse.Namespace:
    raise NotImplementedError


if __name__ == "__main__":
    main()
