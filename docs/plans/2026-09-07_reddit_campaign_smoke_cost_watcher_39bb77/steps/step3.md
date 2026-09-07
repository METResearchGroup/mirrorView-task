# Step 3: Run offline checks, one live proof, and cleanup

## Scope

- **Caller:** the commands in this file, run from `/workspace` with `PYTHONPATH=.`.
- **Task:** Prove the sample selector, watcher paths, mixed-engine aggregate shape, and one live `is_political` smoke under the disposable prefix. Then delete the disposable S3 prefix and temporary Git copies under `reports/smoke/{feature}/`. Keep `deterministic_ten_comment_ids.json`.
- **Out of scope:** Product behavior changes except deleting those temporary report files. No pytest. No 400000-row production. No issues 222 through 229.

## Files to inspect

- `data_platform/generate_features/smoke_reddit_campaign.py`
- `data_platform/generate_features/feature_progress_watcher.py`
- `data_platform/generate_features/campaign_cost_report.py`
- `data_platform/generate_features/deterministic_smoke_sample.py`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/deterministic_ten_comment_ids.json`

## Files allowed to change

- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}/` may exist during the live proof and must be deleted before the last commit.
- No other product files unless a check reveals a correctness bug from Step 1 or Step 2. If a bug is found, fix it in the owning file from those steps and re-run the failing check.

## Files forbidden to change

- `tests/**`
- `registry.py` engine defaults
- `campaign_engine_map.py`
- migrate scripts
- `CHANGELOG.md` (updated only after the pull request exists)
- Primary S3 campaign prefixes

## Environment

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export GH_TOKEN="$METRESEARCHGROUP_GITHUB_PAT_TOKEN"
export GH_PROMPT_DISABLED=1
```

Never echo those values.

If the comments parquet is an LFS pointer, pull it before check 1:

```bash
git lfs pull --include "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet"
```

## Check 1: Offline deterministic sample

```bash
cd /workspace
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.generate_reddit_features import REDDIT_SPEC
from data_platform.generate_features.deterministic_smoke_sample import load_deterministic_ten_post_ids_for_spec
ids = load_deterministic_ten_post_ids_for_spec(
    REDDIT_SPEC,
    'reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079',
    '2026_09_03-23:39:28',
)
assert len(ids) == 10
assert ids == sorted(ids)
print('deterministic_ten_comment_ids OK')
print('first_id=' + ids[0])
"
```

Expected stdout:

```text
deterministic_ten_comment_ids OK
first_id=<reddit-source-record-id>
```

The committed JSON `source_record_ids` must equal that list.

## Check 2: Watcher paths and no GitHub posting

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.feature_progress_watcher import resolve_feature_paths
paths = resolve_feature_paths(
    'reddit_2026_09_03_233928_llm_features_v1',
    'is_political',
    smoke_prefix=None,
    platform='reddit',
    dataset_id='reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079',
)
assert '/reddit/reddit_3d8a2c41' in paths.prefix
print('watcher paths OK')
"
```

Expected stdout:

```text
watcher paths OK
```

Also run:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/feature_progress_watcher.py --help
```

Expected: help text includes `--platform` and `--dataset-id`.

Confirm the module still does not post to GitHub (search for `api.github.com`, `PyGithub`, and `subprocess` `gh`). Printing `github_write_skipped=true` is required. Recording `--github-comment-id` in `watcher.json` is not posting.

## Check 3: Aggregate command shape (synthetic reports, no seven live smokes)

```bash
PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py --help
```

Expected: help text includes `--aggregate` and `--full-run-row-count`.

Create seven synthetic per-feature reports in a temp directory (not under git). Four OpenAI features and three Bedrock features for campaign `reddit_2026_09_03_233928_llm_features_v1`. Each report needs `campaign_id`, `feature`, `model`, `request_count`, token averages and maxes, `smoke_cost_usd`, and both estimated full-run fields. Then:

```bash
PYTHONPATH=. uv run python data_platform/generate_features/campaign_cost_report.py \
  --aggregate \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --smoke-reports-dir "$TMPDIR/reddit_step3_synth_reports" \
  --output "$TMPDIR/reddit_step3_synth_reports/parent_cost_aggregate.json" \
  --full-run-row-count 400000
```

Expected stdout includes:

```text
features_included=7
openai_features=4
bedrock_features=3
full_run_row_count=400000
```

Repeat with seven OpenAI synthetic reports for `bluesky_2026_09_03_235130_llm_features_v1` and omit `--full-run-row-count`. Expected `full_run_row_count=200000`, `openai_features=7`, `bedrock_features=0`.

Delete the temp directory. Do not commit synthetic reports.

## Check 4: Live single-feature tooling proof

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step3_campaign_smoke/
PYTHONPATH=. uv run python data_platform/generate_features/smoke_reddit_campaign.py \
  --campaign-id reddit_2026_09_03_233928_llm_features_v1 \
  --dataset-id reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079 \
  --preprocessed-run 2026_09_03-23:39:28 \
  --feature is_political \
  --smoke-prefix "$DISPOSABLE_PREFIX" \
  --output-dir docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/is_political
```

Expected stdout includes:

```text
engine_type=openai
smoke_rows=10
full_run_row_count=400000
s3_smoke_output_ok=true
s3_smoke_resume_evidence_ok=true
no_batches_prefix_objects=true
primary_smoke_prefix_touched=false
```

Do not run the other six features live in this PR.

## Check 5: Cleanup before the last commit

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step3_campaign_smoke/ --recursive
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step3_campaign_smoke/ --recursive
```

Expected: `aws s3 ls` prints no lines.

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_political/smoke/ 2>&1 || true
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_political/batches/ 2>&1 || true
```

Expected: empty listing or `NoSuchKey`.

Delete every temporary Git copy under `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/reports/smoke/{feature}/`. Keep `deterministic_ten_comment_ids.json`.

## What must pass

All five checks. Record `first_id` from check 1 in the pull request body.

## What must fail / stop

- Live proof writing primary smoke or batches objects.
- Disposable prefix still listing objects after cleanup.
- Temporary `{feature}/` report directories still in git at the last commit.
- Running pytest or adding `tests/**`.
- Closing keyword on issue 218.

## After verification

Do not use `gh pr create`. Stay on `cursor/epic-218-221-reddit-smoke-cost-watcher-flags-d983`. Push, then:

```bash
GH_TOKEN="$METRESEARCHGROUP_GITHUB_PAT_TOKEN" gh stack submit --open --auto --remote origin
```

Then `gh pr edit` so this layer includes `Fixes #221` and `Part of #218` and never a closing keyword on 218.

Title: `Add Reddit campaign smoke, mixed-engine cost aggregate, and watcher platform flags`

Body must state: tooling only, no full runs, disposable smoke prefix used for proof, primary smoke deferred, no GitHub posting from repo code.

This PR's base must be `cursor/epic-218-219-campaign-engine-map-bedrock-path-d983`.
