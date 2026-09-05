# Step 7: Add durable progress reports for feature run watchers

## Goal

Enrich `progress.jsonl` entries after each immutable batch lands. Add `watcher.json` for rolling GitHub comment state. Provide a short, restartable watcher CLI that reads S3 progress state, detects 10,000-row boundaries, prints a prepared markdown report, and updates `watcher.json`. Watchers read S3 only for feature artifacts; they do not mutate batches, manifests, or labels.

## Dependencies

- **Step 5 merged:** immutable batches, `manifest.json`, logical-append `progress.jsonl`, Q44 provenance, canonical S3 layout.
- See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for `watcher.json` schema, milestone cadence, and append semantics.

Step 7 may proceed in parallel with Step 6 after Step 5 merges. Both Step 6 and Step 7 must complete before Steps 8 through 14. Step 7 does not depend on Step 6 smoke outputs.

## Main caller and implementation slice

**Main caller after this PR merges:**

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --once
```

The watcher is a short-lived CLI meant to be restarted by a human operator or external scheduler. It is not a long-running daemon inside the feature generator.

**One implementation slice for this PR:** extend durable `progress.jsonl` entries with watcher-ready counters, add `watcher.json` read/write helpers, and add a standalone watcher CLI that reads S3 progress state, computes whether a 10,000-row boundary was crossed, prints the exact rolling comment body, and atomically updates `watcher.json`.

**Out of scope for this PR:** generating remaining feature rows, changing OpenAI Batch behavior, smoke cost tooling (Step 6), lifecycle expiration rules (Step 16), and any repository code that launches Cursor agents or calls the GitHub API directly.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | `watcher.json` schema and milestone cadence |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | Current progress append path |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | Campaign prefix helpers |
| `/workspace/data_platform/generate_features/generate_features.py` | Batch completion hook |
| `/workspace/lib/aws/s3.py` | S3 read helpers |
| `/workspace/lib/timestamp_utils.py` | UTC timestamps |

## Files allowed to change

- `/workspace/data_platform/generate_features/progress_record.py` (new; structured progress schema)
- `/workspace/data_platform/generate_features/feature_progress_watcher.py` (new; short restartable watcher CLI)
- `/workspace/data_platform/generate_features/seed_progress_watcher_smoke.py` (new temporary smoke helper; delete before merge)
- `/workspace/data_platform/generate_features/s3_feature_batches.py` (append enriched progress lines after each durable batch)
- `/workspace/data_platform/generate_features/s3_feature_campaign.py` (helper to read progress tail and `watcher.json` if needed)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/runbooks/feature_progress_watcher.md` (new operator runbook)
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md` (this file only if correcting the spec during implementation)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step4.md`, `step5.md`, `step6.md`
- `/workspace/tests/**`
- `/workspace/data_platform/generate_features/engines/openai_engine.py` except if a one-line hook is absolutely required
- Feature prompt modules
- `/workspace/webapp/**`
- `/workspace/experiments/**`
- Any repository code that launches Cursor agents, GitHub Actions that auto-comment, or direct GitHub API write clients inside the generator path

## Locked contracts

See `campaign_contract.md`. Exact values for this step:

### progress.jsonl (append-only)

Path per feature:

`s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/{feature}/progress.jsonl`

Each line after a durable batch lands must include at minimum:

| Field | Meaning |
|-------|---------|
| `campaign_id` | `bluesky_2026_09_03_235130_llm_features_v1` |
| `feature` | feature name |
| `run_id` | `bluesky_2026_09_03_235130_llm_features_v1:{feature}` |
| `recorded_at` | UTC timestamp |
| `part_index` | batch part just written |
| `batch_row_count` | rows in that batch |
| `durable_row_total` | cumulative labeled rows across all batches |
| `expected_row_total` | `200000` |
| `percent_complete` | `durable_row_total / 200000` |
| `last_source_record_id` | last id in batch order |
| `manifest_sha256` | SHA-256 of `manifest.json` after update |
| `active_openai_batch_id` | null when idle; set while polling |

`progress.jsonl` is the only progress event file. Each append uses logical read-append-conditional-replace with S3 `If-Match` ETag for concurrency control only. SHA-256 remains the content integrity check for parquet and manifest bytes.

### watcher.json

Path per feature:

`.../features/bluesky_2026_09_03_235130_llm_features_v1/{feature}/watcher.json`

Stores:

| Field | Meaning |
|-------|---------|
| `github_comment_id` | id of the rolling feature-issue comment, or null before first post |
| `last_posted_milestone` | last 10k boundary posted (10000, 20000, …, 200000) |

Atomic replace is permitted using conditional `If-Match` ETag. The watcher CLI updates this file after preparing a new comment.

### Watcher cadence

Emit an updated rolling comment body when `durable_row_total` crosses a new multiple of 10,000. Do not emit duplicate updates for the same boundary.

### Rolling comment body format

The watcher CLI prints a single markdown block to stdout. An agent with authenticated GitHub integration posts or updates the feature-issue comment. Required sections:

1. Campaign id, feature name, durable rows, expected rows, percent complete
2. Latest part index and manifest SHA-256
3. Estimated cost to date if available from smoke reports
4. Active OpenAI batch id or `idle`
5. Last updated UTC timestamp

Example shape:

