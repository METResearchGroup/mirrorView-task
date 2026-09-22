# Upsample mixed study feeds, results

## Tests

`PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q` exited 0.

## Counts

| Count | Value |
| ----- | ----: |
| Base users | 3879 |
| Mixed source | 3202 |
| Cloned feeds | 1000 |
| User count | 4879 |
| Democrat rows | 2440 |
| Republican rows | 2439 |
| Democrat leftover-left | 339 |
| Republican leftover-left | 338 |
| Assignment slots | 97580 |

Source SHA-256: `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce`

Overprovisioned object: `s3://mirrorview-experimental-artifacts/experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments_overprovisioned.csv`

CSV SHA-256: `45b5cc0736a17a9be5a10f40dd49d4ae961bc383aa16591c89a185d2eaa98dd6`

The live prefix `2026_09_09-23:06:02` was left in place. DynamoDB production counters were not reset. The lookup Lambda was not changed.

## Cutover

`PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/cutover.py` replaced the live `assignments.csv` files on prefix `precomputed_assignments/2026_09_09-23:06:02` after copying `_original` siblings. DynamoDB was not reset. The lookup Lambda was not changed.

### Pre-cutover counters

| Party | `iteration_assignment_key` | Counter |
| ----- | -------------------------- | ------: |
| Democrat | `mirrorview_2026_09_09#democrat:training_assisted` | 1242 |
| Republican | `mirrorview_2026_09_09#republican:training_assisted` | 843 |

### Pre-cutover SHA-256

| Object | SHA-256 |
| ------ | ------- |
| `config.yaml` | `948a23b557349a6125ee8f4a3ff998b8bfacb55a0182880c4e8ec3bb8ec041ad` |
| Democrat `assignments.csv` | `73c8e74883c1eb45f996a9a05801b4c5cb43e4115670ab5bf9d645d46b66b648` |
| Republican `assignments.csv` | `f4ef1cf51734e1ae4929047586cc9ec75904a9134693e43c6563507671858b99` |

### `_original` object URIs

| Object | URI |
| ------ | --- |
| Democrat backup | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/democrat/training_assisted/assignments_original.csv` |
| Republican backup | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/republican/training_assisted/assignments_original.csv` |
| Config backup | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/config_original.yaml` |

### Live object URIs

| Object | URI |
| ------ | --- |
| Democrat assignments | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/democrat/training_assisted/assignments.csv` |
| Republican assignments | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/republican/training_assisted/assignments.csv` |
| Config | `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/2026_09_09-23:06:02/config.yaml` |

### Post-cutover SHA-256 and row counts

| Object | SHA-256 | Data rows |
| ------ | ------- | --------: |
| Democrat `assignments.csv` | `9452622dc17385d4693fa0c86cf11b21af97898c9726c5b00798e4c699c76120` | 2440 |
| Republican `assignments.csv` | `2d05e9e7fddc7e2a4b572b7075cf874daea51fbb71d6c8610be2404253bc7754` | 2439 |
| `config.yaml` | `c5fe7349a032b447173edaf9e03d015b741b8fa2d686794e82f90bc459c8a515` | counts 2440 / 2439 |

Live `config.yaml` now uses `s3.prefix: precomputed_assignments/2026_09_09-23:06:02`.

### Returning-user `s3_key` check

| `iteration_user_key` | Result |
| -------------------- | ------ |
| `mirrorview_2026_09_09#manual-test-2026-09-09-d` | No DynamoDB item present in `user_assignments`. |
| `mirrorview_2026_09_09#manual-test-2026-09-09-r` | No DynamoDB item present in `user_assignments`. |

Extra assignment ids `democrat-training_assisted-1941` through `democrat-training_assisted-2440` and `republican-training_assisted-1940` through `republican-training_assisted-2439` are present in the live party CSVs.
