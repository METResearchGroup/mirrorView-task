# Step 5: Report human response times

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py` `main`
- **Task:** On the slim trials from Step 1, summarize `response_time_ms` for split, unanimous keep, and unanimous remove. Report trial-level and post-mean mean, median, p25, p75, max, and row counts. Do not use the `rt` column.
- **Out of scope:** Model runs, bag-of-words, rewriting the cohort builder, editing the website, `RESULTS.md`.

## Dependencies

Step 1 wrote `slim_trials.parquet` with `group` and `response_time_ms`. Load that file, or the matching S3 object. Do not re-download the Prolific CSVs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md` | Trial-level and post-mean tables, long right tail |
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step1.md` | Slim-trial columns |
| `/workspace/webapp/public/plugins/plugin-moderation-trial.js` | `response_time_ms` is `performance.now()` delta on the choice click |
| `/workspace/webapp/public/main.js` | `rt` is a jsPsych field and is empty on these rows |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment3/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment3/summarize.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_summarize_response_times.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (add the experiment 3 command only)

## Files forbidden to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py`
- `/workspace/webapp/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## Summary contract

`usable_times(slim)` keeps rows whose `response_time_ms` is finite and greater than 0. Drop NA. Do not read `rt`. Do not winsorize. The plan reports the tail, so keep the max.

`trial_level_summary(slim)` groups the usable rows by `group` and writes n, mean, median, p25, p75, and max of `response_time_ms`.

`post_mean_summary(slim)` first averages usable `response_time_ms` per `post_id`, then writes the same stats across those post means, still grouped by `group`.

Group order is `split`, `unanimous_keep`, `unanimous_remove`.

On the 2026-09-15 snapshot, trial medians were about 12.6 seconds for split, 13.8 seconds for unanimous keep, and 9.9 seconds for unanimous remove. The live command must print those medians in milliseconds. Do not fail the step if a later export moves the medians. Fail if any group has zero usable times.

Local path:

```text
experiments/reasoning_during_moderation_2026_09_15/experiment3/outputs/response_time_summary.csv
```

S3 key:

```text
experiments/reasoning_during_moderation_2026_09_15/experiment3/response_time_summary.csv
```

CSV columns:

| Column | Meaning |
|--------|---------|
| `level` | `trial` or `post_mean` |
| `group` | Analysis group |
| `n` | Row count at that level |
| `mean` | Mean milliseconds |
| `median` | Median milliseconds |
| `p25` | 25th percentile |
| `p75` | 75th percentile |
| `max` | Maximum milliseconds |

Six data rows: three groups times two levels.

## Pytest files

### `tests/test_summarize_response_times.py`

Class `TestUsableTimes`, class `TestTrialLevelSummary`, class `TestPostMeanSummary`.

```text
given rows with response_time_ms 1000, 2000, NA, 0, and -5, plus an rt column of 999
when usable_times
then only 1000 and 2000 remain

given post A with times 10 and 30 in group split, and post B with time 20 in group split
when trial_level_summary
then n is 3 and median is 20
when post_mean_summary
then n is 2 and the two post means are 20 and 20
and the rt column is never read
```

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
```

Expected stdout includes `rows=6` and `level=trial` and `level=post_mean` counts for all three groups. Expected csv has six data rows.

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_summarize_response_times.py -q
```

Expected: exit 0.

## Must pass

- Only `response_time_ms` is summarized.
- Trial-level and post-mean rows both exist.
- Zero and NA times are dropped.
- Pytest does not download S3.

## Must fail

- Using the `rt` column.
- Dropping the long right tail before the max is computed.
- Re-exporting Prolific CSVs in this step.
- Mixing practice trials back in.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `experiment3/run.py` `main` as the caller.

Phase 2 scaffolds `summarize.py` and `run.py`.

Phase 3 locks the csv columns.

Phase 4 writes `test_summarize_response_times.py`.

Phase 5 implements `usable_times`, then `trial_level_summary`, then `post_mean_summary`, then `main`.

Phase 6 is complete when the pytest command exits 0 and the csv writer is wired.
