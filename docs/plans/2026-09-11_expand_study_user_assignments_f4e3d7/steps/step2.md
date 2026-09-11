# Step 2: Upload the new assignment prefix and point the lookup Lambda at it

## Scope

- **Caller:** the same `run.py` `main` from Step 1, then `experiments/upsample_mixed_study_feeds_2026_09_11/upload.py` `main`
- **Task:** Re-run the Step 1 pytest command, export AWS credentials, run the live upsample command, prove the first 3879 source rows match pull request 278, upload a new timestamped prefix under `jspsych-mirror-view-2026-09-09`, point the job YAML and lookup Lambda at that prefix, prove a returning participant still receives the same 20 posts, and commit `RESULTS.md`.
- **Out of scope:** Rewriting Step 1 modules except docstring fixes, adding files under the repo-root `tests/` folder, changing stimulus catalogs, overwriting `2026_09_09-23:06:02`, running `terraform apply`, resetting DynamoDB, editing the assignment-service repo.

## Files to inspect (read-only)

- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/run.py`
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/README.md`
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/constants.py`
- `/workspace/docs/plans/2026-09-11_expand_study_user_assignments_f4e3d7/plan.md`
- `/workspace/docs/plans/2026-09-11_expand_study_user_assignments_f4e3d7/steps/step1.md`
- `/workspace/experiments/load_study_assignments_2026_09_09/upload.py`
- `/workspace/experiments/load_study_assignments_2026_09_09/RESULTS.md`
- `/workspace/docs/plans/2026-09-09_init_study_assignments_7db8f4/steps/step3.md`
- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs`
- `/workspace/jobs/config/mirrorview_2026_09_09.yaml`

## Files allowed to change

- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/RESULTS.md` (written by the live command, then committed)
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/README.md` only to add the live `batch_uri`, Democrat row count, and Republican row count
- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/upload.py` (new, if Step 1 did not already include it)
- `/workspace/jobs/config/mirrorview_2026_09_09.yaml` (`assignment.batch_uri` timestamp only)
- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs` (`SEPTEMBER_BATCH_URI` timestamp only, then re-zip and `update-function-code`)
- `/workspace/CHANGELOG.md` after the new prefix exists and the returning-user check passes

## Files forbidden to change

