# Init: Migrate local experiment artifacts to S3

**Date:** 2026-07-20  
**Status:** Initial proposal / work plan (not a full spec)  
**Bucket (proposed):** `mirrorview-experimental-artifacts`  
**Key convention:** preserve each artifact’s path relative to the repo root (under `experiments/`)

---

## 1. Objectives and scope

### Goal

Upload `*.csv` and `*.json` artifacts currently living under `experiments/` into a dedicated S3 bucket so large / regenerable run outputs can live remotely while local experiment code, notebooks, specs, and smaller derived assets stay in the repo (or on disk as needed).

### In scope (v1)

- **Files:** all `*.csv` and `*.json` under `experiments/**` (excluding this migration experiment’s own planning docs).
- **Source tree:** dated experiment folders already present under `experiments/` (e.g. `predict_keep_remove_2026_07_01/`, `followup_model_error_analysis_2026_07_15/`, `scaled_mirrors_generation_2026_06_02/`, …).
- **Operations:** discovery → upload → record of what was uploaded (for idempotent re-runs and audit).

### Out of scope (for now)

- Other artifact types also present under `experiments/` (`.png`, `.pkl`, `.parquet`, `.txt`, `.joblib`, `.npy`, models, etc.). These may be a follow-on pass.
- Rewriting experiment scripts to read from S3 by default (optional later; local paths can remain the primary workflow until a download helper exists).
- Deleting local copies after upload (decide after verification; do not auto-delete in v1).
- Production / study runtime buckets (repo already has separate upload tooling under `scripts/upload_to_s3/` aimed at a different release flow).

### What stays local vs remote (proposed default)

| Category | Stay local | Upload to S3 |
| --- | --- | --- |
| Experiment code, specs, notebooks, README | ✓ | — |
| Plots / images (`.png`, `.pdf`) | ✓ (v1) | later? |
| Models / binaries (`.pkl`, `.joblib`, checkpoints) | ✓ (v1) | later? |
| `*.csv` / `*.json` run outputs & metadata | optional cache after upload | ✓ |
| This migration plan / manifests | ✓ (in git) | manifests may also be uploaded for audit |

### Grounding inventory (as of 2026-07-20)

Approximate local scale under `experiments/`:

| Metric | Approx. value |
| --- | --- |
| Total `*.csv` | ~92 |
| Total `*.json` | ~147 |
| Combined csv+json | **~239 files** |
| Combined size | **~86 MB** |
| Top-level experiment folders with csv/json | 9 of ~12 dated folders |

**Heaviest folders (csv+json count):**

- `predict_keep_remove_2026_07_01/` — ~66
- `followup_model_error_analysis_2026_07_15/` — ~63
- `predict_keep_remove_2026_05_07/` — ~35
- `scaled_mirrors_generation_2026_06_02/` — ~20
- others — smaller (model error analysis, truncate posts, mirrors content, etc.)

**Typical layouts:** nested `outputs/`, `models/**/outputs/`, timestamped run dirs (`YYYY_MM_DD-HH:MM:SS`), and curated `data/{platform}/{id}/…/metadata.json`. Largest single files today are on the order of ~5–10 MB CSVs (e.g. keep/remove results, flips, confusion splits)—manageable for a straightforward upload, not a multipart/mega-dataset problem yet.

**Note:** repo `.gitignore` already ignores most `*.csv` globally, with selective re-includes for some experiment prediction CSVs. Many of these artifacts are local-only today; S3 would become the durable store.

---

## 2. Proposed S3 layout

### Bucket

- **Name:** `mirrorview-experimental-artifacts`
- **Region / account / encryption / public access:** TBD (open questions below). Default assumption: private bucket, block public access, server-side encryption on.

### Key convention

Mirror the **repo-relative path** starting at `experiments/`:

```text
s3://mirrorview-experimental-artifacts/{relative path from repo root}
```

So local:

```text
experiments/{experiment_folder}/{…}/{file}.csv|json
```

becomes:

```text
s3://mirrorview-experimental-artifacts/experiments/{experiment_folder}/{…}/{file}.csv|json
```

No flattening, no content-hash renaming in v1—path identity is the contract.

### Examples

| Local path | S3 URI |
| --- | --- |
| `experiments/followup_model_error_analysis_2026_07_15/outputs/confusion_splits/false_positives.csv` | `s3://mirrorview-experimental-artifacts/experiments/followup_model_error_analysis_2026_07_15/outputs/confusion_splits/false_positives.csv` |
| `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv` | `s3://mirrorview-experimental-artifacts/experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv` |
| `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` | `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` |
| `experiments/scaled_mirrors_generation_2026_06_02/data/reddit/reddit_…/curated/2026_06_01-13:33:24/metadata.json` | same path under the bucket prefix |

### Non-goals for layout (v1)

- No `latest/` aliases or run-id remapping.
- No separate `staging/` vs `prod/` prefixes unless we later need environments.
- Do not share this bucket’s keyspace with the existing study/release upload scripts without an explicit prefix policy.

