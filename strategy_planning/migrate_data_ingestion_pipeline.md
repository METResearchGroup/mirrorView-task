# Migrate data ingestion into mirrorview-wt2

Implementation plan: `docs/plans/2026-08-06_migrate_data_ingestion_486894/`.

Copy the per-platform batch pipeline from `lab_data_integrations_interface` into this repo so a new sync and curated export can run here, then feed the existing stimuli assembly path for another data collection round.

Source: `/Users/mark/src/work/lab_data_integrations_interface/data_platform`  
Target package name: `data_ingestion/` at repo root (keep internal module name `data_platform` on first copy to avoid a bulk import rewrite, or rename in a follow-up).  
Does not include: cross-platform merge, LLM mirror generation, webapp deploy, or participant assignment.

Related runbooks already in this repo: `docs/runbooks/HISTORY_OF_STUDY.md`, `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`, `docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`.

---

## Goal for the next collection round

Run a fresh sync on Bluesky, Twitter, and Reddit, curate each platform to `mirrorview.csv`, sample and combine those exports into a stimuli catalog with mirrored text, then ship the catalog (and new assignment IDs if the post set changes) for a new study run.

---

## Current split of ownership

| Stage | Where it lives today | Output |
|---|---|---|
| API sync → preprocess → features → curate | `lab_data_integrations_interface/data_platform` | Per-platform `curated/<ts>/mirrorview.csv` + `metadata.json` |
| Sample across platforms | `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | `concatenated_records/<ts>/records.csv` |
| Generate mirrors (LLM flip) | same experiment + `truncate_posts_2026_06_19` | `generated_flips/…/flips.csv` |
| Balance / finalize | `balance_flips.py`, `jobs/mirrorview_scaled_2026_06_18/` | Deploy `flips.csv` |
| Serve to users | `webapp/` + S3 catalog + assignment Lambda | Browser shows original + mirror |

The mirrorview-wt2 tree already holds curated metadata under `experiments/scaled_mirrors_generation_2026_06_02/data/*/…/curated/`, but the `mirrorview.csv` files are not checked in. A new round cannot start from in-repo curated exports alone.

---

## Target layout after migration

```text
mirrorview-wt2/
  data_ingestion/                 # copied from lab …/data_platform (sans data/)
    ingestion/
    preprocessing/
    generate_features/
    curate/
    aws/                          # Bluesky S3/Athena path; keep but parameterize later
    orchestration/                # optional; Bluesky Prefect only
    models/
    utils/
  ml_tooling/                     # copied; LLM + Perspective helpers for features
  lib/                            # merge env keys into existing files (do not overwrite)
  experiments/scaled_mirrors_generation_2026_06_02/
    sample_data_to_mirror.py      # unchanged contract; point discovery at new curated roots
  jobs/ … webapp/ …               # unchanged until stimuli CSV is ready
```

Recommended data root after copy (same relative layout as today):

`data_ingestion/data/{bluesky|twitter|reddit}/{dataset_id}/{raw|preprocessed|features|curated}/`

Do not copy `data_platform/data/` (~236MB of local run artifacts).

---

## End-to-end user journey (next round)

### A. Ingest and curate (per platform)

1. Set API keys in repo-root `.env` (see Env vars below).
2. Edit or clone ingestion YAML under `data_ingestion/ingestion/configs/<platform>/` (new keywords / limits / `dataset_id` as needed).
3. Sync each platform (checkpointed; resume with `--run-dir` if interrupted):

```bash
PYTHONPATH=. uv run python data_ingestion/ingestion/sync_bluesky.py --config data_ingestion/ingestion/configs/bluesky/mirrorview.yaml
PYTHONPATH=. uv run python data_ingestion/ingestion/sync_twitter.py --config data_ingestion/ingestion/configs/twitter/mirrorview.yaml
PYTHONPATH=. uv run python data_ingestion/ingestion/sync_reddit.py  --config data_ingestion/ingestion/configs/reddit/mirrorview.yaml
```

4. Preprocess → features → curate for each `dataset_id` from the YAML:

```bash
PYTHONPATH=. uv run python data_ingestion/preprocessing/preprocess_<platform>.py --dataset-id <platform>_<uuid>
PYTHONPATH=. uv run python data_ingestion/generate_features/generate_<platform>_features.py --dataset-id <platform>_<uuid> --batch-size 64
PYTHONPATH=. uv run python data_ingestion/curate/curate_<platform>.py --dataset-id <platform>_<uuid> --config mirrorview.yaml
```

5. Confirm outputs:

`data_ingestion/data/<platform>/<dataset_id>/curated/<timestamp>/mirrorview.csv`  
`data_ingestion/data/<platform>/<dataset_id>/curated/<timestamp>/metadata.json`

Bluesky may also upload to `s3://lab-data-integrations-interface/…` if AWS creds and the existing bucket wiring stay enabled. Twitter and Reddit are local-disk pipelines today.

### B. Combine curated exports into study stimuli (already in this repo)

6. Make curated exports discoverable by `sample_data_to_mirror.py` (symlink, copy, or point the discovery glob at `data_ingestion/data/*/…/curated/*/metadata.json`).
7. Sample:

```bash
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
```

Writes `concatenated_records/<ts>/records.csv` (target 10k; drops unclear/neutral stance; Twitter-first per toxicity tier; remaining Bluesky/Reddit 50/50).

8. Generate flips (`generate_flips.py`), fix Reddit keys if needed, balance (`balance_flips.py`), then any truncation / regen path you reuse from `experiments/truncate_posts_2026_06_19/`.
9. Promote final catalog into a new job folder (do not overwrite `jobs/mirrorview_scaled_2026_06_18/` blindly), then follow `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md` and `SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md`.
10. Because post IDs will change for a new sync, regenerate precomputed assignments in `study_participant_assignment_interface` and update the assignment batch URI in webapp / job YAML.

---

## Request and data flow trace

```text
External APIs
  Bluesky (atproto) / Twitter (tweepy + X_BEARER_TOKEN) / Reddit (praw)
        │
        ▼  sync_<platform>.sync_records
  raw/{ts}/posts|comments + metadata.json   [Bluesky: optional S3 + Athena]
        │
        ▼  preprocess_<platform> → validators
  preprocessed/{ts}/
        │
        ▼  generate_<platform>_features → FEATURE_REGISTRY
           (OpenAI via ml_tooling/llm, Perspective via GOOGLE_API_KEY)
  features/{feature}.parquet|csv
        │
        ▼  curate: DuckDB wide join + YAML filters (curate/configs/*/mirrorview.yaml)
  curated/{ts}/mirrorview.csv + metadata.json
        │
        ▼  [hand off, first combine across platforms]
  sample_data_to_mirror.py → concatenated_records/{ts}/records.csv
        │
        ▼  generate_flips.py (Bedrock) → balance_flips.py → truncate/regen
  flips.csv (post_primary_key, original_text, mirrored_text, …)
        │
        ▼  webapp public img/ + S3 catalog; assignment Lambda returns post IDs
  Browser joins assignedPostIds → catalog rows → shows original + mirror
