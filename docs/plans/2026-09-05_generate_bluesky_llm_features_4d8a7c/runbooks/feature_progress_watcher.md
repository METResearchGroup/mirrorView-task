# Runbook: feature progress watcher

## Purpose

Each feature issue of the Bluesky LLM campaign gets one rolling progress comment that is updated every 10,000 durable rows. The watcher CLI in this repository reads the feature's S3 progress state, decides whether a new 10,000 row boundary was reached, prints the comment body, and records the boundary in `watcher.json`. The CLI never posts to GitHub. An operator, or a short agent the operator starts outside this repository, posts the printed body through its own authenticated GitHub integration and then records the comment id.

## What the watcher reads and writes

The watcher reads these objects under the feature prefix `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/{feature}/`.

| Object | Use |
|--------|-----|
| `progress.jsonl` | The batch line with the largest `durable_row_total` gives the row total, part index, and manifest digest |
| `watcher.json` | `github_comment_id` and `last_posted_milestone` from the previous run |
| `active_openai_batch.json` | The provider job that is running now, shown as the active batch, or `idle` when absent |
| `smoke/cost_report.json` | The full run estimate, scaled to the rows labeled so far, or `unavailable` when absent |

The only object the watcher writes is `watcher.json`, through a conditional replace. It never touches batch objects, `manifest.json`, or labels.

## Run the watcher once

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --once
```

When a new boundary was reached, the output starts with `boundary_crossed=true`, names the boundary, and prints the comment body between the `rolling_comment<<<` and `>>>rolling_comment` lines. The watcher has already saved that boundary in `watcher.json` by the time it prints.

When no new boundary was reached, the output is three lines. `boundary_crossed=false`, `duplicate_boundary_suppressed=true` when the current boundary was already reported, and `github_write_skipped=true`. Nothing was written.

## Post the comment

The operator agent, not repository code, does the GitHub work.

1. Copy the text between `rolling_comment<<<` and `>>>rolling_comment`.
2. If `watcher.json` holds a `github_comment_id`, update that comment on the feature issue with the new body. Otherwise create a new comment on the feature issue.
3. After the first comment exists, record its id so the next run updates the same comment instead of adding one.

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --feature is_news_or_opinion \
  --once \
  --github-comment-id <comment id>
```

The output includes `github_comment_id_recorded=<comment id>` and `watcher_json_updated=true`. Do not prescribe or run `gh` write commands from the read only cloud CLI. Use the agent's own authenticated GitHub integration.

## Restart after an interruption

The watcher keeps no state in memory between runs, so restarting is the same as running it again. Because `last_posted_milestone` was saved before the body was printed, a restart after a crash prints the same boundary again only if the crash happened before the `watcher.json` replace. If the agent posted a comment but was interrupted before recording the id, run the `--github-comment-id` command above once. If two watchers run at the same time, the one whose conditional replace loses exits with a `ConditionalWriteConflict` error and should simply be rerun.

To watch a feature until it finishes, run the `--once` command on a schedule, e.g. every 15 minutes, from an operator shell or an external scheduler. Do not add a loop or a daemon inside the repository.

## Reading the comment

```markdown
## Feature progress: is_news_or_opinion
Campaign: bluesky_2026_09_03_235130_llm_features_v1
Durable rows: 10000 / 200000 (5.0%)
Latest part: 4 (manifest sha256: <64 hex characters>)
Estimated cost to date: $0.42
Active OpenAI batch: idle
Updated: 2026_09_06-03:57:14
```

`Durable rows` counts rows in immutable batch objects listed in `manifest.json`, not rows in flight. `Latest part` is the zero based index of the last batch object. `Estimated cost to date` scales the smoke report's average full run estimate to the durable rows. `Active OpenAI batch` names the provider job that is polling right now, or `idle`. `Updated` is the UTC time in the repository's `YYYY_MM_DD-HH:MM:SS` format.

## If the watcher fails

- `progress line N is not a valid batch record`. A batch line does not match the schema in `data_platform/generate_features/progress_record.py`. Inspect the line, and open an issue against the feature run. Do not edit `progress.jsonl` by hand.
- `ConditionalWriteConflict`. Another watcher replaced `watcher.json` between this run's read and write. Rerun.
- Missing AWS credentials. Export the two variables shown above. The watcher needs `s3:GetObject`, `s3:PutObject`, and `s3:ListBucket` on the feature prefix.
