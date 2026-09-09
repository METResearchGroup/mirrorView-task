# Load study assignments, results

## Tests

`PYTHONPATH=. uv run pytest experiments/load_study_assignments_2026_09_09/tests -q` exited 0.

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
```

## Files

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Source assignments | `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv` | `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce` |
| New catalog | `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` | `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` |
| Combined catalog | `experiments/load_study_assignments_2026_09_09/batch/catalog.csv` | `f602f0451e9fb1a64a9e978dd33474f4fe15ece5fd3191e52a47fea730b5f45e` |

## Batch

`batch_uri=s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02`

| Count | Value |
| ----- | ----: |
| Democrat rows | 1940 |
| Republican rows | 1939 |
| Catalog rows | 18899 |

Rewritten ids start at `democrat-training_assisted-0001` and `republican-training_assisted-0001`.

## Manual runs

Website: `http://jspsych-mirror-view-2026-09-09.s3-website.us-east-2.amazonaws.com/`

| Prolific id | Party | Assignment id | Saved CSV |
| ---- | ---- | ---- | ---- |
| `manual-test-2026-09-09-d` | Democrat | `democrat-training_assisted-0001` | `s3://jspsych-mirror-view-2026-09-09/data/prolific/data_1788995437466_1ddc2240-a59e-4ee0-ba04-600993309510.csv` |
| `manual-test-2026-09-09-r` | Republican | `republican-training_assisted-0001` | `s3://jspsych-mirror-view-2026-09-09/data/prolific/data_1788995464759_9b8df491-37eb-455d-a35b-5347b912b63f.csv` |

DynamoDB `user_assignments` in `us-east-2`:

- `study_id` `mirrorview`
- `iteration_user_key` `mirrorview_2026_09_09#manual-test-2026-09-09-d`
- `iteration_user_key` `mirrorview_2026_09_09#manual-test-2026-09-09-r`

CLI smoke with `dev-mirrorview_2026_09_09` and `manual-cli-2026-09-09-d` returned 20 `assigned_post_ids` and `condition` `training_assisted`. A second invoke returned the same ids.

## Dashboard

Public: [verification.html](http://jspsych-mirror-view-2026-09-09.s3-website.us-east-2.amazonaws.com/experiments/load_study_assignments_2026_09_09/verification.html)

Vercel preview: [verification.html](https://mirrorview-task-git-init-study-as-6776f2-marktorres10s-projects.vercel.app/experiments/load_study_assignments_2026_09_09/verification.html)

The dashboard loaded 3,879 feeds and 18,899 catalog posts. Conversion checks passed. First Democrat id is `democrat-training_assisted-0001` (10 left / 10 right).
