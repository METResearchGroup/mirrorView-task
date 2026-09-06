# Step 1: Add the progress schema, the enriched batch line, the watcher CLI, the seed helper, and the runbook

## Goal

Make every durable batch append one validated `progress.jsonl` line with cumulative totals, persist the rolling comment state in `watcher.json`, and give an operator one short command that prints the rolling comment body at each new 10,000 row boundary and never repeats a boundary after a restart.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md`, and the shared layout is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md`. Every locked value below is copied from those two files. If this file disagrees with them, they win and this file is wrong.

## Main caller

`data_platform/generate_features/feature_progress_watcher.py` `main`, run as a Typer command. Steps 8 through 14 run it after each batch of feature runs.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --once
```

That command reads the canonical feature prefix and is not run in this PR. The live proof in this file passes `--smoke-prefix` with the disposable prefix and `--dry-render`.

Happy path through the caller: resolve the feature paths, read every `progress.jsonl` line and keep the batch lines, validate them and take the one with the largest `durable_row_total`, read `watcher.json`, compute the boundary, and either print the comment body and replace `watcher.json` or print that no boundary was crossed.

The second caller is `_record_batch` in `data_platform/generate_features/s3_feature_batches.py`, which `write_batch` and `adopt_unrecorded_batch` call after `save_manifest`. It builds one `ProgressRecord` and appends it.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step7.md` | Locked contracts, commands, allowed and forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | `watcher.json` fields, append semantics, layout |
| `data_platform/generate_features/generate_features.py` | How `write_batch` and `adopt_unrecorded_batch` are called and when `delete_active_state` runs |
| `data_platform/generate_features/campaign_cost_report.py` | Cost report field names `estimated_full_run_usd_avg` and `full_run_post_count` |
| `data_platform/generate_features/models.py` | `Q44ProvenanceModel` as the Pydantic style to follow |
| `data_platform/utils/object_store.py` | `sha256_hex` |
| `lib/timestamp_utils.py` | `get_current_timestamp` |

## Files allowed to change

