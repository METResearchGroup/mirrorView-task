# Step 2: Run the command and write RESULTS.md

## Scope

- **Caller:** the same `run.py` `main` from Step 1.
- **Task:** Re-run the Step 1 pytest command, export AWS credentials, run the live remaining-labels command, confirm the local CSV and the S3 object, prove the live party-mix rules on that CSV, copy logs to `/opt/cursor/artifacts/`, and commit `RESULTS.md` with 10:10 count, left-only count, extra labels, unused remaining labels, SHA-256, and remaining versus assigned slots by cell.
- **Out of scope:** Rewriting Step 1 modules except docstring fixes, adding files under the repo-root `tests/` folder, changing catalogs, changing the remaining labels CSV, changing the assignment Lambda, uploading to the study website assignment bucket.

## Files to inspect (read-only)

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/run.py`
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/README.md`
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/constants.py`
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/assign.py`
- `/workspace/docs/plans/2026-09-09_study_user_assignments_ac7f04/plan.md`
- `/workspace/docs/plans/2026-09-09_study_user_assignments_ac7f04/steps/step1.md`

## Files allowed to change

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/RESULTS.md` (written by the live command, then committed)
- `/workspace/experiments/generate_study_user_assignments_2026_09_08/README.md` only to add the live 10:10 count, left-only count, and assignment row count
- `/workspace/CHANGELOG.md` after the live S3 object exists

## Files forbidden to change

- `/workspace/experiments/generate_study_user_assignments_2026_09_08/tests/**`
- `/workspace/webapp/lambdas/lambda-get-post-assignments.mjs`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/**`
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-09_study_user_assignments_ac7f04/**`
- The remaining labels S3 object
- The pull request 273 catalog S3 object

## Pytest gate

Run this before the live command. Do not upload if pytest fails.

```bash
PYTHONPATH=. uv run pytest experiments/generate_study_user_assignments_2026_09_08/tests -q
```

Expected: exit 0.

## Live commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```

Expected stdout includes `ten_ten_count=3202`, `left_only_count=677`, `user_count=3879`, `assignment_rows=3879`, `assignment_slots=77580`, `extra_labels=23`, `unused_remaining=0`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv`, and `csv_sha256=`.

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib
import json
from pathlib import Path

import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

local = Path(
    "experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv"
)
shuffled = Path(
    "experiments/generate_study_user_assignments_2026_09_08/shuffled_stimuli.csv"
)
store = CampaignObjectStore("mirrorview-experimental-artifacts")
key = "experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv"
stored = store.get(key)
assert stored is not None
frame = pd.read_csv(local)
assert list(frame.columns) == [
    "id",
    "assigned_post_ids",
    "political_party",
    "condition",
    "created_at",
]
assert len(frame) == 3879
joined = pd.read_csv(shuffled)
stance_by_id = dict(
    zip(joined["post_primary_key"].astype(str), joined["sampled_stance"])
)
mixes = []
for row in frame.itertuples(index=False):
    post_ids = json.loads(row.assigned_post_ids)
    assert len(post_ids) == 20
    assert len(set(post_ids)) == 20
    left = sum(stance_by_id[post_id] == "left" for post_id in post_ids)
    right = sum(stance_by_id[post_id] == "right" for post_id in post_ids)
    mixes.append((left, right))
assert mixes[:3202] == [(10, 10)] * 3202
assert mixes[3202:] == [(20, 0)] * 677
assert hashlib.sha256(local.read_bytes()).hexdigest() == hashlib.sha256(
    stored.body
).hexdigest()
print("live party mix ok", len(frame), mixes.count((10, 10)), mixes.count((20, 0)))
PY
```

Expected: `live party mix ok 3879 3202 677`.

Copy the live command stdout to `/opt/cursor/artifacts/study_user_assignments_run.log`. Copy the party-mix check stdout to `/opt/cursor/artifacts/study_user_assignments_party_mix.log`.

A second run of the same live command must raise `FileExistsError`.

## Remaining by cell on the pull request 279 file

After joining remaining ids to the catalogs, remaining labels by cell should be:

| Cell | Remaining |
| ---- | --------: |
| 1 left low | 10445 |
| 2 left middle | 22001 |
| 3 left high | 13096 |
| 4 right low | 8791 |
| 5 right middle | 16594 |
| 6 right high | 6630 |

Assigned slots by cell depend on steal. Do not pin those counts before the live run. Pin party totals: assigned left slots 45,560, assigned right slots 32,020, extra left 18, extra right 5, unused remaining 0.

## RESULTS.md

`RESULTS.md` must include:

- The pytest command and that it exited 0
- The live run command
- Remaining-labels URI and SHA-256
- New catalog URI and SHA-256
- Local path, S3 URI, and SHA-256 of the assignment CSV
- 10:10 count 3,202
- Left-only count 677
- User count 3,879
- Assignment slots 77,580
- Extra labels 23, split as 5 right and 18 left
- Unused remaining labels 0
- Remaining labels versus assigned slots by cell
- A sentence that users 1 through 3,202 have 10 left and 10 right, and users 3,203 through 3,879 have 20 left and 0 right

## CHANGELOG.md

Add one line under the current date. Say operators now have 3,879 study feeds, 3,202 at 10 left and 10 right and 677 left-only, covering 77,557 remaining labels with 23 extra labels.

## Must pass

- Pytest exits 0 before the live run.
- Live command exits 0 on the first run.
- `ten_ten_count=3202` and `left_only_count=677`.
- `user_count=3879` and `assignment_slots=77580`.
- `extra_labels=23` and `unused_remaining=0`.
- Local SHA-256 equals S3 object SHA-256.
- Live party-mix check prints `live party mix ok 3879 3202 677`.
- `RESULTS.md` is committed and records those counts.
- README live counts match 3,202 / 677 / 3,879.
- Catalog objects and the remaining labels object are unchanged.

## Must fail

- A second run of the same live command, because `put_new` must raise `FileExistsError`.
- The live party-mix check, if any of the first 3,202 feeds is not 10:10, or if any of the last 677 feeds is not 20:0.
