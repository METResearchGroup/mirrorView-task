# Step 2: Run the command and write RESULTS.md

## Scope

- **Caller:** the same `run.py` `main` from Step 1.
- **Task:** Export AWS credentials, run the command, confirm the local CSV and the S3 object, copy logs to `/opt/cursor/artifacts/`, and commit `RESULTS.md` with remaining label totals overall and split by old and new.
- **Out of scope:** pytest, editing the experiment README, changing the old catalog, changing the old results file, changing the 10,000-row catalog, changing the v1 or v2 remaining-label CSVs.

## Files to inspect (read-only)

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/README.md`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/constants.py`
- `/workspace/docs/plans/2026-09-09_required_label_count_pr273_catalog_7ad7e0/plan.md`
- `/workspace/docs/plans/2026-09-09_required_label_count_pr273_catalog_7ad7e0/steps/step1.md`

## Files allowed to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/RESULTS.md` (written by the live command, then committed)
- `/workspace/CHANGELOG.md` after the live S3 object exists

## Files forbidden to change

- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/README.md`
- `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-09_required_label_count_pr273_catalog_7ad7e0/**`

## Live commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py
```

Expected stdout includes `old_posts=8899`, `old_labels=27557`, `new_posts=10000`, `new_labels=50000`, `total_posts=18899`, `total_labels=77557`, a local path under `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv`, and `csv_sha256=`.

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib
from pathlib import Path
import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

local = Path(
    "experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/"
    "required_label_count_per_stimulus_post.csv"
)
store = CampaignObjectStore("mirrorview-experimental-artifacts")
key = (
    "experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/"
    "required_label_count_per_stimulus_post.csv"
)
stored = store.get(key)
assert stored is not None
frame = pd.read_csv(local)
assert list(frame.columns) == ["id", "number_of_times_to_label", "batch"]
assert (frame["number_of_times_to_label"] > 0).all()
assert len(frame) == 18899
assert int((frame["batch"] == "old").sum()) == 8899
assert int((frame["batch"] == "new").sum()) == 10000
assert int(frame["number_of_times_to_label"].sum()) == 77557
assert int(frame.loc[frame["batch"] == "old", "number_of_times_to_label"].sum()) == 27557
assert int(frame.loc[frame["batch"] == "new", "number_of_times_to_label"].sum()) == 50000
assert hashlib.sha256(local.read_bytes()).hexdigest() == hashlib.sha256(stored.body).hexdigest()
print("required label counts ok", len(frame), int(frame["number_of_times_to_label"].sum()))
PY
```

Expected: `required label counts ok 18899 77557`.

Copy the command stdout to `/opt/cursor/artifacts/required_label_count_pr273_run.log`.

## Must pass

- Live command exits 0 on the first run.
- `old_posts=8899` and `old_labels=27557`.
- `new_posts=10000` and `new_labels=50000`.
- `total_posts=18899` and `total_labels=77557`.
- Local SHA-256 equals S3 object SHA-256.
- `RESULTS.md` is committed and records those three remaining label totals.
- New catalog object SHA-256 is still `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`.
- `README.md` is unchanged from Step 1.

## Must fail

- A second run of the same command, because `require_output_key_absent` and `put_new` must raise `FileExistsError`.
