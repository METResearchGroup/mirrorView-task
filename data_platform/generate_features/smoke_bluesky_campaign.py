"""Ten-post smoke for one feature of a Bluesky LLM campaign, with an interrupt-and-resume proof.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \\
        --preprocessed-run 2026_09_03-23:51:30 \\
        --feature is_news_or_opinion

Pass ``--smoke-prefix s3://bucket/root/`` to write under ``root/{feature}/smoke/``
instead of the canonical campaign feature prefix.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import typer

from data_platform.generate_features.campaign_cost_report import (
    COST_REPORT_SUFFIX,
    DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS,
    DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_SOURCE_URL,
    BatchPricing,
    RequestUsage,
    build_feature_cost_report,
    request_usages_from_output_text,
)
from data_platform.generate_features.deterministic_smoke_sample import (
    SMOKE_POST_COUNT,
    load_deterministic_ten_posts,
)
from data_platform.generate_features.engines.openai_engine import (
    CUSTOM_ID_INDEX_WIDTH,
    CUSTOM_ID_PREFIX,
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchClient,
    OpenAIBatchEngine,
    create_openai_client,
    submit_active_batch,
)
from data_platform.generate_features.generate_features import CAMPAIGN_ENGINE_TYPE
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from data_platform.generate_features.openai_batch_state import load_active_batch_state
from data_platform.generate_features.registry import FEATURE_REGISTRY
from data_platform.generate_features.s3_feature_batches import (
    attach_provenance,
    parquet_rows,
    q44_columns,
    rows_to_parquet_bytes,
    validate_q44_rows,
)
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    run_id_for_feature,
)
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
    STANDARDIZED_TEXT_COLUMN,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

logger = logging.getLogger(__name__)

DEFAULT_SMOKE_REPORTS_DIR = (
    REPO_ROOT / "docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke"
)
FILES_CREATE_CALL = "files.create"
BATCHES_CREATE_CALL = "batches.create"
SMOKE_BATCH_INDEX = 0
SMOKE_ATTEMPT_COUNT = 1
RESUME_EVIDENCE_SUFFIX = "_resume_evidence.json"
S3_CHECKS_SUFFIX = "_s3_checks.txt"
JSON_INDENT = 2
CHECK_SMOKE_OBJECTS_UNTAGGED = "smoke_objects_exist_untagged"
CHECK_SMOKE_OUTPUT_OK = "s3_smoke_output_ok"
CHECK_RESUME_EVIDENCE_OK = "s3_smoke_resume_evidence_ok"
CHECK_NO_BATCHES = "no_batches_prefix_objects"
CHECK_CANONICAL_TOUCHED = "canonical_smoke_prefix_touched"


class _CountingNamespace:
    """Delegates to ``client.files`` or ``client.batches`` and counts ``create`` calls."""

    def __init__(self, target: Any, calls: Counter[str], call_name: str) -> None:
        self._target = target
        self._calls = calls
        self._call_name = call_name

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._target, name)
        if name != "create":
            return attribute

        def counted_create(*args: Any, **kwargs: Any) -> Any:
            self._calls[self._call_name] += 1
            return attribute(*args, **kwargs)

        return counted_create


class CountingOpenAIClient:
    """OpenAI client wrapper whose ``calls`` counter records every upload and batch creation."""

    def __init__(self, client: OpenAIBatchClient) -> None:
        self.calls: Counter[str] = Counter()
        self.files: Any = _CountingNamespace(client.files, self.calls, FILES_CREATE_CALL)
        self.batches: Any = _CountingNamespace(client.batches, self.calls, BATCHES_CREATE_CALL)


@dataclass(frozen=True)
class SmokePaths:
    """Smoke paths in use plus the canonical paths they must not overlap."""

    paths: FeaturePaths
    canonical: FeaturePaths
    smoke_prefix_uri: str


@dataclass(frozen=True)
class InterruptedJob:
    """The provider job state saved before the deliberate interruption, and the calls it took."""

    state: dict[str, Any]
    submit_calls: dict[str, int]
    interrupted_at: str


@dataclass(frozen=True)
class ResumedJob:
    """Rows and usage collected by the engine that reattached to the interrupted job."""

    rows: list[dict[str, Any]]
    request_usages: list[RequestUsage]
    engine: OpenAIBatchEngine
    resume_calls: dict[str, int]
    resumed_at: str


@dataclass(frozen=True)
class SmokeResult:
    """Everything one smoke run produced, for printing and for the Git copies."""

    smoke_prefix_uri: str
    cost_report: dict[str, Any]
    resume_evidence: dict[str, Any]
    checks: dict[str, bool]
    cost_report_path: Path


def build_smoke_paths(
    campaign_id: str, dataset_id: str, feature: str, smoke_prefix: str | None
) -> SmokePaths:
    """Return the canonical feature paths, or paths under ``smoke_prefix`` when it is given.

    Raises
    ------
    ValueError
        When ``smoke_prefix`` is not an ``s3://`` URI, or when it lands on or
        inside the canonical feature prefix, or contains it.
    """
    canonical = FeaturePaths.canonical(campaign_id, feature, dataset_id=dataset_id)
    if smoke_prefix is None:
        return SmokePaths(
            paths=canonical,
            canonical=canonical,
            smoke_prefix_uri=canonical.uri(canonical.smoke_prefix),
        )
    paths = FeaturePaths.from_root_uri(smoke_prefix, feature)
    same_bucket = paths.bucket == canonical.bucket
    overlaps = paths.prefix.startswith(canonical.prefix) or canonical.prefix.startswith(
        paths.prefix
    )
    if same_bucket and overlaps:
        raise ValueError(
            f"smoke prefix {smoke_prefix!r} overlaps the canonical feature prefix "
            f"{canonical.uri(canonical.prefix)}"
        )
    return SmokePaths(paths=paths, canonical=canonical, smoke_prefix_uri=smoke_prefix)


def _tasks(posts: pd.DataFrame) -> list[LabelTask]:
    return [
        LabelTask(
            uri=str(row[STANDARDIZED_SOURCE_RECORD_ID_COLUMN]),
            text=str(row[STANDARDIZED_TEXT_COLUMN]),
        )
        for _, row in posts.iterrows()
    ]


def _submit_calls(client: CountingOpenAIClient) -> dict[str, int]:
    return {name: client.calls[name] for name in (FILES_CREATE_CALL, BATCHES_CREATE_CALL)}


def submit_and_interrupt(
    client: CountingOpenAIClient,
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_dir: Path,
) -> InterruptedJob:
    """Upload the ten requests, create one provider batch, save its ``polling`` state, and stop.

    Stopping here, with the state file on disk and no poll made, is the
    deliberate interruption. The caller discards ``client`` afterwards.
    """
    state = submit_active_batch(
        client,
        spec,
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        _tasks(posts),
        run_dir=run_dir,
        feature_name=spec.name,
        batch_index=SMOKE_BATCH_INDEX,
        attempt_count=SMOKE_ATTEMPT_COUNT,
    )
    logger.info(
        "Deliberate smoke interruption after provider submit",
        extra={"batch_id": state["batch_id"], "feature_name": spec.name},
    )
    return InterruptedJob(
        state=state,
        submit_calls=_submit_calls(client),
        interrupted_at=get_current_timestamp(),
    )


def resume_and_collect_rows(
    client: CountingOpenAIClient,
    spec: FeatureSpec,
    posts: pd.DataFrame,
    *,
    run_dir: Path,
    run_id: str,
) -> ResumedJob:
    """Let a fresh engine reattach to the saved job and return its Q44 rows and per-request usage.

    Rows get ``run_id``, the provider ``batch_id``, the ``task-NNNNN``
    request id, and the attempt count from the state the engine saved.

    Raises
    ------
    RuntimeError
        When any post ends without a valid row, or the engine reports no
        completed batch.
    """
    tasks = _tasks(posts)
    engine = OpenAIBatchEngine(
        spec,
        FeatureRunConfig(batch_size=len(tasks)),
        client,
        DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
        time.sleep,
    )
    rows_by_id: dict[str, dict[str, Any]] = {}
    last_state: dict[str, Any] = {}

    def write_rows(rows: list[dict[str, Any]]) -> None:
        state = load_active_batch_state(run_dir, spec.name)
        if state is None:
            raise RuntimeError("engine delivered rows without an active batch state")
        last_state.clear()
        last_state.update(state)
        request_ids = {
            uri: f"{CUSTOM_ID_PREFIX}{index:0{CUSTOM_ID_INDEX_WIDTH}d}"
            for index, uri in enumerate(state["pending_source_record_ids"])
        }
        with_provenance = attach_provenance(
            rows,
            run_id=run_id,
            batch_id=state["batch_id"],
            request_ids=request_ids,
            attempt_count=int(state["attempt_count"]),
        )
        rows_by_id.update({row["source_record_id"]: row for row in with_provenance})

    resumed_at = get_current_timestamp()
    failures = engine.label_chunk(
        tasks,
        feature_name=spec.name,
        run_dir=run_dir,
        batch_index=SMOKE_BATCH_INDEX,
        write_rows=write_rows,
    )
    if failures:
        detail = "; ".join(f"{failure.source_record_id}: {failure.error}" for failure in failures)
        raise RuntimeError(f"smoke left {len(failures)} posts unlabeled: {detail}")
    missing = [task.uri for task in tasks if task.uri not in rows_by_id]
    if missing:
        raise RuntimeError(f"smoke produced no row for {missing}")
    last_batch = engine.last_batch
    if last_batch is None or last_batch.output_file_id is None:
        raise RuntimeError("resumed engine reported no completed batch with output")
    output_text = client.files.content(last_batch.output_file_id).text
    return ResumedJob(
        rows=[rows_by_id[task.uri] for task in tasks],
        request_usages=request_usages_from_output_text(
            output_text, list(last_state["pending_source_record_ids"])
        ),
        engine=engine,
        resume_calls=_submit_calls(client),
        resumed_at=resumed_at,
    )


def build_resume_evidence(
    *,
    feature: str,
    run_id: str,
    interrupted: InterruptedJob,
    resumed: ResumedJob,
) -> dict[str, Any]:
    """Return the interrupt-and-resume proof for ``resume_evidence.json``.

    ``resume_ok`` is true only when the resumed engine made no upload and no
    batch creation call, finished on the same provider batch id that was
    saved before the interruption, and wrote a row for every post.
    """
    last_batch = resumed.engine.last_batch
    resumed_batch_id = last_batch.id if last_batch is not None else None
    same_batch = resumed_batch_id == interrupted.state["batch_id"]
    no_new_jobs = all(count == 0 for count in resumed.resume_calls.values())
    return {
        "feature": feature,
        "run_id": run_id,
        "batch_id": interrupted.state["batch_id"],
        "input_file_id": interrupted.state["input_file_id"],
        "submitted_at": interrupted.state["submitted_at"],
        "interrupted_at": interrupted.interrupted_at,
        "state_at_interrupt": interrupted.state,
        "resumed_at": resumed.resumed_at,
        "submit_calls_before_interrupt": interrupted.submit_calls,
        "submit_calls_after_resume": resumed.resume_calls,
        "resumed_batch_id": resumed_batch_id,
        "reattached_same_batch_id": same_batch,
        "resumed_batch_status": last_batch.status if last_batch is not None else None,
        "rows_written": len(resumed.rows),
        "provider_batch_ids_in_output": sorted({str(row["batch_id"]) for row in resumed.rows}),
        "resume_ok": no_new_jobs and same_batch and len(resumed.rows) == SMOKE_POST_COUNT,
    }


def _json_bytes(document: dict[str, Any]) -> bytes:
    return f"{json.dumps(document, indent=JSON_INDENT)}\n".encode("utf-8")


def write_smoke_objects(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    posts: pd.DataFrame,
    rows: list[dict[str, Any]],
    spec: FeatureSpec,
    run_id: str,
    cost_report: dict[str, Any],
    resume_evidence: dict[str, Any],
) -> None:
    """Put the four untagged smoke objects under ``paths.smoke_prefix`` with ``If-None-Match: *``.

    Raises
    ------
    FileExistsError
        When any of the four objects already exists, because a feature's smoke
        runs once.
    ValueError
        When ``rows`` fail the Q44 validation.
    """
    validate_q44_rows(rows, spec, run_id=run_id)
    store.put_new(
        paths.smoke_input_key,
        rows_to_parquet_bytes(posts.to_dict(orient="records"), list(posts.columns)),
    )
    store.put_new(paths.smoke_output_key, rows_to_parquet_bytes(rows, q44_columns(spec)))
    store.put_new(paths.smoke_cost_report_key, _json_bytes(cost_report))
    store.put_new(paths.smoke_resume_evidence_key, _json_bytes(resume_evidence))


def _exists_untagged(store: CampaignObjectStore, key: str) -> tuple[bool, bool]:
    exists = store.get(key) is not None
    untagged = exists and store.get_tags(key) == {}
    return exists, untagged


def run_s3_checks(
    store: CampaignObjectStore,
    smoke_paths: SmokePaths,
    *,
    spec: FeatureSpec,
    canonical_smoke_keys_before: list[str],
) -> tuple[dict[str, bool], list[str]]:
    """Verify the smoke objects and return the named checks plus one text line per observation.

    Checks: the four smoke objects exist without tags, ``output.parquet`` holds
    exactly ten rows with the Q44 columns, ``resume_evidence.json`` records
    ``resume_ok``, no object exists under the smoke paths' ``batches/``, and
    whether the canonical ``smoke/`` prefix changed during this run.
    """
    paths = smoke_paths.paths
    lines: list[str] = []
    all_untagged = True
    for key in (
        paths.smoke_input_key,
        paths.smoke_output_key,
        paths.smoke_cost_report_key,
        paths.smoke_resume_evidence_key,
    ):
        exists, untagged = _exists_untagged(store, key)
        all_untagged = all_untagged and exists and untagged
        lines.append(f"exists {paths.uri(key)}={str(exists).lower()}")
        lines.append(f"untagged {paths.uri(key)}={str(untagged).lower()}")
    output = store.get(paths.smoke_output_key)
    output_ok = False
    if output is not None:
        frame = parquet_rows(output.body)
        output_ok = len(frame) == SMOKE_POST_COUNT and list(frame.columns) == q44_columns(spec)
        lines.append(f"output_rows={len(frame)}")
        lines.append(f"output_columns={list(frame.columns)}")
    evidence = store.get(paths.smoke_resume_evidence_key)
    resume_ok = False
    if evidence is not None:
        resume_ok = bool(json.loads(evidence.body.decode("utf-8")).get("resume_ok"))
    batch_keys = store.list_keys(paths.batches_prefix)
    lines.append(f"batches_prefix={paths.uri(paths.batches_prefix)} objects={len(batch_keys)}")
    canonical_after = store.list_keys(smoke_paths.canonical.smoke_prefix)
    lines.append(
        f"canonical_smoke_prefix={smoke_paths.canonical.uri(smoke_paths.canonical.smoke_prefix)} "
        f"objects_before={len(canonical_smoke_keys_before)} objects_after={len(canonical_after)}"
    )
    checks = {
        CHECK_SMOKE_OBJECTS_UNTAGGED: all_untagged,
        CHECK_SMOKE_OUTPUT_OK: output_ok and all_untagged,
        CHECK_RESUME_EVIDENCE_OK: resume_ok and all_untagged,
        CHECK_NO_BATCHES: not batch_keys,
        CHECK_CANONICAL_TOUCHED: canonical_after != canonical_smoke_keys_before,
    }
    lines.extend(f"{name}={str(value).lower()}" for name, value in checks.items())
    return checks, lines


def write_git_copies(
    output_dir: Path,
    feature: str,
    *,
    cost_report: dict[str, Any],
    resume_evidence: dict[str, Any],
    check_lines: list[str],
) -> Path:
    """Write the cost report, resume evidence, and S3 check lines under ``output_dir`` and return the cost report path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{feature}{COST_REPORT_SUFFIX}"
    report_path.write_bytes(_json_bytes(cost_report))
    (output_dir / f"{feature}{RESUME_EVIDENCE_SUFFIX}").write_bytes(_json_bytes(resume_evidence))
    (output_dir / f"{feature}{S3_CHECKS_SUFFIX}").write_text(
        "".join(f"{line}\n" for line in check_lines), encoding="utf-8"
    )
    return report_path