```markdown
## Feature progress: is_news_or_opinion
Campaign: bluesky_2026_09_03_235130_llm_features_v1
Durable rows: 10000 / 200000 (5.0%)
Latest part: 4 (manifest sha256: abcd...)
Estimated cost to date: $0.42
Active OpenAI batch: idle
Updated: 2026-09-05T20:15:00Z
```

### No repository agent launching or GitHub writes

Hard rule: no Python module in this repository may invoke Cursor Cloud agents or call GitHub write APIs. Describe GitHub posting as an agent responsibility in the runbook. Do not prescribe `gh` write commands from the read-only cloud CLI.

## Ordered implementation work

1. Define `progress_record.py` schema and validation for append-only lines.
2. Extend batch completion path to append enriched progress records with cumulative durable totals.
3. Implement `feature_progress_watcher.py` with `--once` mode that reads S3, detects crossed 10,000 boundaries, updates `watcher.json`, and prints the rolling comment body.
4. Write operator runbook `runbooks/feature_progress_watcher.md` describing manual restart steps for short watcher subagents outside the repo.
5. Seed disposable `progress.jsonl` and `watcher.json` under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/`, run the watcher proof against that prefix in `--dry-render` mode, then recursively clean the disposable prefix before merge.

## Exact live smoke and basic check commands with expected output

### Offline schema check

```bash
cd /workspace

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.progress_record import ProgressRecord
r = ProgressRecord(
    campaign_id='bluesky_2026_09_03_235130_llm_features_v1',
    feature='is_news_or_opinion',
    run_id='bluesky_2026_09_03_235130_llm_features_v1:is_news_or_opinion',
    recorded_at='2026-09-05T20:00:00Z',
    part_index=0,
    batch_row_count=2000,
    durable_row_total=2000,
    expected_row_total=200000,
    percent_complete=0.01,
    last_source_record_id='at://example/1',
    manifest_sha256='abc',
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

### Live watcher proof against disposable prefix (available after this step's implementation)

Step 5 and Step 6 do not write canonical campaign `batches/` or canonical `{feature}/smoke/`. Seed watcher inputs under a disposable prefix only.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/

PYTHONPATH=. uv run python data_platform/generate_features/seed_progress_watcher_smoke.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --durable-row-total 10000
```

Expected stdout:

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/
progress_seeded=true
watcher_seeded=true
durable_row_total=10000
```

Run the watcher against the disposable prefix in dry-render mode (prints the rolling comment body without GitHub writes):

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --dry-render \
  --once
```

Expected stdout when durable total is at least 10,000:

```text
boundary_crossed=true
boundary=10000
watcher_json_updated=true
github_write_skipped=true
rolling_comment<<<
(same heading and body shape as Rolling comment body format example above)
...
>>>rolling_comment
```

### Restart idempotency check

Run the same watcher command twice without changing seeded progress.

Expected second stdout:

```text
boundary_crossed=false
duplicate_boundary_suppressed=true
github_write_skipped=true
```

Expected S3 effect under the disposable prefix: `watcher.json` unchanged after the second run.

### Disposable prefix cleanup (required before merge)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/ --recursive
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/ --recursive
```

Expected: `aws s3 rm` reports deleted objects (or no objects found). `aws s3 ls` prints no lines, confirming the disposable prefix is empty.

## Acceptance criteria

- Every durable batch append adds one validated `progress.jsonl` line with cumulative totals.
- `watcher.json` persists `github_comment_id` and `last_posted_milestone`.
- Watcher CLI reads S3 state only and prints a rolling comment at each new 10,000-row boundary.
- Step 7 watcher proof seeds and reads only under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/`; it does not depend on Step 5 or Step 6 writing canonical batches or canonical smoke.
- Disposable S3 prefix is empty after `aws s3 rm ... --recursive` before merge.
- Restarting the watcher does not duplicate boundary notifications.
- Operator runbook documents short restartable manual watcher subagents outside the repo.
- No repository code launches Cursor agents or posts to GitHub automatically.
- No automated tests were added or run.

## Failure conditions

- Progress totals derived only from memory, not from durable S3 batch state.
- Missing cumulative `durable_row_total` on any progress line.
- Duplicate rolling comment emission for the same 10,000 boundary after restart.
- Watcher proof writes under the canonical campaign feature prefix instead of the disposable prefix.
- Disposable prefix `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/` is not empty before merge.
- Claiming Step 5 or Step 6 wrote canonical campaign batches as a prerequisite for watcher proof.
- Watcher mutates batch objects or manifest content.
- Any GitHub API write client added to the generator or watcher path.
- Any code path that launches Cursor agents or other autonomous agent runners.
- Using `watcher_state.json` or a `progress/` directory instead of the canonical paths.
- Any edit under `/workspace/tests/**`.

## PR artifact and commit rules

- Commit `feature_progress_watcher.py`, `progress_record.py`, and runbook.
- Capture one sample printed rolling comment in `WATCHER_SMOKE_EVIDENCE.md` during review; delete before merge.
- Before merge: delete `seed_progress_watcher_smoke.py`, run `aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/ --recursive`, and verify the disposable prefix is empty.
- PR title: `Add durable progress reports and watcher CLI for feature runs`
- PR body must include a pasted sample rolling comment from `--dry-render` mode and the disposable smoke prefix used for proof.
