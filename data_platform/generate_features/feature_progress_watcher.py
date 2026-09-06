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

import json
from dataclasses import dataclass
from typing import Any

import typer

from data_platform.generate_features.progress_record import (
    ProgressRecord,
    latest_batch_record,
    parse_batch_records,
)
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
    load_active_state,
    load_watcher_state,
    read_progress_lines,
    save_watcher_state,
)
from lib.timestamp_utils import get_current_timestamp

MILESTONE_ROWS = 10_000
COMMENT_OPEN = "rolling_comment<<<"
COMMENT_CLOSE = ">>>rolling_comment"
IDLE = "idle"
GITHUB_COMMENT_ID_FIELD = "github_comment_id"
LAST_POSTED_MILESTONE_FIELD = "last_posted_milestone"


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
    """Return the canonical feature paths, or the paths under ``smoke_prefix/{feature}/`` when given."""
    if smoke_prefix is None:
        return FeaturePaths.canonical(campaign_id, feature)
    return FeaturePaths.from_root_uri(smoke_prefix, feature)


def crossed_boundary(durable_row_total: int, last_posted_milestone: int) -> int | None:
    """Return the highest 10,000-row multiple reached that is above the last posted one, or None."""
    boundary = durable_row_total // MILESTONE_ROWS * MILESTONE_ROWS
    if boundary > last_posted_milestone:
        return boundary
    return None


def estimated_cost_to_date(
    cost_report: dict[str, Any] | None, durable_row_total: int
) -> float | None:
    """Scale the smoke report's average full-run estimate to the rows labeled so far, or None without a report."""
    if cost_report is None:
        return None
    per_row = float(cost_report["estimated_full_run_usd_avg"]) / int(
        cost_report["full_run_post_count"]
    )
    return durable_row_total * per_row


def _load_json_or_none(store: CampaignObjectStore, key: str) -> dict[str, Any] | None:
    stored = store.get(key)
    if stored is None:
        return None
    return json.loads(stored.body.decode("utf-8"))


def render_rolling_comment(
    record: ProgressRecord,
    *,
    active_openai_batch_id: str | None,
    cost_to_date_usd: float | None,
    updated_at: str,
) -> str:
    """Return the markdown block of the rolling feature-issue comment, without a trailing newline."""
    cost = "unavailable" if cost_to_date_usd is None else f"${cost_to_date_usd:.2f}"
    rows = f"{record.durable_row_total} / {record.expected_row_total}"
    return "\n".join(
        [
            f"## Feature progress: {record.feature}",
            f"Campaign: {record.campaign_id}",
            f"Durable rows: {rows} ({record.percent_complete * 100:.1f}%)",
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
    """Read the feature's S3 progress state once and report whether a new 10,000-row boundary was reached.

    ``watcher.json`` is replaced only when a new boundary is reached or when
    ``github_comment_id`` differs from the stored one, so a rerun with no
    change leaves the object untouched. The comment is rendered only for a new
    boundary.

    Raises
    ------
    ValueError
        When a batch line of ``progress.jsonl`` fails validation.
    ConditionalWriteConflict
        When another watcher replaced ``watcher.json`` first.
    """
    latest = latest_batch_record(parse_batch_records(read_progress_lines(store, paths)))
    stored_state, etag = load_watcher_state(store, paths)
    state = {
        GITHUB_COMMENT_ID_FIELD: None,
        LAST_POSTED_MILESTONE_FIELD: 0,
        **(stored_state or {}),
    }
    last_posted = int(state[LAST_POSTED_MILESTONE_FIELD])
    durable_row_total = 0 if latest is None else latest.durable_row_total
    boundary = crossed_boundary(durable_row_total, last_posted)
    duplicate_suppressed = boundary is None and last_posted >= MILESTONE_ROWS
    comment = None
    if boundary is not None and latest is not None:
        active_state, _ = load_active_state(store, paths)
        comment = render_rolling_comment(
            latest,
            active_openai_batch_id=None if active_state is None else str(active_state["batch_id"]),
            cost_to_date_usd=estimated_cost_to_date(
                _load_json_or_none(store, paths.smoke_cost_report_key), latest.durable_row_total
            ),
            updated_at=get_current_timestamp(),
        )
        state[LAST_POSTED_MILESTONE_FIELD] = boundary
    recorded_id = None
    if github_comment_id is not None and state[GITHUB_COMMENT_ID_FIELD] != github_comment_id:
        state[GITHUB_COMMENT_ID_FIELD] = github_comment_id
        recorded_id = github_comment_id
    watcher_updated = state != stored_state and (boundary is not None or recorded_id is not None)
    if watcher_updated:
        save_watcher_state(store, paths, state, etag)
    return WatcherOutcome(
        boundary=boundary,
        duplicate_suppressed=duplicate_suppressed,
        watcher_state=state,
        watcher_updated=watcher_updated,
        comment=comment,
        github_comment_id_recorded=recorded_id,
    )


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
    """Run the watcher once and print its outcome lines.

    ``--dry-render`` is accepted so the step spec's command lines run as
    written. The command never writes to GitHub in any mode.
    """
    if not once:
        raise typer.BadParameter("pass --once; it is the only mode of this command")
    paths = resolve_feature_paths(campaign_id, feature, smoke_prefix)
    store = CampaignObjectStore(paths.bucket)
    outcome = run_watcher_once(store, paths, github_comment_id=github_comment_id)
    for line in output_lines(outcome):
        print(line)


if __name__ == "__main__":
    typer.run(main)
