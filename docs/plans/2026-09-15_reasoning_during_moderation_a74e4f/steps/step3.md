# Step 3: Run experiment 1

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py` `main` without `--smoke`
- **Task:** For every cohort post, generate one completion per model with the study prompt and no criteria addendum. Reuse the stored Post 1 / Post 2 order and the generation seed from Step 2. Store traces and thinking-token counts. Write a six-row summary table. Do not score keep or remove accuracy.
- **Out of scope:** Experiment 2, human times, bag-of-words, `RESULTS.md`, changing the prompt renderer, shuffling pair order, downsampling the cohort.

## Dependencies

Step 1 uploaded the three-group cohort. Step 2 smoke printed `thinking_enabled=true` and a non-zero thinking-token count for both models. Do not start the full run until that smoke has passed.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md` | Six-row table, no F1, no downsample |
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step1.md` | Cohort path and group names |
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step2.md` | Renderer, runner, seeds, resume, Hugging Face Jobs |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/runner.py` | Shared completion helper from Step 2 |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/jobs.py` | Job command builder from Step 2 |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/summarize.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_summarize_tokens.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (add the full-run command only)

## Files forbidden to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py`
- `/workspace/webapp/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/**`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## Run contract

`add_criteria` is false.

One completion per `post_id` per model. Load every eligible cohort row. Do not sample a subset after the count confirmation.

Reuse `post_1_role` from the cohort. Reuse `generation_seed(post_id)`. Do not draw a new pair order. Do not draw a new seed when retrying `infrastructure`.

`max_new_tokens` is 8192.

Write traces incrementally as jsonl. Resume skips `post_id` values already stored for that model. A second full run for a model whose traces already cover the cohort returns without generating.

Local paths:

```text
experiments/reasoning_during_moderation_2026_09_15/experiment1/outputs/traces_qwen.jsonl
experiments/reasoning_during_moderation_2026_09_15/experiment1/outputs/traces_deepseek.jsonl
experiments/reasoning_during_moderation_2026_09_15/experiment1/outputs/token_summary.csv
```

Matching S3 keys under `s3://mirrorview-experimental-artifacts/experiments/reasoning_during_moderation_2026_09_15/experiment1/`. Upload traces with `put_new` only when that key is absent. If a job is resuming a partial traces object, write to a local file and replace the S3 object only through a documented resume helper that does not use `put_new` on a different experiment's keys.

Each jsonl row includes `post_id`, `group`, `model_id`, `prompt_arm` equal to `study`, `post_1_role`, `post_2_role`, `generation_seed`, `status`, `thinking_token_count`, `thinking_text`, `completion_text`, and `max_new_tokens`.

## Summary table contract

`summarize_tokens(traces)` builds six rows, one per model and group.

Row identity: `model_id` × `group`, with `group` in the order `split`, `unanimous_keep`, `unanimous_remove`.

Columns:

| Column | Meaning |
|--------|---------|
| `model_id` | Hugging Face id |
| `group` | Analysis group |
| `n_posts` | Cohort posts in that group |
| `n_valid` | Rows with `status=valid` |
| `mean` | Mean `thinking_token_count` on valid rows |
| `median` | Median on valid rows |
| `p25` | 25th percentile on valid rows |
| `p75` | 75th percentile on valid rows |
| `max` | Maximum on valid rows |
| `truncated_rate` | Fraction of `n_posts` with `status=truncated` |
| `empty_thinking_rate` | Fraction of `n_posts` with `status=empty_thinking` |

Do not write F1, accuracy, precision, or recall. Do not parse `Allow` or `Remove` from `completion_text` for a score table.

Percentiles use the default numpy percentile on the valid counts. Empty valid sets write `NaN` for mean, median, p25, p75, and max, and still write the rate columns.

## Pytest files

### `tests/test_summarize_tokens.py`

Class `TestSummarizeTokens`.

```text
given two models and three groups with known valid counts 10, 20, 30 and 11, 21, 31
when summarize_tokens
then the frame has six rows
and mean for Qwen split equals 10
and no column is named f1 or accuracy

given one truncated row and one valid row in a group of two posts
when summarize_tokens
then truncated_rate is 0.5
and n_valid is 1
```

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --model qwen
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --model deepseek
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --summarize
```

On a machine without a GPU, run the first two commands through the Hugging Face Job built in Step 2, one job per model. `--summarize` can run locally from the jsonl files.

Expected `--summarize` stdout includes `rows=6` and `prompt_arm=study`. Expected file `token_summary.csv` has six data rows.

Pytest:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_summarize_tokens.py -q
```

Expected: exit 0.

## Must pass

- Every cohort post has a trace row per model, or a documented `infrastructure` retry that then writes the row.
- Pair order in each trace equals the cohort pair order for that `post_id`.
- Generation seed in each trace equals `generation_seed(post_id)`.
- Summary has six rows and no accuracy columns.
- `put_new` lands traces under the experiment 1 S3 prefix.

## Must fail

- Downsampling the cohort.
- `add_criteria=true`.
- Scoring keep or remove against human labels.
- A new shuffle of Post 1 and Post 2.
- A new generation seed on retry.
- Writing the summary before both models have traces.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `experiment1/run.py` `main` without `--smoke` as the caller.

Phase 2 scaffolds `summarize.py` and extends `run.py` with a full-run path that is still stubbed.

Phase 3 locks the summary columns.

Phase 4 writes `test_summarize_tokens.py`.

Phase 5 implements `summarize_tokens`, then the full-run loop, then S3 upload.

Phase 6 is complete when the summarize pytest is green and the six-row csv writer is wired.