- `/workspace/experiments/upsample_mixed_study_feeds_2026_09_11/tests/**`
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/**`
- `/workspace/experiments/load_study_assignments_2026_09_09/**`
- `/workspace/webapp/infra/main.tf`
- `/workspace/webapp/public/config.js`
- `/workspace/webapp/public/main.js`
- `/workspace/webapp/public/img/flips_2026_09_09.csv`
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-11_expand_study_user_assignments_f4e3d7/**`
- The pull request 273 catalog S3 object
- The pull request 278 source CSV
- `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/**`
- DynamoDB tables `user_assignments` and `study_assignment_counter`

## Pytest gate

Run this before the live command. Do not upload if pytest fails.

```bash
PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q
```

Expected: exit 0.

## Live generate

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
```

Expected stdout includes `base_users=3879`, `mixed_source=3202`, `cloned_feeds=1000`, `user_count=4879`, `democrat_rows=2440`, `republican_rows=2439`, `assignment_slots=97580`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments.csv`, and `csv_sha256=`.

## Identity checks before study-bucket upload

```bash
PYTHONPATH=. uv run python - <<'PY'
import io
import json
from pathlib import Path

import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import sha256_hex

local = Path(
    "experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments.csv"
)
store = CampaignObjectStore("mirrorview-experimental-artifacts")
pinned_key = (
    "experiments/generate_study_user_assignments_2026_09_08/"
    "study_user_assignments.csv"
)
expanded_key = (
    "experiments/upsample_mixed_study_feeds_2026_09_11/"
    "study_user_assignments.csv"
)
pinned_obj = store.get(pinned_key)
assert pinned_obj is not None
pinned = pd.read_csv(io.BytesIO(pinned_obj.body))
frame = pd.read_csv(local)
assert len(frame) == 4879
assert list(frame["id"].head(3879)) == list(pinned["id"])
for left, right in zip(frame["assigned_post_ids"].head(3879), pinned["assigned_post_ids"]):
    assert json.loads(left) == json.loads(right)
cloned = frame.tail(1000)
assert cloned["id"].tolist() == [f"user-{user_id:04d}" for user_id in range(3880, 4880)]
assert cloned["id"].nunique() == 1000
stored = store.get(expanded_key)
assert stored is not None
assert sha256_hex(local.read_bytes()) == sha256_hex(stored.body)
print("source_identity_ok")
print("expanded_rows", len(frame))
PY
```

Expected: `source_identity_ok` and `expanded_rows 4879`.

Download the live party files and compare the original prefix:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python - <<'PY'
import io
import json
from pathlib import Path

import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

live = CampaignObjectStore("jspsych-mirror-view-2026-09-09")
prefix = "precomputed_assignments/2026_09_09-23:06:02"
old_d_obj = live.get(f"{prefix}/democrat/training_assisted/assignments.csv")
old_r_obj = live.get(f"{prefix}/republican/training_assisted/assignments.csv")
assert old_d_obj is not None
assert old_r_obj is not None
old_d = pd.read_csv(io.BytesIO(old_d_obj.body))
old_r = pd.read_csv(io.BytesIO(old_r_obj.body))
new_d = pd.read_csv(
    Path(
        "experiments/upsample_mixed_study_feeds_2026_09_11/batch/"
        "democrat/training_assisted/assignments.csv"
    )
)
new_r = pd.read_csv(
    Path(
        "experiments/upsample_mixed_study_feeds_2026_09_11/batch/"
        "republican/training_assisted/assignments.csv"
    )
)
assert len(new_d) == 2440
assert len(new_r) == 2439
assert list(new_d["id"].head(1940)) == list(old_d["id"])
assert list(new_r["id"].head(1939)) == list(old_r["id"])
for left, right in zip(new_d["assigned_post_ids"].head(1940), old_d["assigned_post_ids"]):
    assert json.loads(left) == json.loads(right)
for left, right in zip(new_r["assigned_post_ids"].head(1939), old_r["assigned_post_ids"]):
    assert json.loads(left) == json.loads(right)
assert new_d.iloc[1940]["id"] == "democrat-training_assisted-1941"
assert new_r.iloc[1939]["id"] == "republican-training_assisted-1940"
print("party_prefix_identity_ok")
PY
```

Expected: `party_prefix_identity_ok`.

Also prove every cloned feed is mixed, and that leftover-left rows were not cloned:

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path

import pandas as pd
from experiments.load_study_assignments_2026_09_09.catalog import stance_by_id
from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    feed_kind,
    parse_post_ids,
)

catalog = pd.read_csv(
    Path("experiments/upsample_mixed_study_feeds_2026_09_11/batch/catalog.csv")
)
stance = stance_by_id(catalog)
frame = pd.read_csv(
    Path("experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments.csv")
)
cloned = frame.tail(1000)
assert cloned["id"].tolist() == [f"user-{user_id:04d}" for user_id in range(3880, 4880)]
kinds = [
    feed_kind(parse_post_ids(cell), stance) for cell in cloned["assigned_post_ids"]
]
assert kinds == [FeedKind.TEN_TEN] * 1000
mixed_sets = {
    tuple(sorted(json.loads(cell)))
    for cell in frame.head(3202)["assigned_post_ids"]
}
left_only_sets = {
    tuple(sorted(json.loads(cell)))
    for cell in frame.iloc[3202:3879]["assigned_post_ids"]
}
for cell in cloned["assigned_post_ids"]:
    post_set = tuple(sorted(json.loads(cell)))
    assert post_set in mixed_sets
    assert post_set not in left_only_sets
print("cloned_mixed_ok")
PY
```

Expected: `cloned_mixed_ok`.

If any identity check fails, stop. Do not upload to the study bucket.

## Upload the new assignment prefix

Use timestamp format matching `/workspace/lib/timestamp_utils.py` (`YYYY_MM_DD-HH:MM:SS`). Call that helper. Do not invent a different layout. Do not reuse `2026_09_09-23:06:02`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/upload.py
```

Expected stdout includes the three keys and `batch_uri=s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>`.

```bash
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/config.yaml --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/democrat/training_assisted/assignments.csv --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/republican/training_assisted/assignments.csv --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/2026_09_09-23:06:02/config.yaml --region us-east-2
```

Expected: all four succeed. The old prefix still exists.

## Point the lookup Lambda at the new prefix

Put that `batch_uri` into `jobs/config/mirrorview_2026_09_09.yaml` `assignment.batch_uri` and into `webapp/lambdas/lambda-get-post-assignments.mjs` `SEPTEMBER_BATCH_URI`. Do not change `STUDY_ITERATION_ID`. Do not run `terraform apply`. Do not reset DynamoDB.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

python - <<'PY'
from pathlib import Path
import zipfile
src = Path("webapp/lambdas/lambda-get-post-assignments.mjs")
out = Path("webapp/infra/get-post-assignments.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(src, "index.mjs")
print(out)
PY

aws lambda update-function-code \
  --function-name jspsych-scroll-get-post-assignments \
  --zip-file fileb://webapp/infra/get-post-assignments.zip \
  --region us-east-2
```

Expected: the command prints a new `CodeSha256`.

Confirm save-data still points at September:

```bash
aws lambda get-function-configuration \
  --function-name jspsych-scroll-save-data \
  --region us-east-2 \
  --query 'Environment.Variables.BUCKET_NAME' \
  --output text
```

Expected: `jspsych-mirror-view-2026-09-09`.

## Returning user and new-dev checks

Do not create a new production assignment. The production iteration is `mirrorview_2026_09_09`. Manual tests already claimed `democrat-training_assisted-0001` and `republican-training_assisted-0001`.

Returning user, production iteration:

```bash
aws lambda invoke \
  --function-name get_study_assignment \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"study_id":"mirrorview","study_iteration_id":"mirrorview_2026_09_09","prolific_id":"manual-test-2026-09-09-d","political_party":"democrat","assignment_batch_uri":"s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>"}' \
  /tmp/upsample_returning.json
```

Expected: the payload has 20 `assigned_post_ids`, and they match the original Democrat row `democrat-training_assisted-0001` from `2026_09_09-23:06:02`. DynamoDB `s3_key` for that user still points at the old prefix. The production counter is unchanged by this returning-user read.

New user, dev iteration only:

```bash
aws lambda invoke \
  --function-name get_study_assignment \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"study_id":"mirrorview","study_iteration_id":"dev-mirrorview_2026_09_09","prolific_id":"manual-cli-upsample-2026-09-11-d","political_party":"democrat","assignment_batch_uri":"s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>"}' \
  /tmp/upsample_new_dev.json
```

Expected: 20 `assigned_post_ids` and `condition` `training_assisted`. A second run with the same prolific id returns the same ids.

If the returning-user check fails, stop. Do not send more production traffic. Leave the old prefix in place. The lookup Lambda can be pointed back at `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02` with the same zip and `update-function-code` steps.

## RESULTS.md and CHANGELOG.md

`RESULTS.md` records base users, mixed source count, cloned feed count, user count, Democrat rows, Republican rows, leftover-left counts, assignment slots, source SHA-256, experimental S3 URI, new `batch_uri`, and a note that `2026_09_09-23:06:02` was left in place and DynamoDB production counters were not reset.

Add one `CHANGELOG.md` line under today's date. The line names 4879 feeds, 2440 Democrat rows, 2439 Republican rows, 1000 cloned mixed feeds, and the new prefix.

Copy the live command stdout to `/opt/cursor/artifacts/upsample_mixed_study_feeds_run.log`. Copy the identity check stdout to `/opt/cursor/artifacts/upsample_mixed_study_feeds_identity.log`.

## Must pass

- Pytest command from Step 1 still exits 0.
- First 3879 source `assigned_post_ids` lists match pull request 278.
- First 1940 Democrat and 1939 Republican `assigned_post_ids` lists match `2026_09_09-23:06:02`.
- Every cloned feed is 10 left and 10 right. The 1000 cloned user ids are unique.
- New prefix exists. Old prefix still exists.
- Lookup Lambda `SEPTEMBER_BATCH_URI` equals the new `batch_uri`.
- Returning production user `manual-test-2026-09-09-d` still receives the same 20 posts.
- Save-data `BUCKET_NAME` is still `jspsych-mirror-view-2026-09-09`.
- Stimulus catalogs are unchanged.
- `RESULTS.md` records 4879, 2440, 2439, 1000 clones, and both prefixes.

## Must fail

- Upload to the study bucket if the identity checks fail.
- Overwrite of `2026_09_09-23:06:02`.
- `terraform apply`.
- A new production assignment created only to test clones.
- Reset of DynamoDB counters.
- Second `put_new` of the experimental source CSV key.
- Any edit of `img/flips_2026_09_09.csv` or the pull request 273 catalog.