```

### Stage entrypoints (source paths today)

| Stage | Bluesky | Twitter | Reddit |
|---|---|---|---|
| Sync | `ingestion/sync_bluesky.py` | `ingestion/sync_twitter.py` | `ingestion/sync_reddit.py` |
| Preprocess | `preprocessing/preprocess_bluesky.py` | `…_twitter.py` | `…_reddit.py` |
| Features | `generate_features/generate_bluesky_features.py` | `…_twitter…` | `…_reddit…` |
| Curate | `curate/curate_bluesky.py` | `…_twitter.py` | `…_reddit.py` |
| Orchestrator | `orchestration/orchestrate_bluesky.py` (Prefect) | none | none |

Shared helpers: `curate/consolidate.py` (wide table), `curate/apply_rules.py` (YAML filters), `generate_features/registry.py`, `models/sync.py` (raw Pydantic schemas), `utils/dataset.py` / `utils/storage.py` (local layout).

---

## Key interfaces (contracts you must preserve)

### Curated export → sampler

`sample_data_to_mirror.normalize_mirrorview_df` expects:

| Platform | ID | Text | Toxicity | Stance |
|---|---|---|---|---|
| Reddit | `post_reddit_id` + `comment_id` (composite `unique_reddit_id`) | `body` | `toxicity_tier` or `sample_toxicity_type` | `political_stance` |
| Twitter | `tweet_id` | `text` | same | same |
| Bluesky | `uri` (hashed to `bluesky_<sha256>`) | `text` | same | same |

Curate YAML (`curate/configs/*/mirrorview.yaml`) currently keeps rows where:

- `news_or_opinion_category == opinion`
- `is_political == true`
- `is_likely_spam == false`
- `political_stance in {left, right}`
- `is_self_contained == true`
- `is_structurally_complete == true`

Feature generators that feed those columns live under `generate_features/{is_political,is_news_or_opinion,is_likely_spam,political_stance,is_self_contained,is_structurally_complete,is_toxic_tiered}/`.

### Stimuli catalog → webapp

Minimum columns on the served CSV: `post_primary_key`, `original_text`, `mirrored_text` (plus `sample_toxicity_type`, `sampled_stance` for analysis).  
ID prefixes: `twitter_<id>`, `bluesky_<sha256(uri)>`, `reddit_<post>_<comment>`.

### Identity and layout

- `dataset_id` format: `{bluesky|twitter|reddit}_<uuid>` (pinned in ingestion YAML).
- Local tree: `data_ingestion/data/{platform}/{dataset_id}/{stage}/…`
- Manifest: `dataset.json` (`format`: csv or parquet).

### Env vars to merge into `lib/load_env_vars.py`

Already in wt2: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `WANDB_API_KEY`.

Add from lab: `BLUESKY_HANDLE`, `BLUESKY_PASSWORD`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_REDIRECT_URI`, `X_BEARER_TOKEN` (and optionally `X_CONSUMER_KEY`, `X_SECRET_KEY`).

AWS uses the default credential chain (see `AGENTS.md`). Bluesky cloud constants today hardcode bucket `lab-data-integrations-interface`, region `us-east-2`.

---

## Exact copy list

### Copy as-is (rename folder to `data_ingestion/`)

```text
lab_data_integrations_interface/data_platform/
  aws/
  curate/                 # include configs/
  generate_features/
  ingestion/              # include configs/
  models/
  orchestration/          # optional for v1
  preprocessing/
  utils/
  README.md
```

Exclude: `data_platform/data/`.

### Copy new into wt2

```text
lab_data_integrations_interface/ml_tooling/     → mirrorview-wt2/ml_tooling/
lab_data_integrations_interface/tests/data_platform/  → tests/data_ingestion/ (optional but useful)
```

Optional ops doc: `lab_data_integrations_interface/docs/runbooks/HOW_TO_ADD_NEW_BATCH_DATA_JOB.md`.

### Merge, do not overwrite

| Lab file | Action in wt2 |
|---|---|
| `lib/load_env_vars.py` | Add platform API keys to `ENV_VAR_TYPES` |
| `lib/constants.py` | Keep wt2 `REPO_ROOT`; confirm path resolution still works |
| `lib/timestamp_utils.py` | Diff and align if APIs differ |
| `pyproject.toml` | Add deps: `atproto`, `tweepy`, `praw`, `duckdb`, `langdetect`, `tenacity`; add `prefect` only if you keep Bluesky orchestration |

### Do not copy

- Local `data/` artifacts
- Lab Iceberg / unrelated platform code outside `data_platform` + `ml_tooling`
- Anything from `study_participant_assignment_interface` (separate migration)

---

## Migration phases

### Phase 0: Prep

- Diff `lib/` between repos; list env keys to add.
- Decide package path: `data_ingestion/` on disk with imports still `data_platform.*` for the first land, or rename the package and rewrite imports in one shot.
- Decide whether Bluesky keeps writing to the shared `lab-data-integrations-interface` S3 bucket, or runs local-only for the next round (Twitter/Reddit are already local-only).

### Phase 1: Land code

- Copy tree + `ml_tooling/`.
- Merge env allowlist.
- Add PyPI deps; `uv sync`; smoke `PYTHONPATH=. uv run python -c "import data_platform"` (or `data_ingestion` if renamed).
- Fix Twitter/Reddit preprocess gate: `require_all_runs_uploaded` expects `s3_upload_status`, which Twitter/Reddit sync never set. Either mark local runs uploaded, or skip the gate for non-Bluesky platforms (lab already stubs this in tests).

### Phase 2: Wire curated outputs into sampler

- Point `sample_data_to_mirror.py` discovery at `data_ingestion/data/*/…/curated/*/metadata.json` (or copy/symlink curated runs into the old `experiments/.../data/` layout).
- Dry-run normalize on one small curated CSV per platform before a full sync.

### Phase 3: First real sync for the new round

- Run sync → preprocess → features → curate for all three platforms (start with a small `limit` config, then scale YAML).
- Run sample → flip → balance → finalize job CSV.
- Follow stimuli replace + new collection runbooks; regenerate assignments because IDs are new.

### Phase 4: Cleanup (later)

- Rename imports from `data_platform` → `data_ingestion` if you deferred that.
- Parameterize `aws/constants.py` (bucket / workgroup names) so this repo is not silently coupled to the lab bucket.
- Update `docs/runbooks/HISTORY_OF_STUDY.md` to say ingestion lives here.
- Optionally retire the live dependency on the external repo for Mirrorview jobs (leave lab repo for other consumers if any).

---

## Coupling and breakage risks

| Risk | Why it bites | Mitigation |
|---|---|---|
| `PYTHONPATH=.` + `from data_platform…` | Package must sit at import root | Land at repo root; keep name or rewrite imports |
| Data root = `Path(__file__).parents[1] / "data"` | Always sibling of package code | Accept `data_ingestion/data/`; do not expect configurable root in v1 |
| S3 upload gate on preprocess | Twitter/Reddit fail without `s3_upload_status` | Relax gate or set flag after local sync |
| Python 3.11 (lab) vs 3.12 (wt2) | Dep constraint mismatch | Pin/test on 3.12; watch Prefect if used |
| Hardcoded AWS bucket names | Accidental writes to lab bucket | Explicit decision before Bluesky cloud path |
| Missing `mirrorview.csv` in git | Sampler cannot rebuild historical samples | New sync, or restore CSVs from lab disk/S3 |
| Assignment IDs | New posts ⇒ new `post_primary_key` set | Regenerate assignment batch; update Lambda URI |

---

## Out of scope for this migration

- Merging three curated files into one stimuli catalog (already owned by `sample_data_to_mirror.py` / `balance_flips.py`).
- Moving `study_participant_assignment_interface`.
- Rewriting the jsPsych webapp or Lambda save path.
- Checking large raw/preprocessed/feature artifacts into git.
- Unifying Twitter/Reddit onto Prefect or S3 (nice-to-have after the next round ships).

---

## Definition of done

- [ ] `data_ingestion/` (or kept `data_platform/`) runs sync → curate for Bluesky, Twitter, and Reddit from this repo with `PYTHONPATH=. uv run …`
- [ ] Curated `mirrorview.csv` files satisfy `normalize_mirrorview_df`
- [ ] `sample_data_to_mirror.py` produces a new `records.csv` from those curated runs
- [ ] Flip / balance / job CSV path produces a deployable catalog
- [ ] Runbooks updated so the next person does not open the lab repo for Mirrorview ingestion
- [ ] Env keys and deps documented in `.env.example` or `AGENTS.md`

---

## Quick command cheat sheet (after land)

```bash
# from mirrorview-wt2 root
export PYTHONPATH=.

# per platform (example Bluesky)
uv run python data_ingestion/ingestion/sync_bluesky.py --config data_ingestion/ingestion/configs/bluesky/mirrorview.yaml
uv run python data_ingestion/preprocessing/preprocess_bluesky.py --dataset-id bluesky_<uuid>
uv run python data_ingestion/generate_features/generate_bluesky_features.py --dataset-id bluesky_<uuid> --batch-size 64
uv run python data_ingestion/curate/curate_bluesky.py --dataset-id bluesky_<uuid> --config mirrorview.yaml

# combine → stimuli (existing)
uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
# then generate_flips.py → balance_flips.py → job finalize → HOW_TO_REPLACE_STIMULI_DATASET.md
```