def run_campaign_smoke(
    *,
    campaign_id: str,
    dataset_id: str,
    preprocessed_run: str,
    feature: str,
    smoke_prefix: str | None,
    output_dir: Path,
    pricing: BatchPricing,
    client_factory: Callable[[], OpenAIBatchClient] | None = None,
) -> SmokeResult:
    """Label the ten smoke posts for ``feature`` with one deliberate interruption and resume.

    Order of work: build the smoke paths and refuse a smoke prefix that
    overlaps the canonical feature prefix, load the ten posts, submit one
    provider job and save its ``polling`` state, discard that engine, let a
    new engine reattach to the saved job and collect the rows, build the
    cost report and the resume evidence, write the four untagged smoke
    objects, run the S3 checks, and write the Git copies under ``output_dir``.

    Raises
    ------
    ValueError
        When ``feature`` is not an OpenAI feature or ``smoke_prefix`` overlaps
        the canonical feature prefix.
    RuntimeError
        When the resumed job leaves any of the ten posts without a valid row.
    """
    spec = FEATURE_REGISTRY[feature]
    if spec.engine_type != CAMPAIGN_ENGINE_TYPE:
        raise ValueError(f"smoke requires an OpenAI feature, got {feature!r}")
    smoke_paths = build_smoke_paths(campaign_id, dataset_id, feature, smoke_prefix)
    store = CampaignObjectStore(smoke_paths.paths.bucket)
    canonical_smoke_keys_before = store.list_keys(smoke_paths.canonical.smoke_prefix)
    posts = load_deterministic_ten_posts(dataset_id, preprocessed_run)
    run_id = run_id_for_feature(campaign_id, feature)
    make_client = client_factory or create_openai_client
    with tempfile.TemporaryDirectory(prefix="smoke_bluesky_campaign_") as run_dir_name:
        run_dir = Path(run_dir_name)
        interrupted = submit_and_interrupt(
            CountingOpenAIClient(make_client()), spec, posts, run_dir=run_dir
        )
        resumed = resume_and_collect_rows(
            CountingOpenAIClient(make_client()), spec, posts, run_dir=run_dir, run_id=run_id
        )
    last_batch = resumed.engine.last_batch
    cost_report = build_feature_cost_report(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        model=DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
        smoke_uri=smoke_paths.paths.uri(smoke_paths.paths.smoke_prefix),
        batch_id=interrupted.state["batch_id"],
        batch_usage=last_batch.usage if last_batch is not None else None,
        request_usages=resumed.request_usages,
        pricing=pricing,
    )
    resume_evidence = build_resume_evidence(
        feature=feature, run_id=run_id, interrupted=interrupted, resumed=resumed
    )
    write_smoke_objects(
        store,
        smoke_paths.paths,
        posts=posts,
        rows=resumed.rows,
        spec=spec,
        run_id=run_id,
        cost_report=cost_report,
        resume_evidence=resume_evidence,
    )
    checks, check_lines = run_s3_checks(
        store,
        smoke_paths,
        spec=spec,
        canonical_smoke_keys_before=canonical_smoke_keys_before,
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
    """Return the stdout lines of one smoke run, in the order the step spec fixes."""
    report = result.cost_report
    checks = result.checks
    return [
        f"smoke_prefix={result.smoke_prefix_uri}",
        f"smoke_rows={result.resume_evidence['rows_written']}",
        f"avg_input_tokens={report['avg_input_tokens_per_request']}",
        f"max_input_tokens={report['max_input_tokens_per_request']}",
        f"avg_output_tokens={report['avg_output_tokens_per_request']}",
        f"max_output_tokens={report['max_output_tokens_per_request']}",
        f"estimated_full_run_usd_avg={report['estimated_full_run_usd_avg']}",
        f"estimated_full_run_usd_max={report['estimated_full_run_usd_max']}",
        f"{CHECK_SMOKE_OUTPUT_OK}={str(checks[CHECK_SMOKE_OUTPUT_OK]).lower()}",
        f"{CHECK_RESUME_EVIDENCE_OK}={str(checks[CHECK_RESUME_EVIDENCE_OK]).lower()}",
        f"{CHECK_NO_BATCHES}={str(checks[CHECK_NO_BATCHES]).lower()}",
        f"{CHECK_CANONICAL_TOUCHED}={str(checks[CHECK_CANONICAL_TOUCHED]).lower()}",
        f"cost_report={_display_path(result.cost_report_path)}",
    ]


def checks_passed(checks: dict[str, bool]) -> bool:
    """True when every smoke object check holds and no ``batches/`` object exists.

    ``canonical_smoke_prefix_touched`` is reported but not judged here, because
    a canonical run touches that prefix by design.
    """
    return all(
        checks[name]
        for name in (
            CHECK_SMOKE_OBJECTS_UNTAGGED,
            CHECK_SMOKE_OUTPUT_OK,
            CHECK_RESUME_EVIDENCE_OK,
            CHECK_NO_BATCHES,
        )
    )


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    dataset_id: str = typer.Option(..., "--dataset-id"),
    preprocessed_run: str = typer.Option(..., "--preprocessed-run"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str | None = typer.Option(None, "--smoke-prefix"),
    output_dir: Path | None = typer.Option(None, "--output-dir"),
    input_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS, "--input-usd-per-million-tokens"
    ),
    output_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS, "--output-usd-per-million-tokens"
    ),
) -> None:
    result = run_campaign_smoke(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        smoke_prefix=smoke_prefix,
        output_dir=output_dir or DEFAULT_SMOKE_REPORTS_DIR / feature,
        pricing=BatchPricing(
            source_url=PRICING_SOURCE_URL,
            input_usd_per_million_tokens=input_usd_per_million_tokens,
            output_usd_per_million_tokens=output_usd_per_million_tokens,
        ),
    )
    """Run the ten-post smoke for one feature, print the summary lines, and exit 1 when an S3 check fails."""
    for line in summary_lines(result):
        print(line)
    if not checks_passed(result.checks):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
