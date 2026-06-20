## How to replace the stimuli dataset (CSV catalog)

This runbook explains how to replace the **stimuli dataset** used by the MirrorView experiment when the browser loads posts + mirrors from a CSV catalog.

It uses the current scaled run as an example:

- **Job source-of-record**: `jobs/mirrorview_scaled_2026_06_18/flips.csv`
- **Browser fetch path (deployed)**: `public/main.js` → `STUDY_SPEC.postCatalogPath` = `img/flips_scaled_2026_06_18.csv`
- **Upload allowlist / critical keys**: `scripts/upload_to_s3/constants.py` includes `img/flips_scaled_2026_06_18.csv`

### Key concept: assignments vs stimuli are separate

- The **assignment** Lambda returns `assignedPostIds` (post IDs), but it does **not** provide the mirror text.
- The **browser** loads the CSV catalog (stimuli) and then maps `assignedPostIds` → rows in that CSV by `post_primary_key`.

So:

- If you keep the **same post IDs**, you can swap the dataset by updating the CSV only.
- If you change **post IDs**, you must also regenerate precomputed assignments and update the assignment wiring.

---

## Preconditions

- You know which stimulus catalog file the deployed study is fetching:
  - Check `public/main.js`:
    - `STUDY_SPEC.postCatalogPath` (where the browser fetches the CSV)
    - `STUDY_SPEC.postIdField` (ID column, typically `post_primary_key`)
    - `STUDY_SPEC.mirrorTextField` (mirror text column, typically `mirrored_text`)
- Your new catalog CSV contains the expected columns (at minimum):
  - `post_primary_key`
  - `original_text`
  - `mirrored_text`
  - plus any columns you use downstream (e.g. `sample_toxicity_type`, `sampled_stance`)

---

## Step 1 — Decide whether IDs are unchanged

### If IDs are unchanged (common case)

You only need to replace the catalog CSV that gets uploaded under `public/` (or repo-root fallback; see below).

### If IDs changed (or you added/removed rows)

You must also regenerate assignments, because the assignment Lambda can return IDs that won’t exist in the catalog.

Where to look:

- `lambda-get-post-assignments.mjs` hardcodes which assignment batch URI to use (see `resolveAssignmentBatchUri()` and `SCALED_BATCH_URI`).
- The external assignment service repository (`study_participant_assignment_interface`) produces the precomputed assignment rows in S3.

When you change post IDs:

- Regenerate the precomputed assignments for the new ID set.
- Upload the new precomputed assignments to S3 under a new batch prefix.
- Update:
  - `lambda-get-post-assignments.mjs` to point to the new `SCALED_BATCH_URI` (or equivalent)
  - `jobs/config/<job>.yaml` → `assignment.batch_uri` (documentation / source of truth)

---

## Step 2 — Put the new catalog in the deployable location

The deploy pipeline uploads files from `public/` (and also supports repo-root fallbacks for allowlisted paths).

For the scaled run, the deployed key must be:

- `img/flips_scaled_2026_06_18.csv`

### Preferred: place under `public/`

Copy your source-of-record into the deployed path:

```bash
mkdir -p public/img
cp jobs/mirrorview_scaled_2026_06_18/flips.csv public/img/flips_scaled_2026_06_18.csv
```

### Alternate: repo-root fallback (advanced)

The staging script resolves allowlisted files from either:

- `public/<relpath>` **or**
- `<relpath>` at repo root

So you may also place it at:

- `img/flips_scaled_2026_06_18.csv`

This is mainly useful if you intentionally keep stimuli out of `public/` in git, but still want the upload tooling to pick it up.

---

## Step 3 — Verification (before uploading)

### 3A. Schema + ID sanity checks (recommended)

Validate:

- Required columns exist
- `post_primary_key` is unique (or at least the assignment set maps unambiguously)
- No empty `original_text` / `mirrored_text`

Example (run from repo root):

```bash
PYTHONPATH=. uv run python -c "import pandas as pd; df=pd.read_csv('public/img/flips_scaled_2026_06_18.csv'); req=['post_primary_key','original_text','mirrored_text']; missing=[c for c in req if c not in df.columns]; assert not missing, missing; print('rows', len(df), 'unique_ids', df['post_primary_key'].astype(str).nunique()); print('empty_original', (df['original_text'].fillna('').astype(str).str.strip()=='').sum()); print('empty_mirror', (df['mirrored_text'].fillna('').astype(str).str.strip()=='').sum())"
```

If the IDs are unchanged, also spot-check that the **number of unique IDs** matches the old dataset (if you have it).

### 3B. Content-level verification (optional but useful)

For the scaled run, there is a built-in check that compares average character lengths across dataset versions:

```bash
PYTHONPATH=. uv run python jobs/mirrorview_scaled_2026_06_18/compare_avg_char_lengths.py
```

### 3C. Assignment compatibility check (only if you changed IDs)

If you changed IDs, you must verify the assignment system is producing IDs that exist in the new catalog.

At minimum:

- Check that the assignment batch (S3) was regenerated for the new ID set.
- Confirm `lambda-get-post-assignments.mjs` is pointing at the new batch URI.

---

## Step 4 — Upload + verify in S3

From repo root:

```bash
bash scripts/upload_to_s3/run_upload.sh
```

This will:

- stage allowlisted files (including `img/flips_scaled_2026_06_18.csv`)
- upload them to the configured bucket
- verify critical keys exist in S3 post-upload

---

## Step 5 — End-to-end verification (after uploading)

### 5A. S3 object sanity check

Verify the object exists and was recently updated:

```bash
aws s3api head-object --bucket jspsych-mirror-view-4 --key img/flips_scaled_2026_06_18.csv --region us-east-2
```

Verify the S3 object content matches your local file (recommended):

```bash
bash scripts/upload_to_s3/verify_s3_object_matches_local.sh \
  --bucket jspsych-mirror-view-4 \
  --key img/flips_scaled_2026_06_18.csv \
  --local public/img/flips_scaled_2026_06_18.csv \
  --region us-east-2
```

### 5B. Browser smoke test

Open the deployed site (S3 website endpoint) and complete:

- consent
- party selection
- assignment fetch (should not error)
- confirm you see mirror text that matches the new dataset

If you see an “unknown post IDs” / assignment error in the browser, it almost always means:

- assignments were generated for IDs not present in the catalog, or
- the catalog dropped rows due to missing `original_text` / `mirrored_text`, or
- you changed `postIdField` / column names without updating `STUDY_SPEC`.

