# Step 7: Add durable progress reports for feature run watchers

## Goal

Write structured progress records to durable S3 state after each immutable shard lands. Give operators enough information to run short, restartable watcher processes that update one rolling GitHub issue comment at every 10,000 completed durable rows per feature. Watchers read S3 only; they do not mutate shards, manifests, or labels.

## Real dependencies

- Step 4 merged: OpenAI Batch resume behavior.
- Step 5 merged: immutable shards, `manifest.json`, `progress.jsonl`, Q44 provenance, S3 layout.
- Step 6 merged: deterministic smoke artifacts, approval gate, and first production shard combiner.
- Steps 1 through 3 merged: S3 production backend.

## Main caller and one implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --github-issue 999 \
  --once
```

The watcher is a short-lived CLI meant to be restarted by a human operator or external scheduler. It is not a long-running daemon inside the feature generator.

**One implementation slice for this PR:** extend durable `progress.jsonl` entries with watcher-ready counters and add a standalone watcher CLI that reads S3 progress state, computes whether a 10,000-row boundary was crossed, and prints the exact rolling comment body for manual paste or for a separate non-repo automation.

**Out of scope for this PR:** generating remaining feature rows beyond progress reporting, changing OpenAI Batch behavior, modifying smoke cost gate logic, lifecycle expiration rules, and any repository code that launches Cursor agents or calls the GitHub API directly.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Parent plan Step 7 scope |
| `/workspace/data_platform/generate_features/s3_feature_shards.py` | Current progress append path |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | Campaign prefix helpers |
| `/workspace/data_platform/generate_features/campaign_cost_report.py` | Cost fields to echo in progress |
| `/workspace/data_platform/generate_features/bluesky_llm_campaign_smoke.py` | Smoke artifact locations |
| `/workspace/data_platform/generate_features/generate_features.py` | Batch completion hook |
| `/workspace/lib/aws/s3.py` | S3 read helpers |
| `/workspace/lib/timestamp_utils.py` | UTC timestamps |

## Files allowed to change

- `/workspace/data_platform/generate_features/progress_record.py` (new; structured progress schema)
- `/workspace/data_platform/generate_features/feature_progress_watcher.py` (new; short restartable watcher CLI)
- `/workspace/data_platform/generate_features/s3_feature_shards.py` (append enriched progress lines after each durable shard)
- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (helper to read progress tail if needed)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/runbooks/feature_progress_watcher.md` (new operator runbook for manual subagents)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step5.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step6.md`
- `/workspace/tests/**`
- `/workspace/data_platform/generate_features/engines/openai_engine.py` except if a one-line hook is absolutely required; prefer editing shard writer only
- Feature prompt modules
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents, GitHub Actions that auto-comment, or direct GitHub API clients inside the generator path

## Locked contracts

### Durable S3 progress state

Append one JSON object per line to:

```text
s3://mirrorview-experimental-artifacts/data_platform/data/features/bluesky_2026_09_03_235130_llm_features_v1/{feature}/progress.jsonl
```

Each line after a durable shard lands must include at minimum:

| Field | Meaning |
|-------|---------|
| `campaign_id` | `bluesky_2026_09_03_235130_llm_features_v1` |
| `feature` | feature name |
| `recorded_at` | UTC timestamp |
| `batch_shard_index` | shard just written |
| `shard_row_count` | rows in that shard |
| `durable_row_total` | cumulative labeled rows across all shards |
| `expected_row_total` | `200000` |
| `percent_complete` | `durable_row_total / 200000` |
| `last_source_record_id` | last id in shard order |
| `manifest_sha256` | SHA-256 of `manifest.json` after update |
| `estimated_cost_usd_to_date` | optional running estimate from token usage |
| `active_openai_batch_id` | null when idle; set while polling |

Progress lines are append-only. Watchers treat the file as authoritative durable state.

### Watcher cadence: one rolling comment every 10,000 durable rows

For each feature issue, emit an updated rolling comment body when `durable_row_total` crosses a new multiple of 10,000:

`10000, 20000, 30000, ... 200000`

Watchers must not emit duplicate updates for the same boundary. Persist last emitted boundary in a small S3 sidecar:

```text
.../{feature}/watcher_state.json
```

### Short restartable watcher subagents

Watchers must be safe to kill and restart. On restart, reload `progress.jsonl` and `watcher_state.json` from S3, recompute the highest durable total, and continue from the next unseen 10,000 boundary.

The operator runbook describes manual subagent restarts. Repository code must not spawn subagents, Cursor agents, background threads that loop forever, or GitHub API calls.

### Rolling comment body format

The watcher CLI prints a single markdown block to stdout for manual paste into the feature issue. Required sections:

1. Campaign id, feature name, durable rows, expected rows, percent complete
2. Latest shard index and manifest SHA-256
3. Estimated cost to date and projected final cost if available from Step 6 reports
4. Active OpenAI batch id or `idle`
5. Last updated UTC timestamp

Example shape:

```markdown
## Feature progress: is_news_or_opinion
Campaign: bluesky_2026_09_03_235130_llm_features_v1
Durable rows: 10000 / 200000 (5.0%)
Latest shard: 4 (manifest sha256: abcd...)
Estimated cost to date: $0.42
Active OpenAI batch: idle
Updated: 2026-09-05T20:15:00Z
```

### No repository agent launching

Hard rule: no Python module in this repository may invoke Cursor Cloud agents, GitHub Copilot agents, or other autonomous coding agents. Watchers report state only.

## Ordered implementation work

1. Define `progress_record.py` schema and validation for append-only lines.
2. Extend shard completion path to append enriched progress records with cumulative durable totals.
3. Implement `feature_progress_watcher.py` with `--once` mode that reads S3, detects crossed 10,000 boundaries, updates `watcher_state.json`, and prints the rolling comment body.
4. Write operator runbook `runbooks/feature_progress_watcher.md` describing manual restart steps for short watcher subagents outside the repo.
5. Add temporary smoke helper or reuse Step 6 first production shard output to simulate at least 10,000 durable rows, or document a reduced-boundary dev flag limited to smoke evidence only.
6. Run live smoke commands below. Commit watcher runbook and sample printed comment during review. Remove temporary dev-only boundary override before merge.

## Exact live smoke/basic check commands with expected output

### Offline schema check

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.progress_record import ProgressRecord
r = ProgressRecord(
    campaign_id='bluesky_2026_09_03_235130_llm_features_v1',
    feature='is_news_or_opinion',
    recorded_at='2026-09-05T20:00:00Z',
    batch_shard_index=0,
    shard_row_count=2000,
    durable_row_total=2000,
    expected_row_total=200000,
    percent_complete=0.01,
    last_source_record_id='at://example/1',
    manifest_sha256='abc',
    estimated_cost_usd_to_date=0.01,
    active_openai_batch_id=None,
)
assert r.expected_row_total == 200000
print('ProgressRecord schema OK')
"
```

Expected stdout:

```text
ProgressRecord schema OK
```

### Live watcher read against existing S3 progress

After Step 5 or Step 6 smoke has written at least one shard:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --github-issue 999 \
  --once
```

Expected stdout when durable total is below 10,000:

```text
boundary_crossed=false
durable_row_total=<number less than 10000>
no_comment_update_needed=true
```

Expected stdout when durable total reaches at least 10,000:

```text
boundary_crossed=true
boundary=10000
watcher_state_updated=true
rolling_comment<<<
## Feature progress: is_news_or_opinion
...
>>>rolling_comment
```

### Restart idempotency check

Run the same watcher command twice without new shards landing.

Expected second stdout:

```text
boundary_crossed=false
duplicate_boundary_suppressed=true
```

Expected S3 effect: `watcher_state.json` unchanged after the second run.

### Manual subagent restart proof documented in runbook

The operator runbook must include these exact steps:

1. Stop the watcher process.
2. Confirm the feature generator or batch job is still running or safely idle.
3. Re-run the watcher command with the same `--campaign-id` and `--feature`.
4. Verify `duplicate_boundary_suppressed=true` when no new durable rows arrived.

No repository command may start a Cursor agent.

## Acceptance criteria

- Every durable shard append adds one validated `progress.jsonl` line with cumulative totals.
- Watcher CLI reads S3 state only and prints a rolling comment at each new 10,000-row boundary.
- Restarting the watcher does not duplicate boundary notifications.
- `watcher_state.json` persists the last emitted boundary in S3.
- Operator runbook documents short restartable manual watcher subagents outside the repo.
- No repository code launches Cursor agents or posts to GitHub automatically.
- No automated tests were added or run.

## Failure conditions

- Progress totals derived only from memory, not from durable S3 shard state.
- Missing cumulative `durable_row_total` on any progress line.
- Duplicate rolling comment emission for the same 10,000 boundary after restart.
- Watcher mutates shard objects or manifest content.
- Any GitHub API client added to the generator or watcher path.
- Any code path that launches Cursor agents or other autonomous agent runners.
- Any edit under `/workspace/tests/**`.

## PR artifact/commit rules

- Branch name: `cursor/feature-progress-watcher-86b0`
- Commit `feature_progress_watcher.py`, `progress_record.py`, runbook, and one sample printed rolling comment captured in `WATCHER_SMOKE_EVIDENCE.md` during review.
- Delete dev-only boundary override helpers before merge; keep production 10,000-row cadence.
- PR title: `Add durable progress reports for feature run watchers`
- PR body must include a pasted sample rolling comment and the S3 keys for `progress.jsonl` and `watcher_state.json`.
