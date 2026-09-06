"""Short restartable watcher that prints a rolling progress comment for one campaign feature.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --feature is_news_or_opinion \\
        --once

The watcher reads S3 only and its one write is the conditional replace of
``watcher.json``. It never posts to GitHub; an operator agent outside the
repository posts the printed body.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import typer

from data_platform.generate_features.progress_record import ProgressRecord
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
)

MILESTONE_ROWS = 10_000
COMMENT_OPEN = "rolling_comment<<<"
COMMENT_CLOSE = ">>>rolling_comment"


@dataclass(frozen=True)
class WatcherOutcome:
    """What one watcher run decided, saved, and rendered."""

    boundary: int | None
    duplicate_suppressed: bool
    watcher_state: dict[str, Any]
    watcher_updated: bool
    comment: str | None
    github_comment_id_recorded: int | None


def resolve_feature_paths(
    campaign_id: str, feature: str, smoke_prefix: str | None
) -> FeaturePaths:
    raise NotImplementedError


def crossed_boundary(durable_row_total: int, last_posted_milestone: int) -> int | None:
    raise NotImplementedError


def estimated_cost_to_date(
    cost_report: dict[str, Any] | None, durable_row_total: int
) -> float | None:
    raise NotImplementedError


def render_rolling_comment(
    record: ProgressRecord,
    *,
    active_openai_batch_id: str | None,
    cost_to_date_usd: float | None,
    updated_at: str,
) -> str:
    raise NotImplementedError


def run_watcher_once(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    github_comment_id: int | None,
) -> WatcherOutcome:
    raise NotImplementedError


def output_lines(outcome: WatcherOutcome) -> list[str]:
    raise NotImplementedError


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str | None = typer.Option(None, "--smoke-prefix"),
    dry_render: bool = typer.Option(False, "--dry-render"),
    once: bool = typer.Option(False, "--once"),
    github_comment_id: int | None = typer.Option(None, "--github-comment-id"),
) -> None:
    if not once:
        raise typer.BadParameter("pass --once; it is the only mode of this command")
    paths = resolve_feature_paths(campaign_id, feature, smoke_prefix)
    store = CampaignObjectStore(paths.bucket)
    outcome = run_watcher_once(store, paths, github_comment_id=github_comment_id)
    for line in output_lines(outcome):
        print(line)


if __name__ == "__main__":
    typer.run(main)
