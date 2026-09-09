# Load study assignments

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

This command does not generate feeds. It converts the pull request 278 CSV.

Source object: `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv`
SHA-256: `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce`

Odd original user ids go to `democrat` and even original user ids go to `republican`. Original user 1 is Democrat. Original user 2 is Republican.

Expected counts are 1,940 Democrat rows and 1,939 Republican rows, 1,601 mixed feeds each, 339 leftover-left Democrat feeds, and 338 leftover-left Republican feeds.

Rewritten ids are `democrat-training_assisted-0001` through `democrat-training_assisted-1940` and `republican-training_assisted-0001` through `republican-training_assisted-1939`, sorted by original user id inside each party.

Local output layout under `experiments/load_study_assignments_2026_09_09/batch/`:

- `config.yaml`
- `democrat/training_assisted/assignments.csv`
- `republican/training_assisted/assignments.csv`
- `catalog.csv`

Catalog sources: `STUDY_PHASE_2_PART_2_STIMULI` and `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` (SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`).

## Tests

```bash
PYTHONPATH=. uv run pytest experiments/load_study_assignments_2026_09_09/tests -q
```

## Live run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
```

## Verification page

`verification.html` in this folder checks the party split, leftover-left counts, rewritten ids, and catalog coverage. It loads `verification_dataset.json` by default.