---

## 3. High-level components

Preliminary building blocks only—details deferred to a later spec.

1. **Discovery**
   - Walk `experiments/` (or a configurable root).
   - Select files matching `*.csv` / `*.json`.
   - Optionally exclude this migration folder, `node_modules`-style noise, or paths listed in an exclude file.
   - Emit a local inventory (path, size, mtime, checksum).

2. **Upload**
   - Create bucket if missing (one-time / infra step).
   - Map each inventory row → S3 key = relative path from repo root.
   - Upload with checksum verification (e.g. compare local SHA-256 to object metadata or re-download check).
   - Idempotent: skip if remote object already matches (size + hash); otherwise overwrite or fail-closed (policy TBD).

3. **Tracking**
   - Write a **manifest** (JSON or CSV) of uploaded objects: local path, s3 uri, size, hash, upload timestamp, success/skip/fail.
   - Keep manifests under this experiment folder (and optionally upload the manifest itself).
   - Support dry-run (inventory only) and resume-from-manifest.

Reuse opportunity: patterns in `scripts/upload_to_s3/` (verify by hash, staged manifests) are relevant inspiration, but this migration should stay **experiment-scoped** under `experiments/migrate_local_artifacts_to_s3_2026_07_20/` rather than conflating with public release uploads.

---

## 4. Suggested workflow / implementation steps

1. **Confirm AWS context** — account, region, credentials, whether the bucket name is globally available.
2. **Create the bucket** — private, encryption, block public access; document who owns it.
3. **Dry-run discovery** — generate full inventory of ~239 csv/json files; review outliers / sensitive paths.
4. **Pilot upload** — one mid-size experiment folder (e.g. `followup_model_error_analysis_2026_07_15/` or `scaled_mirrors_generation_2026_06_02/`).
5. **Verify** — spot-check keys, sizes, and hashes against local files.
6. **Full upload** — remaining experiment folders; write a complete manifest.
7. **Document consume path** — short note on how to `aws s3 cp` / sync a folder back locally when needed.
8. **Decide local retention** — keep as cache, gitignore hygiene, or optional prune of large files after successful verify (separate decision).
9. **(Optional follow-on)** — thin download helper; expand to parquet/pkl/png; wire selected notebooks to prefer S3 when local miss.

---

## 5. Open questions / risks / assumptions

### Assumptions

- Artifacts are research/experiment outputs, not production participant PII dumps in these csv/json trees—but content should still be reviewed before upload (especially Reddit/Twitter/Bluesky curated metadata and model prediction CSVs).
- ~86 MB / ~239 objects is small enough that a simple sequential or lightly parallel `aws s3 cp` / boto3 upload is fine for v1.
- Path-preserving keys are desirable so humans can navigate the bucket like the repo.
- Existing study S3 usage (`scripts/upload_to_s3/`, other buckets mentioned in experiment notes) remains separate.

### Open questions

- Exact AWS account, region, and IAM principal for create/upload?
- Bucket naming conflicts / org naming conventions (name is proposed as given)?
- Versioning on the bucket? Lifecycle rules?
- Overwrite policy if local file changes after upload?
- Should we exclude tiny config JSON that is already committed to git?
- Any csv/json that must **not** leave the machine (credentials, assignment files, etc.)?
- After upload, do we update `.gitignore` / docs so new runs know S3 is the home for large outputs?

### Risks

- **Sensitive content** in social-platform or prediction artifacts uploaded to the wrong account or with overly broad IAM.
- **Path characters** — some dirs use colons in timestamps (`2026_06_17-14:50:48`); S3 keys allow `:`, but tooling/shell quoting must be careful.
- **Partial uploads** without a manifest make resume messy—tracking is required even for a “simple” script.
- **Drift** if people keep writing large csv/json only locally with no sync habit.
- **Confusion with other buckets** if docs are unclear about which bucket is for experiments vs study assets.

---

## 6. Rough file layout under this experiment

Proposed (not all created yet—only this plan exists for now):

```text
experiments/migrate_local_artifacts_to_s3_2026_07_20/
├── init_migration_work_plan.md    # this document
├── README.md                      # short how-to once tooling exists
├── inventory/                     # dry-run outputs
│   └── artifacts_inventory.json   # discovered paths, sizes, hashes
├── manifests/                     # post-upload records
│   ├── pilot_manifest.json
│   └── full_upload_manifest.json
├── scripts/                       # thin, experiment-local tooling
│   ├── discover_artifacts.py      # walk experiments/ → inventory
│   ├── upload_artifacts.py        # inventory → S3 (dry-run / apply)
│   └── verify_artifacts.py        # local vs remote hash checks
└── notes/                         # optional: decisions, AWS setup crumbs
    └── aws_setup.md
```

Keep implementation here until the approach is proven; only then consider promoting shared helpers next to `scripts/upload_to_s3/` if the same patterns are needed repo-wide.

---

## Next action

Agree on AWS account/region and sensitivity review rules, then implement **discovery + dry-run inventory** before any bucket writes.
