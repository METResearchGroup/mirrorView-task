# Setup

The report uses live participant data from the September 2026 MirrorView run (`mirrorview_2026_09_09`).

## Data required

1. Saved jsPsych CSVs under `s3://jspsych-mirror-view-2026-09-09/data/prolific/`. Each file is one finished session. The export helper skips files whose Prolific id looks like a placeholder, a manual test, or a dev id.
2. Assignment rows in DynamoDB table `user_assignments` (region `us-east-2`) with `study_id` `mirrorview` and `study_iteration_id` `mirrorview_2026_09_09`. Party comes from the assignment payload metadata.
3. The assignment file size used as the target: 3,879 feeds, 1,940 Democrat and 1,939 Republican, 20 posts per feed, 77,580 label slots. Cell slot targets come from `experiments/generate_study_user_assignments_2026_09_08/RESULTS.md`.

Environment setup is out of scope here. AWS access uses the lab keys documented in `AGENTS.md`.

## Refresh

From the repository root:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/study_progress_dashboard_2026_09_11/run.py
```

Pass `--export-csv path/to/combined.csv` to reuse a combined export. Pass `--skip-upload` to skip writing copies to `s3://mirrorview-experimental-artifacts/experiments/study_progress_dashboard_2026_09_11/`.

## Tests

```bash
PYTHONPATH=. uv run pytest experiments/study_progress_dashboard_2026_09_11/tests -q
```

## View

The dashboard is a static file, `index.html`. On a Vercel preview for this branch it is also at `/study-progress`.
