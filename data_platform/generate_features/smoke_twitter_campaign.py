"""Ten-post smoke for one feature of the Twitter LLM campaign, with interrupt-and-resume.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \\
        --campaign-id twitter_2026_09_06_192847_llm_features_v1 \\
        --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \\
        --preprocessed-run 2026_09_06-19:28:47 \\
        --feature is_news_or_opinion \\
        --smoke-prefix s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/twitter_step1_campaign_smoke/ \\
        --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/_step1_disposable

Pass ``--smoke-prefix s3://bucket/root/`` to write under ``root/{feature}/smoke/``
instead of the primary campaign feature prefix.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

import typer

from data_platform.generate_features.campaign_cost_report import (
    CAMPAIGN_LLM_FEATURES,
    DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS,
    DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_SOURCE_URL,
    BatchPricing,
    build_feature_cost_report,
)
from data_platform.generate_features.deterministic_smoke_sample import (
    load_deterministic_ten_posts,
)
from data_platform.generate_features.engines.openai_engine import (
    DEFAULT_OPENAI_BATCH_ENGINE_CONFIG,
    OpenAIBatchClient,
    create_openai_client,
)
from data_platform.generate_features.generate_features import CAMPAIGN_ENGINE_TYPE
from data_platform.generate_features.generate_twitter_features import TWITTER_SPEC
from data_platform.generate_features.registry import FEATURE_REGISTRY
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
    SmokePaths,
    SmokeResult,
    build_resume_evidence,
    checks_passed,
    resume_and_collect_rows,
    run_s3_checks,
    submit_and_interrupt,
    write_git_copies,
    write_smoke_objects,
)
from data_platform.generate_features.twitter_campaign_config import (
    load_twitter_campaign_config,
)
from lib.constants import REPO_ROOT

DEFAULT_SMOKE_REPORTS_DIR = (
    REPO_ROOT / "docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke"
)
CHECK_PRIMARY_TOUCHED = "primary_smoke_prefix_touched"
SMOKE_RUN_DIR_PREFIX = "smoke_twitter_campaign_"


def build_twitter_smoke_paths(
    campaign_id: str, dataset_id: str, feature: str, smoke_prefix: str | None
) -> SmokePaths:
    """Return the primary Twitter feature paths, or paths under ``smoke_prefix`` when given.

    Raises
    ------
    ValueError
        When ``smoke_prefix`` is not an ``s3://`` URI, or when it lands on or
        inside the primary feature prefix, or contains it.
    """
    primary = FeaturePaths.for_campaign(
        campaign_id,
        feature,
        platform=TWITTER_SPEC.platform,
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


def run_twitter_campaign_smoke(
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
    overlaps the primary feature prefix, load the ten posts, submit one
    provider job and save its polling state, discard that engine, let a
    new engine reattach to the saved job and collect the rows, build the
    cost report and the resume evidence, write the four untagged smoke
    objects, run the S3 checks, and write the Git copies under ``output_dir``.

    Raises
    ------
    ValueError
        When ``feature`` is not an OpenAI feature, ``campaign_id`` is not the
        locked Twitter campaign id, or ``smoke_prefix`` overlaps the primary
        feature prefix.
    RuntimeError
        When the resumed job leaves any of the ten posts without a valid row.
    """
    spec = FEATURE_REGISTRY.get(feature)
    if spec is None or spec.engine_type != CAMPAIGN_ENGINE_TYPE:
        raise ValueError(
            f"smoke requires one of the OpenAI features {list(CAMPAIGN_LLM_FEATURES)}, "
            f"got {feature!r}"
        )
    campaign = load_twitter_campaign_config(campaign_id)
    smoke_paths = build_twitter_smoke_paths(campaign_id, dataset_id, feature, smoke_prefix)
    store = CampaignObjectStore(smoke_paths.paths.bucket)
    canonical_smoke_keys_before = store.list_keys(smoke_paths.canonical.smoke_prefix)
    posts = load_deterministic_ten_posts(dataset_id, preprocessed_run, spec=TWITTER_SPEC)
    run_id = run_id_for_feature(campaign_id, feature)
    make_client = client_factory or create_openai_client
    with tempfile.TemporaryDirectory(prefix=SMOKE_RUN_DIR_PREFIX) as run_dir_name:
        run_dir = Path(run_dir_name)
        interrupted = submit_and_interrupt(
            CountingOpenAIClient(make_client()), spec, posts, run_dir=run_dir
        )
        resumed = resume_and_collect_rows(
            CountingOpenAIClient(make_client()), spec, posts, run_dir=run_dir, run_id=run_id
        )
    cost_report = build_feature_cost_report(
        campaign_id=campaign_id,
        dataset_id=dataset_id,
        preprocessed_run=preprocessed_run,
        feature=feature,
        model=DEFAULT_OPENAI_BATCH_ENGINE_CONFIG.model,
        smoke_uri=smoke_paths.paths.uri(smoke_paths.paths.smoke_prefix),
        batch_id=interrupted.state["batch_id"],
        batch_usage=resumed.last_batch.usage,
        request_usages=resumed.request_usages,
        pricing=pricing,
        full_run_post_count=int(campaign["row_count"]),
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
    """Return the stdout lines of one Twitter smoke run."""
    report = result.cost_report
    checks = result.checks
    return [
        f"smoke_prefix={result.smoke_prefix_uri}",
        f"smoke_rows={result.resume_evidence['rows_written']}",
        f"full_run_row_count={report['full_run_post_count']}",
        f"avg_input_tokens={report['avg_input_tokens_per_request']}",
        f"max_input_tokens={report['max_input_tokens_per_request']}",
        f"avg_output_tokens={report['avg_output_tokens_per_request']}",
        f"max_output_tokens={report['max_output_tokens_per_request']}",
        f"estimated_full_run_usd_avg={report['estimated_full_run_usd_avg']}",
        f"estimated_full_run_usd_max={report['estimated_full_run_usd_max']}",
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
    input_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_INPUT_USD_PER_MILLION_TOKENS, "--input-usd-per-million-tokens"
    ),
    output_usd_per_million_tokens: float = typer.Option(
        DEFAULT_BATCH_OUTPUT_USD_PER_MILLION_TOKENS, "--output-usd-per-million-tokens"
    ),
) -> None:
    """Run the ten-post smoke for one feature, print the summary lines, and exit 1 when an S3 check fails."""
    result = run_twitter_campaign_smoke(
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
    for line in summary_lines(result):
        print(line)
    if not checks_passed(result.checks):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