- `data_platform/generate_features/progress_record.py` (new)
- `data_platform/generate_features/feature_progress_watcher.py` (new)
- `data_platform/generate_features/seed_progress_watcher_smoke.py` (new, temporary, deleted in the last commit)
- `data_platform/generate_features/s3_feature_batches.py` (`_record_batch` only)
- `data_platform/generate_features/s3_feature_campaign.py` (`watcher.json` key, `manifest_sha256`, progress reader, watcher state helpers)
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/runbooks/feature_progress_watcher.md` (new)
- `docs/plans/2026-09-06_feature_progress_watcher_8aaf41/**` (this plan)

`CHANGELOG.md` is edited only in a separate commit after implementation.

## Files forbidden to change

- `tests/**`
- `data_platform/generate_features/engines/**`, `openai_batch_state.py`, `generate_features.py`, `generate_bluesky_features.py`, `registry.py`, `models.py`, `metadata.py`, `smoke_bluesky_campaign.py`, `campaign_cost_report.py`, `deterministic_smoke_sample.py`
- Feature prompt modules under `data_platform/generate_features/is_*`, `political_stance`, `llm_toxicity_tiered`
- `data_platform/utils/**`, `lib/**`, `webapp/**`, `experiments/**`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md`, `campaign_contract.md`, and every step file other than `steps/step7.md`
- Any GitHub API client, any `gh` write command, and any code that starts agents

Stage files by explicit path only. Never run `git add -A` or `git add .`. The 24 Bluesky dump parquet files that `git status` lists as modified are an LFS artifact and are never staged.

## S3 rules for this step

- The only S3 writes allowed are under `s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step7_progress_watcher/`.
- The only S3 deletes allowed are of objects under that same prefix.
- Never write under any canonical `{feature}/` prefix.
- Never touch the 53 objects that Step 1 of the epic copied.
- No OpenAI call.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts`, region `us-east-2` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Run id | `{campaign_id}:{feature}` |
| Expected rows per feature | `200000` |
| Milestone size | `10000` rows |
| Progress key | `{feature prefix}progress.jsonl`, logical append with `If-Match` |
| Watcher key | `{feature prefix}watcher.json`, conditional atomic replace with `If-Match` |
| Watcher fields | `github_comment_id` (integer or null), `last_posted_milestone` (integer, 0 before the first post) |
| Timestamp format | `get_current_timestamp()`, which is `YYYY_MM_DD-HH:MM:SS` UTC |
| Smoke prefix override | `--smoke-prefix s3://bucket/root/` puts the feature under `root/{feature}/`, so the objects land at `root/{feature}/progress.jsonl` and `root/{feature}/watcher.json` |
| Cost to date | `durable_row_total * estimated_full_run_usd_avg / full_run_post_count` from `{feature prefix}smoke/cost_report.json`, or `unavailable` |

## Progress line fields

Every batch line holds these fields. The first twelve come from `step7.md`. The rest are the Step 5 fields, kept so the line stays a superset of what Step 5 wrote.

| Field | Value |
|-------|-------|
| `campaign_id` | manifest `campaign_id` |
| `feature` | manifest `feature` |
| `run_id` | `{campaign_id}:{feature}`, must equal the `run_id` passed to the writer |
| `recorded_at` | `get_current_timestamp()` |
| `part_index` | the part just recorded |
| `batch_row_count` | rows in that batch object |
| `durable_row_total` | sum of `row_count` over every manifest batch entry after the append |
| `expected_row_total` | manifest `expected_row_count` |
| `percent_complete` | `durable_row_total / expected_row_total` |
| `last_source_record_id` | `source_record_id` of the last row of the batch, in batch order |
| `manifest_sha256` | SHA-256 of the manifest bytes just uploaded |
| `active_openai_batch_id` | `batch_id` of the S3 `active_openai_batch.json`, or null when absent |
| `ts` | same value as `recorded_at` |
| `event` | `batch` |
| `key` | batch object key |
| `row_count` | same value as `batch_row_count` |
| `sha256` | SHA-256 of the batch object bytes |
| `provider_batch_ids` | distinct provider batch ids of the rows, in row order |
| `rows_total` | same value as `durable_row_total` |
| `batches_total` | number of manifest batch entries |

## Contracts

`data_platform/generate_features/progress_record.py`:

- `PROGRESS_EVENT_BATCH = "batch"`
- `class ProgressRecord(BaseModel)` with `extra="forbid"`, the twenty fields above, `event: str = "batch"`, and the eight Step 5 fields optional with `None` defaults. Validators reject a `run_id` that is not `{campaign_id}:{feature}`, a `durable_row_total` below `batch_row_count`, and a `percent_complete` that is not `durable_row_total / expected_row_total` within `1e-9`.
- `parse_batch_records(lines: Iterable[str]) -> list[ProgressRecord]` parses each non empty JSON line, keeps lines whose `event` is `batch`, validates them, and raises `ValueError` naming the line number when a batch line is invalid.
- `latest_batch_record(records: Sequence[ProgressRecord]) -> ProgressRecord | None` returns the record with the largest `durable_row_total`, or None for an empty list.

`data_platform/generate_features/s3_feature_campaign.py`:

- `WATCHER_FILENAME = "watcher.json"` and `FeaturePaths.watcher_key`.
- `manifest_sha256(manifest: dict) -> str` returns the SHA-256 of the exact bytes `save_manifest` uploads for `manifest`.
- `read_progress_lines(store, paths) -> list[str]` returns the lines of `progress.jsonl`, or an empty list when the object is absent.
- `load_watcher_state(store, paths) -> tuple[dict | None, str | None]` and `save_watcher_state(store, paths, state, etag) -> str`, the same shape as `load_manifest` and `save_manifest`.

`data_platform/generate_features/s3_feature_batches.py`:

- `_record_batch` gains the keyword `last_source_record_id: str` and builds the appended line through `ProgressRecord(...).model_dump()`. `write_batch` passes the last row's id, and `adopt_unrecorded_batch` passes the last id of the stored frame. `PROGRESS_EVENT_BATCH` is imported from `progress_record.py` so the constant has one home.

`data_platform/generate_features/feature_progress_watcher.py`:

- `MILESTONE_ROWS = 10_000`, `COMMENT_OPEN = "rolling_comment<<<"`, `COMMENT_CLOSE = ">>>rolling_comment"`.
- `resolve_feature_paths(campaign_id: str, feature: str, smoke_prefix: str | None) -> FeaturePaths` returns the canonical paths, or `FeaturePaths.from_root_uri(smoke_prefix, feature)`, and raises `ValueError` when a smoke prefix overlaps the canonical feature prefix.
- `crossed_boundary(durable_row_total: int, last_posted_milestone: int) -> int | None` returns the new boundary or None.
- `estimated_cost_to_date(cost_report: dict | None, durable_row_total: int) -> float | None`.
- `render_rolling_comment(record: ProgressRecord, *, active_openai_batch_id: str | None, cost_to_date_usd: float | None, updated_at: str) -> str` returns the markdown block with the five required sections.
- `@dataclass(frozen=True) class WatcherOutcome` with `boundary`, `duplicate_suppressed`, `watcher_state`, `watcher_updated`, `comment`, `github_comment_id_recorded`.
- `run_watcher_once(store, paths, *, github_comment_id: int | None) -> WatcherOutcome`.
- `output_lines(outcome: WatcherOutcome) -> list[str]`.
- `main(campaign_id, feature, smoke_prefix, dry_render, once, github_comment_id)` Typer command. Without `--once` it raises a usage error, because the CLI has no other mode.

`data_platform/generate_features/seed_progress_watcher_smoke.py` (temporary):

- `main(campaign_id, feature, smoke_prefix, durable_row_total)` Typer command. It requires `--smoke-prefix`, raises `ValueError` when the prefix does not contain `/_smoke/`, writes `durable_row_total / 2000` cumulative batch lines to `progress.jsonl`, writes `watcher.json` with `github_comment_id` null and `last_posted_milestone` 0, overwrites both objects when they exist, and prints the four lines from `step7.md`.

## Watcher stdout

When a new boundary is crossed:

```text
boundary_crossed=true
boundary=<n>
watcher_json_updated=true
github_write_skipped=true
rolling_comment<<<
<comment body>
>>>rolling_comment
```

When no new boundary is crossed:

```text
boundary_crossed=false
duplicate_boundary_suppressed=<true when the current boundary is at least 10000 and already posted, else false>
github_write_skipped=true
```

When `--github-comment-id` is passed, `watcher_json_updated=true` and `github_comment_id_recorded=<id>` are printed even without a new boundary, because the id is saved.

## Rolling comment body

```markdown
## Feature progress: {feature}
Campaign: {campaign_id}
Durable rows: {durable_row_total} / {expected_row_total} ({percent:.1f}%)
Latest part: {part_index} (manifest sha256: {manifest_sha256})
Estimated cost to date: ${cost:.2f} or unavailable
Active OpenAI batch: {batch_id} or idle
Updated: {updated_at}
```

## Scenarios (given, when, then)

No pytest is added. These scenarios are the behavior the offline check and the live proof prove.

1. Given the eleven keyword arguments from `step7.md`, when `ProgressRecord` is constructed, then it validates and `expected_row_total` is 200000.
2. Given `run_id` `other:feature`, when `ProgressRecord` is constructed, then it raises a validation error.
3. Given lines with events `batch`, `final`, and `batch`, when `parse_batch_records` runs, then it returns two records and `latest_batch_record` returns the one with the larger total.
4. Given a manifest with two batch entries of 2000 rows, when `_record_batch` runs for the second, then the appended line has `durable_row_total` 4000, `batches_total` 2, `percent_complete` 0.02, and `manifest_sha256` equal to the SHA-256 of the saved manifest bytes.
5. Given `durable_row_total` 10000 and `last_posted_milestone` 0, when the watcher runs, then it prints `boundary=10000` and `watcher.json` holds `last_posted_milestone` 10000.
6. Given the same progress and `last_posted_milestone` 10000, when the watcher runs, then it prints `boundary_crossed=false` and `duplicate_boundary_suppressed=true` and does not replace `watcher.json`.
7. Given `durable_row_total` 9999 and `last_posted_milestone` 0, when the watcher runs, then it prints `boundary_crossed=false` and `duplicate_boundary_suppressed=false`.
8. Given `durable_row_total` 35000 and `last_posted_milestone` 10000, when the watcher runs, then it prints `boundary=30000` once.
9. Given no `smoke/cost_report.json`, when the comment renders, then the cost line reads `unavailable`. Given a report with `estimated_full_run_usd_avg` 8.4 and `full_run_post_count` 200000, and 10000 rows, then it reads `$0.42`.
10. Given a `--smoke-prefix` that equals or contains the canonical feature prefix, when the watcher or the seed helper starts, then it raises `ValueError` before any S3 call.

## Ordered implementation work

1. Scaffold `progress_record.py`, `feature_progress_watcher.py`, and `seed_progress_watcher_smoke.py` with stub bodies and a thin `main` in each, plus `WATCHER_FILENAME` and `FeaturePaths.watcher_key`. Commit.
2. Fill in the signatures above with stub bodies. Commit.
3. Write the offline scenario script under `/tmp/step7_checks.py` that exercises scenarios 1, 2, 3, 5 through 9 through the public functions with an in memory fake store, and record that it fails on the stubs. The script lives outside the repository and is not committed. Commit the watcher's `output_lines` and comment template as the executable spec of the stdout.
4. Implement `ProgressRecord`, `parse_batch_records`, and `latest_batch_record`. Run the offline schema check. Commit.
5. Implement `manifest_sha256`, `read_progress_lines`, `load_watcher_state`, and `save_watcher_state`. Commit.
6. Fill `ProgressRecord` from `_record_batch` and pass `last_source_record_id` from both callers. Commit.
7. Implement `resolve_feature_paths`, `crossed_boundary`, `estimated_cost_to_date`, `render_rolling_comment`, `run_watcher_once`, and `main`. Run the scenario script to green. Commit.
8. Implement the seed helper. Commit.
9. Write `runbooks/feature_progress_watcher.md`. Commit.
10. Run the live proof below: seed, watcher twice, compare `watcher.json` bytes, clean the prefix, list it. Record observed output for the PR body.
11. Run `uv run pytest -q`. Expect 631 passed.
12. After review, delete `seed_progress_watcher_smoke.py` in its own commit.

## Exact commands with expected output

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

### Seed the disposable prefix

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

### First watcher run

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --dry-render \
  --once
```

Expected stdout:

```text
boundary_crossed=true
boundary=10000
watcher_json_updated=true
github_write_skipped=true
rolling_comment<<<
## Feature progress: is_news_or_opinion
Campaign: bluesky_2026_09_03_235130_llm_features_v1
Durable rows: 10000 / 200000 (5.0%)
Latest part: 4 (manifest sha256: <64 hex characters>)
Estimated cost to date: unavailable
Active OpenAI batch: idle
Updated: <YYYY_MM_DD-HH:MM:SS>
>>>rolling_comment
```

### Second watcher run (restart idempotence)

Run the same command again without changing the seeded progress. Before the run, download `watcher.json` and keep its bytes.

Expected stdout:

```text
boundary_crossed=false
duplicate_boundary_suppressed=true
github_write_skipped=true
```

Expected S3 effect: `watcher.json` bytes are identical before and after the second run, and its content is `{"github_comment_id": null, "last_posted_milestone": 10000}`.

### Disposable prefix cleanup (required before merge)

The `aws` CLI is not installed in this environment, so the cleanup uses boto3 with the same effect.

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
import boto3
s3 = boto3.client('s3', region_name='us-east-2')
bucket = 'mirrorview-experimental-artifacts'
prefix = 'data_platform/data/_smoke/step7_progress_watcher/'
keys = [o['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix) for o in page.get('Contents', [])]
for key in keys:
    print('delete:', key)
if keys:
    s3.delete_objects(Bucket=bucket, Delete={'Objects': [{'Key': k} for k in keys]})
left = s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get('KeyCount', 0)
print('remaining_under_disposable_prefix=', left)
"
```

Expected: one `delete:` line per seeded object (`.../is_news_or_opinion/progress.jsonl` and `.../is_news_or_opinion/watcher.json`), then `remaining_under_disposable_prefix= 0`.

### Existing suite

```bash
cd /workspace
uv run pytest -q
```

Expected: `631 passed`.

## Must pass

- The offline check prints `ProgressRecord schema OK`.
- The seed prints the four expected lines.
- The first watcher run prints `boundary=10000` and a comment body with the seven lines above, and the second run prints `duplicate_boundary_suppressed=true` with `watcher.json` unchanged.
- The cleanup prints `remaining_under_disposable_prefix= 0`.
- `uv run pytest -q` reports 631 passed with no test file changes.

## Must fail

- A `ProgressRecord` whose `run_id` is not `{campaign_id}:{feature}`, whose `durable_row_total` is below `batch_row_count`, or whose `percent_complete` does not match the two totals.
- A watcher or seed `--smoke-prefix` that overlaps the canonical feature prefix.
- A seed `--smoke-prefix` without `/_smoke/` in its key.
- A watcher run without `--once`.
