# Step 5: Update operator docs for in-repo ingest

## Goal

Document that Mirrorview platform ingest and curation run from this repository, including env keys, local-only Bluesky default, sync → curate commands, and the handoff into the existing sample and stimuli replace runbooks.

## Caller / unit of work

**Main caller:** a human operator preparing another data collection round, reading:

1. `docs/runbooks/HISTORY_OF_STUDY.md` (where collection logic lives)
2. `AGENTS.md` (env / secrets)
3. A new or updated ingest runbook under `docs/runbooks/`

**In scope:** Doc updates only. No production code changes unless a doc example reveals a wrong path from Steps 1–4 that must be corrected in prose.

**Out of scope:** Implementing live sync; assignment interface migration; rewriting stimuli replace runbook end-to-end beyond linking to it.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt2/docs/plans/2026-08-06_migrate_data_ingestion_486894/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt2/strategy_planning/migrate_data_ingestion_pipeline.md` | Command cheat sheet and journey |
| `/Users/mark/src/work/mirrorview-wt2/docs/runbooks/HISTORY_OF_STUDY.md` | Still points at lab repo for collection |
| `/Users/mark/src/work/mirrorview-wt2/docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md` | Downstream after sampling |
| `/Users/mark/src/work/mirrorview-wt2/docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` | Study run setup |
| `/Users/mark/src/work/mirrorview-wt2/AGENTS.md` | Secrets section |
| `/Users/mark/src/work/lab_data_integrations_interface/docs/runbooks/HOW_TO_ADD_NEW_BATCH_DATA_JOB.md` | Optional source to adapt |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt2/docs/runbooks/HISTORY_OF_STUDY.md` (replace "lives in lab repo" with in-repo `data_platform/` pointer; keep assignment-repo note as still external)
- Create `/Users/mark/src/work/mirrorview-wt2/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` (new operator runbook)
- `/Users/mark/src/work/mirrorview-wt2/AGENTS.md` (document new env keys and Bluesky S3 opt-in)
- `/Users/mark/src/work/mirrorview-wt2/data_platform/README.md` (fix commands/paths for this repo root if still lab-centric)
- `/Users/mark/src/work/mirrorview-wt2/strategy_planning/migrate_data_ingestion_pipeline.md` (one-line pointer at top to the completed plan folder, optional)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt2/data_platform/ingestion/**` (behavior)
- `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `/Users/mark/src/work/mirrorview-wt2/webapp/**`
- `/Users/mark/src/work/lab_data_integrations_interface/**`

## Required content for `HOW_TO_RUN_DATA_INGESTION.md`

Use sentence case headings. Include:

1. **Purpose:** sync → preprocess → features → curate per platform in this repo; outputs under `data_platform/data/`.
2. **Prerequisites:** `uv sync`, `PYTHONPATH=.`, `.env` keys listed (Bluesky, Reddit, X, OpenAI, Google/Perspective). AWS only if Bluesky S3 opt-in is enabled.
3. **Bluesky S3 default:** local-only unless `DATA_PLATFORM_BLUESKY_S3_UPLOAD=1`.
4. **Commands** for each platform (sync, preprocess, features, curate) matching landed paths under `data_platform/`.
5. **Handoff:** after curated `mirrorview.csv` exists for all three platforms, run `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`, then point to `HOW_TO_REPLACE_STIMULI_DATASET.md` and `SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`. Note that new post IDs require regenerating assignments in the external assignment repository.
6. **Do not commit** `data_platform/data/` run artifacts.

## `HISTORY_OF_STUDY.md` edit

Find the sentence that says data collection logic lives in the lab_data_integrations_interface repo (near the Phase 2 Part 2 scale-up notes). Replace it so ingest/curation is described as living in this repo under `data_platform/`, with a link to `HOW_TO_RUN_DATA_INGESTION.md`. Keep the note that participant assignment still lives in `study_participant_assignment_interface` until that is migrated.

## `AGENTS.md` edit

Under secrets / environment variables, add the platform API keys and `DATA_PLATFORM_BLUESKY_S3_UPLOAD`. State that ingest CLIs use `PYTHONPATH=. uv run python data_platform/...`.

## Pass / fail

| Check | Pass | Fail |
|-------|------|------|
| New runbook | Exists with commands and handoff | Missing or lab-only paths |
| HISTORY | Points here for ingest | Still says collection only lives in lab repo |
| AGENTS | Lists new env keys + Bluesky opt-in | Keys undocumented |
| Package README | Commands work from wt2 root | Still assumes lab-only layout without note |

## Out of scope reminders

- Do not perform the live multi-platform sync as part of this step.
- Do not migrate the assignment repository.
- Do not rename `data_platform/` to `data_ingestion/`.
