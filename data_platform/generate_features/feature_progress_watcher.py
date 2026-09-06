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
IDLE = "idle"


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
    """Return the markdown block of the rolling feature-issue comment, without a trailing newline."""
    cost = "unavailable" if cost_to_date_usd is None else f"${cost_to_date_usd:.2f}"
    return "\n".join(
        [
            f"## Feature progress: {record.feature}",
            f"Campaign: {record.campaign_id}",
            f"Durable rows: {record.durable_row_total} / {record.expected_row_total} "
            f"({record.percent_complete * 100:.1f}%)",
            f"Latest part: {record.part_index} (manifest sha256: {record.manifest_sha256})",
            f"Estimated cost to date: {cost}",
            f"Active OpenAI batch: {active_openai_batch_id or IDLE}",
            f"Updated: {updated_at}",
        ]
    )


def run_watcher_once(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    github_comment_id: int | None,
) -> WatcherOutcome:
    raise NotImplementedError


def output_lines(outcome: WatcherOutcome) -> list[str]:
    """Return the stdout lines of one run, in the order the step spec fixes."""
    lines = [f"boundary_crossed={str(outcome.boundary is not None).lower()}"]
    if outcome.boundary is not None:
        lines.append(f"boundary={outcome.boundary}")
    else:
        lines.append(f"duplicate_boundary_suppressed={str(outcome.duplicate_suppressed).lower()}")
    if outcome.watcher_updated:
        lines.append("watcher_json_updated=true")
    lines.append("github_write_skipped=true")
    if outcome.github_comment_id_recorded is not None:
        lines.append(f"github_comment_id_recorded={outcome.github_comment_id_recorded}")
    if outcome.comment is not None:
        lines.extend([COMMENT_OPEN, outcome.comment, COMMENT_CLOSE])
    return lines


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
