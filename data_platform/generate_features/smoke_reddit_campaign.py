"""Ten-comment smoke for one feature of the Reddit LLM campaign, with interrupt-and-resume.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \\
        --campaign-id reddit_2026_09_03_233928_llm_features_v1 \\
        --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \\
        --preprocessed-run 2026_09_03-23:39:28 \\
        --feature is_political

Pass ``--smoke-prefix s3://bucket/root/`` to write under ``root/{feature}/smoke/``
instead of the primary campaign feature prefix.
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.generate_features.campaign_cost_report import (
    RequestUsage,
    build_feature_cost_report,
    pricing_for_engine_type,
)
from data_platform.generate_features.campaign_engine_map import (
    BEDROCK_ENGINE_TYPE,
    OPENAI_ENGINE_TYPE,
    campaign_engine_type,
)
from data_platform.generate_features.deterministic_smoke_sample import (
    SMOKE_POST_COUNT,
    load_deterministic_ten_posts_for_spec,
)
from data_platform.generate_features.engines.bedrock_engine import (
    BedrockConverseEngine,
    BedrockRuntimeClient,
    create_bedrock_runtime_client,
)
from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchClient,
    create_openai_client,
)
from data_platform.generate_features.generate_reddit_features import REDDIT_SPEC
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.generate_features.s3_feature_batches import attach_row_metadata
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    run_id_for_feature,
)
from data_platform.generate_features.smoke_bluesky_campaign import (
    CHECK_CANONICAL_TOUCHED,
    CHECK_NO_BATCHES,
    CHECK_RESUME_EVIDENCE_OK,
    CHECK_SMOKE_OUTPUT_OK,
    CountingOpenAIClient,
    InterruptedJob,
    ResumedJob,
    SmokePaths,
    SmokeResult,
    _tasks,
    build_resume_evidence,
    checks_passed,
    resume_and_collect_rows,
    run_s3_checks,
    submit_and_interrupt,
    write_git_copies,
    write_smoke_objects,
)
from lib.constants import DEFAULT_BEDROCK_NOVA_MICRO, REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

logger = logging.getLogger(__name__)

REDDIT_PLATFORM = "reddit"
FULL_RUN_ROW_COUNT = 400_000
DEFAULT_SMOKE_REPORTS_DIR = (
    REPO_ROOT
    / "docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke"
)
CONVERSE_CALL = "converse"
BEDROCK_SMOKE_BATCH_ID = "bedrock-smoke"
BEDROCK_REQUEST_ID_PREFIX = "bedrock-"
BEDROCK_REQUEST_ID_WIDTH = 5
BEDROCK_SMOKE_ATTEMPT_COUNT = 1
BEDROCK_SMOKE_MAX_CONCURRENCY = 8
BEDROCK_STATE_FILENAME = "bedrock_smoke_state.json"
CHECK_PRIMARY_TOUCHED = "primary_smoke_prefix_touched"
JSON_INDENT = 2


@dataclass(frozen=True)
class BedrockSmokeJob:
    """Rows, usage, and converse counts from one Bedrock smoke engine."""

    rows: list[dict[str, Any]]
    request_usages: list[RequestUsage]
    last_usage: dict[str, int]
    converse_calls: int
    stamped_at: str


class CountingBedrockClient:
    """Bedrock Runtime wrapper that counts ``converse`` calls and stores per-call usage."""

    def __init__(self, client: BedrockRuntimeClient) -> None:
        self._client = client
        self._lock = threading.Lock()
        self.calls: Counter[str] = Counter()
        self.usages: list[tuple[str, int, int]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        response = self._client.converse(**kwargs)
        user_text = kwargs["messages"][0]["content"][0]["text"]
        usage = response.get("usage") or {}
        with self._lock:
            self.calls[CONVERSE_CALL] += 1
            self.usages.append(
                (
                    str(user_text),
                    int(usage.get("inputTokens", 0)),
                    int(usage.get("outputTokens", 0)),
                )
            )
        return response


def build_reddit_smoke_paths(
    campaign_id: str, dataset_id: str, feature: str, smoke_prefix: str | None
) -> SmokePaths:
    """Return primary Reddit feature paths, or paths under ``smoke_prefix`` when it is given.

    Raises
    ------
    ValueError
        When ``smoke_prefix`` is not an ``s3://`` URI, or when it overlaps the
        primary feature prefix.
    """
    primary = FeaturePaths.for_campaign(
        campaign_id,
        feature,
        platform=REDDIT_PLATFORM,
        dataset_id=dataset_id,
    )
    if smoke_prefix is None:
        return SmokePaths(
            paths=primary,
            canonical=primary,
            smoke_prefix_uri=primary.uri(primary.smoke_prefix),
        )
    paths = FeaturePaths.from_root_uri(smoke_prefix, feature)
    same_bucket = paths.bucket == primary.bucket
    overlaps = paths.prefix.startswith(primary.prefix) or primary.prefix.startswith(
        paths.prefix
    )
    if same_bucket and overlaps:
        raise ValueError(
            f"smoke prefix {smoke_prefix!r} overlaps the primary feature prefix "
            f"{primary.uri(primary.prefix)}"
        )
    return SmokePaths(paths=paths, canonical=primary, smoke_prefix_uri=smoke_prefix)


def _bedrock_request_ids(ordered_ids: list[str]) -> dict[str, str]:
    return {
        source_record_id: f"{BEDROCK_REQUEST_ID_PREFIX}{index:0{BEDROCK_REQUEST_ID_WIDTH}d}"
        for index, source_record_id in enumerate(ordered_ids)
    }


def _usages_for_tasks(
    client: CountingBedrockClient, tasks: list[LabelTask]
) -> list[RequestUsage]:
    last_by_text: dict[str, tuple[int, int]] = {}
    for text, input_tokens, output_tokens in client.usages:
        last_by_text[text] = (input_tokens, output_tokens)
    usages: list[RequestUsage] = []
    request_ids = _bedrock_request_ids([task.uri for task in tasks])
    for task in tasks:
        tokens = last_by_text.get(task.text)
        if tokens is None:
            raise RuntimeError(f"no Bedrock usage captured for {task.uri}")
        input_tokens, output_tokens = tokens
        usages.append(
            RequestUsage(
                source_record_id=task.uri,
                request_id=request_ids[task.uri],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
    return usages


def _write_bedrock_state(path: Path, job: BedrockSmokeJob) -> None:
    document = {
        "rows": job.rows,
        "request_usages": [asdict(usage) for usage in job.request_usages],
        "last_usage": job.last_usage,
        "converse_calls": job.converse_calls,
        "stamped_at": job.stamped_at,
    }
    path.write_text(f"{json.dumps(document, indent=JSON_INDENT)}\n", encoding="utf-8")


def _read_bedrock_state(path: Path) -> BedrockSmokeJob:
    document = json.loads(path.read_text(encoding="utf-8"))
    return BedrockSmokeJob(
        rows=document["rows"],
        request_usages=[RequestUsage(**payload) for payload in document["request_usages"]],
        last_usage=document["last_usage"],
        converse_calls=int(document["converse_calls"]),
        stamped_at=document["stamped_at"],
    )


def submit_bedrock_and_interrupt(
    client: CountingBedrockClient,
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_id: str,
    state_path: Path,
) -> BedrockSmokeJob:
    """Label the ten comments through Converse, save rows locally, and stop before S3 writes."""
    tasks = _tasks(posts)
    engine = BedrockConverseEngine(
        spec,
        FeatureRunConfig(
            batch_size=len(tasks),
            max_concurrency=BEDROCK_SMOKE_MAX_CONCURRENCY,
        ),
        client,
        DEFAULT_BEDROCK_NOVA_MICRO,
    )
    labels = engine.batch_label_records(tasks)
    if engine.last_usage is None:
        raise RuntimeError("Bedrock engine reported no usage after labeling")
    ordered_ids = [task.uri for task in tasks]
    rows = attach_row_metadata(
        labels,
        run_id=run_id,
        batch_id=BEDROCK_SMOKE_BATCH_ID,
        request_ids=_bedrock_request_ids(ordered_ids),
        attempt_count=BEDROCK_SMOKE_ATTEMPT_COUNT,
    )
    job = BedrockSmokeJob(
        rows=rows,
        request_usages=_usages_for_tasks(client, tasks),
        last_usage={
            "input_tokens": engine.last_usage.input_tokens,
            "output_tokens": engine.last_usage.output_tokens,
            "total_tokens": engine.last_usage.total_tokens,
        },
        converse_calls=int(client.calls[CONVERSE_CALL]),
        stamped_at=get_current_timestamp(),
    )
    _write_bedrock_state(state_path, job)
    logger.info(
        "Deliberate smoke interruption after Bedrock Converse",
        extra={"feature_name": spec.name, "converse_calls": job.converse_calls},
    )
    return job


def resume_bedrock_from_state(state_path: Path, client: CountingBedrockClient) -> BedrockSmokeJob:
    """Return the saved Bedrock rows without making another Converse call."""
    if int(client.calls[CONVERSE_CALL]) != 0:
        raise RuntimeError("resume Bedrock client already made a converse call")
    return _read_bedrock_state(state_path)


def build_bedrock_resume_evidence(
    *,
    feature: str,
    run_id: str,
    interrupted: BedrockSmokeJob,
    resumed: BedrockSmokeJob,
    resume_converse_calls: int,
) -> dict[str, Any]:
    """Return the interrupt-and-resume proof for a Bedrock smoke run."""
    same_rows = len(resumed.rows) == SMOKE_POST_COUNT
    no_new_jobs = resume_converse_calls == 0
    return {
        "feature": feature,
        "run_id": run_id,
        "batch_id": BEDROCK_SMOKE_BATCH_ID,
        "input_file_id": None,
        "interrupted_at": interrupted.stamped_at,
        "resumed_at": get_current_timestamp(),
        "submit_calls_before_interrupt": {CONVERSE_CALL: interrupted.converse_calls},
        "submit_calls_after_resume": {CONVERSE_CALL: resume_converse_calls},
        "reattached_same_batch_id": True,
        "rows_written": len(resumed.rows),
        "provider_batch_ids_in_output": sorted(
            {str(row["batch_id"]) for row in resumed.rows}
        ),
        "resume_ok": no_new_jobs and same_rows,
    }


def _label_openai_with_interrupt(
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_id: str,
    run_dir: Path,
    client_factory: Callable[[], OpenAIBatchClient],
) -> tuple[InterruptedJob, ResumedJob]:
    interrupted = submit_and_interrupt(
        CountingOpenAIClient(client_factory()), spec, posts, run_dir=run_dir
    )
    resumed = resume_and_collect_rows(
        CountingOpenAIClient(client_factory()), spec, posts, run_dir=run_dir, run_id=run_id
    )
    return interrupted, resumed


def _openai_cost_and_evidence(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    run_id: str,
    smoke_uri: str,
    interrupted: InterruptedJob,
    resumed: ResumedJob,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cost_report = build_feature_cost_report(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        model=DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
        engine_type=OPENAI_ENGINE_TYPE,
        smoke_uri=smoke_uri,
        batch_id=interrupted.state["batch_id"],
        batch_usage=resumed.last_batch.usage,
        request_usages=resumed.request_usages,
        pricing=pricing_for_engine_type(OPENAI_ENGINE_TYPE),
        full_run_row_count=FULL_RUN_ROW_COUNT,
    )
    resume_evidence = build_resume_evidence(
        feature=feature, run_id=run_id, interrupted=interrupted, resumed=resumed
    )
    return cost_report, resume_evidence


def _label_bedrock_with_interrupt(
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_id: str,
    run_dir: Path,
    client_factory: Callable[[], BedrockRuntimeClient],
) -> tuple[BedrockSmokeJob, BedrockSmokeJob, int]:
    state_path = run_dir / BEDROCK_STATE_FILENAME
    interrupted = submit_bedrock_and_interrupt(
        CountingBedrockClient(client_factory()),
        spec,
        posts,
        run_id=run_id,
        state_path=state_path,
    )
    resume_client = CountingBedrockClient(client_factory())
    resumed = resume_bedrock_from_state(state_path, resume_client)
    return interrupted, resumed, int(resume_client.calls[CONVERSE_CALL])


def _bedrock_cost_and_evidence(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    run_id: str,
    smoke_uri: str,
    interrupted: BedrockSmokeJob,
    resumed: BedrockSmokeJob,
    resume_converse_calls: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cost_report = build_feature_cost_report(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        model=DEFAULT_BEDROCK_NOVA_MICRO,
        engine_type=BEDROCK_ENGINE_TYPE,
        smoke_uri=smoke_uri,
        batch_id=BEDROCK_SMOKE_BATCH_ID,
        batch_usage=None,
        request_usages=resumed.request_usages,
        pricing=pricing_for_engine_type(BEDROCK_ENGINE_TYPE),
        full_run_row_count=FULL_RUN_ROW_COUNT,
    )
    cost_report["batch_usage"] = resumed.last_usage
    resume_evidence = build_bedrock_resume_evidence(
        feature=feature,
        run_id=run_id,
        interrupted=interrupted,
        resumed=resumed,
        resume_converse_calls=resume_converse_calls,
    )
    return cost_report, resume_evidence


def run_campaign_smoke(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    smoke_prefix: str | None,
    output_dir: Path,
    openai_client_factory: Callable[[], OpenAIBatchClient] | None = None,
    bedrock_client_factory: Callable[[], BedrockRuntimeClient] | None = None,
) -> SmokeResult:
    """Label the ten smoke comments for ``feature`` with one deliberate interruption and resume.

    Raises
    ------
    ValueError
        When ``feature`` is missing from the registry or the campaign map, or
        ``smoke_prefix`` overlaps the primary feature prefix.
    RuntimeError
        When the resumed job leaves any of the ten comments without a valid row.
    """
    spec = FEATURE_REGISTRY.get(feature)
    if spec is None:
        raise ValueError(f"unknown feature {feature!r}")
    engine_type = campaign_engine_type(campaign_id, feature)
    smoke_paths = build_reddit_smoke_paths(campaign_id, dataset_id, feature, smoke_prefix)
    store = CampaignObjectStore(smoke_paths.paths.bucket)
    primary_smoke_keys_before = store.list_keys(smoke_paths.canonical.smoke_prefix)
    posts = load_deterministic_ten_posts_for_spec(REDDIT_SPEC, dataset_id, preprocessed_run)
    run_id = run_id_for_feature(campaign_id, feature)
    with tempfile.TemporaryDirectory(prefix="smoke_reddit_campaign_") as run_dir_name:
        run_dir = Path(run_dir_name)
        if engine_type == OPENAI_ENGINE_TYPE:
            interrupted_openai, resumed_openai = _label_openai_with_interrupt(
                spec,
                posts,
                run_id=run_id,
                run_dir=run_dir,
                client_factory=openai_client_factory or create_openai_client,
            )
            rows = resumed_openai.rows
            cost_report, resume_evidence = _openai_cost_and_evidence(
                campaign_id=campaign_id,
                dataset_id=dataset_id,
                preprocessed_run=preprocessed_run,
                feature=feature,
                run_id=run_id,
                smoke_uri=smoke_paths.paths.uri(smoke_paths.paths.smoke_prefix),
                interrupted=interrupted_openai,
                resumed=resumed_openai,
            )
        elif engine_type == BEDROCK_ENGINE_TYPE:
            interrupted_bedrock, resumed_bedrock, resume_calls = _label_bedrock_with_interrupt(
                spec,
                posts,
                run_id=run_id,
                run_dir=run_dir,
                client_factory=bedrock_client_factory or create_bedrock_runtime_client,
            )
            rows = resumed_bedrock.rows
            cost_report, resume_evidence = _bedrock_cost_and_evidence(
                campaign_id=campaign_id,
                dataset_id=dataset_id,
                preprocessed_run=preprocessed_run,
                feature=feature,
                run_id=run_id,
                smoke_uri=smoke_paths.paths.uri(smoke_paths.paths.smoke_prefix),
                interrupted=interrupted_bedrock,
                resumed=resumed_bedrock,
                resume_converse_calls=resume_calls,
            )
        else:
            raise ValueError(f"unsupported engine_type {engine_type!r}")
    write_smoke_objects(
        store,
        smoke_paths.paths,
        posts=posts,
        rows=rows,
        spec=spec,
        run_id=run_id,
        cost_report=cost_report,
        resume_evidence=resume_evidence,
    )
    checks, check_lines = run_s3_checks(
        store,
        smoke_paths,
        spec=spec,
        canonical_smoke_keys_before=primary_smoke_keys_before,
    )
    cost_report_path = write_git_copies(
        output_dir,
        feature,
        cost_report=cost_report,
        resume_evidence=resume_evidence,
        check_lines=check_lines,
    )
    return SmokeResult(
        smoke_prefix_uri=smoke_paths.smoke_prefix_uri,
        cost_report=cost_report,
        resume_evidence=resume_evidence,
        checks=checks,
        cost_report_path=cost_report_path,
    )


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def summary_lines(result: SmokeResult) -> list[str]:
    """Return the stdout lines of one Reddit smoke run, in the order the step spec fixes."""
    report = result.cost_report
    checks = result.checks
    return [
        f"smoke_prefix={result.smoke_prefix_uri}",
        f"engine_type={report['engine_type']}",
        f"smoke_rows={result.resume_evidence['rows_written']}",
        f"avg_input_tokens={report['avg_input_tokens_per_request']}",
        f"max_input_tokens={report['max_input_tokens_per_request']}",
        f"avg_output_tokens={report['avg_output_tokens_per_request']}",
        f"max_output_tokens={report['max_output_tokens_per_request']}",
        f"estimated_full_run_usd_avg={report['estimated_full_run_usd_avg']}",
        f"estimated_full_run_usd_max={report['estimated_full_run_usd_max']}",
        f"full_run_row_count={report['full_run_row_count']}",
        f"{CHECK_SMOKE_OUTPUT_OK}={str(checks[CHECK_SMOKE_OUTPUT_OK]).lower()}",
        f"{CHECK_RESUME_EVIDENCE_OK}={str(checks[CHECK_RESUME_EVIDENCE_OK]).lower()}",
        f"{CHECK_NO_BATCHES}={str(checks[CHECK_NO_BATCHES]).lower()}",
        f"{CHECK_PRIMARY_TOUCHED}={str(checks[CHECK_CANONICAL_TOUCHED]).lower()}",
        f"cost_report={_display_path(result.cost_report_path)}",
    ]


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str | None = typer.Option(None, "--smoke-prefix"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
) -> None:
    """Run the ten-comment smoke for one Reddit feature, print the summary, and exit 1 when an S3 check fails."""
    result = run_campaign_smoke(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        smoke_prefix=smoke_prefix,
        output_dir=output_dir or DEFAULT_SMOKE_REPORTS_DIR / feature,
    )
    for line in summary_lines(result):
        print(line)
    if not checks_passed(result.checks):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
