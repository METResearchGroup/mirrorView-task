# Step 4: Remove the warmup API and rewrite the stimuli runbook

## Goal

Delete `warm`, `filter_rows`, `note_appended`, and `DedupeConfig.include_prior_runs`. Rename tests that still say warm. Rewrite the stimuli runbook so skip-set load is not a pipeline stage. This PR is the last code+docs land; it does not ship a product feature of its own beyond finishing the rename.

## Caller / unit of work

**Main caller:** remaining references to `warm` / `include_prior_runs` / `filter_rows` / `note_appended` after Steps 2 and 3. After this PR those names do not exist.

**Slice:** delete compatibility API → rename tests → update `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`.

**Out of scope:** YAML `dedupe_policy` token rename; `FeatureLabelQuery`; renaming `DedupeSession` / `append_deduped_records`.

**Depends on:** Steps 2 and 3 (no remaining production callers of `warm`).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md` | Done-state and runbook target |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py` | Compatibility methods to delete |
| `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` | mermaid warm node and `_drop_already_preprocessed` prose |
| `/Users/mark/src/work/mirrorview-wt/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | mentions `append_deduped_records`; do not invent a warm stage |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/deduplication.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_deduplication.py`
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_storage.py` (only if a leftover `warm` remains)
- `/Users/mark/src/work/mirrorview-wt/tests/data_platform/ingestion/test_sync_checkpoint.py` (only if a leftover `warm` remains)
- `/Users/mark/src/work/mirrorview-wt/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_bluesky.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_twitter.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/ingestion/sync_reddit.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/preprocessing/runner.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- `/Users/mark/src/work/mirrorview-wt/backlog.md` (already lists deferred items)
- `/Users/mark/src/work/mirrorview-wt/data_platform/generate_features/**`

If ingest/preprocess/storage still call `warm`, **stop** — Steps 2/3 are not done. Do not re-migrate callers in this PR.

## Contracts to lock

`DedupeConfig` after this PR:

```text
id_column: str
filename: str | None = None
# include_prior_runs is gone
```

`DedupeSession` public methods after this PR:

```text
load_seen_ids
load_seen_ids_from_all_runs
exclude_seen_ids
add_seen_ids
```

`policy_includes_prior_runs` remains. `PRIOR_RUN_POLICIES` remains.

Runbook mermaid (Stage 2 extra details) becomes:

```text
cli → validate → gate → load skip set → load raw → drop known IDs → collapse candidates → transform → filter → save
```

Prose must say:

- Skip-set load is not a preprocess stage.
- Load all prior preprocessed IDs before creating the new run directory.
- Drop known IDs with pandas; collapse remaining IDs last-wins.
- Do not name `warm` or `_drop_already_preprocessed`.

Keep `policy_includes_prior_runs` / YAML policy discussion out of this runbook unless it already exists there.

## Test design

Rename (do not drop coverage):

- `test_session_warm_loads_current_run_only_by_default` → `test_load_seen_ids_loads_current_run_only`
- `test_session_warm_unions_prior_runs_when_enabled` → split into all-runs load + union-into-existing-seen_ids if that function still mixes two cases
- `test_session_filter_rows_skips_seen` → `test_exclude_seen_ids_skips_seen`
- `test_note_appended_updates_seen_ids` → `test_add_seen_ids_updates_seen_ids`

given no `include_prior_runs` on `DedupeConfig`
when constructing `DedupeConfig(id_column="uri", include_prior_runs=True)`
then TypeError (unexpected keyword)

Repo-wide grep after the change must not find production `warm` / `include_prior_runs` / `filter_rows` / `note_appended` except `policy_includes_prior_runs` and comments in `policy_includes_prior_runs` itself.

## Implementation notes

Delete compatibility wrappers first, then fix tests, then runbook. Do not edit `plan.md` or other step files.

Unrelated uses of the word "warm" (HF CLI, LR warmup, climate text) are out of scope — do not grep-replace those.

## Must pass

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0.

```bash
rg -n "include_prior_runs|\.warm\(|filter_rows|note_appended|_drop_already_preprocessed" data_platform tests docs/runbooks
```

Expected: matches only `policy_includes_prior_runs` (and its docstring/tests) plus possibly the word "warm" in unrelated docs. No `DedupeSession.warm`. No mermaid node named warm.

## Must fail / not happen

- Reintroducing `include_prior_runs` on `DedupeConfig`.
- Changing YAML `dedupe_policy` token strings.
- Touching `FeatureLabelQuery`.
- Rewriting `DATA_INGESTION_PIPELINE_ARCHITECTURE.md` unless a leftover `warm` reference is found there (today it has none).
