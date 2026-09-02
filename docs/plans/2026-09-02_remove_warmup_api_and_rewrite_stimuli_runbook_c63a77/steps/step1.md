# Step 1: Delete leftover skip-set names, fix tests, and rewrite the stimuli runbook

## Goal

Delete `warm`, `filter_rows`, `note_appended`, and `DedupeConfig.include_prior_runs`. Rename tests that still say warm. Land and rewrite `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` so skip-set load is not a mermaid node or named preprocess stage. Keep `policy_includes_prior_runs` and `PRIOR_RUN_POLICIES`.

## Caller / unit of work

**Main caller:** remaining references to `warm` / `include_prior_runs` / `filter_rows` / `note_appended` after GitHub issues #69 and #70. After this PR those names do not exist on `DedupeSession` or `DedupeConfig`.

**Slice:** delete compatibility wrappers → fix tests → rewrite the stimuli runbook Stage 2 extra details.

**Out of scope:** YAML `dedupe_policy` token rename; `FeatureLabelQuery`; renaming `DedupeSession` / `append_deduped_records`; ingest `sync_*.py`; `preprocessing/runner.py` and `preprocess_*.py`; `storage.py`; filling empty Stage 1 / Stage 3 / Stage 4 headings in the stimuli runbook; rewriting `DATA_INGESTION_PIPELINE_ARCHITECTURE.md` unless a leftover `warm` reference is found there (today it has none). Sibling GitHub issues #68, #69, and #70. Do not edit `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/**`, `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`, `/workspace/docs/plans/2026-09-02_switch_ingest_to_explicit_skip_set_loads_a74c89/**`, or `/workspace/docs/plans/2026-09-02_switch_preprocess_to_skip_then_collapse_d2084b/**`.

**Depends on:** GitHub issues #69 and #70 already on this stack branch. Production ingest, preprocess, and storage must not call `warm`. If any of those files still call `warm`, stop. Do not re-migrate callers in this PR.

**Runbook source:** `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` is not on this branch. The draft lives on `origin/add-how-to-get-stimuli-runbook`. Copy that file onto this branch, then rewrite only the Stage 2 extra-details mermaid and the matching prose. When the draft names `PlatformIdBinding` / `binding`, write `PlatformSpecificColumns` / `columns` so the runbook matches this branch. Do not fill Stage 1, Stage 3, or Stage 4. Drop the trailing draft note about Reddit sources at the end of the file.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/plan.md` | Done-state and runbook target (do not edit) |
| `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/steps/step4.md` | Source contracts for this slice (do not edit) |
| `/workspace/data_platform/utils/deduplication.py` | Compatibility methods to delete |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Confirm no `.warm(` caller. Stop if one remains. |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Confirm no `.warm(` caller. Stop if one remains. |
| `/workspace/data_platform/ingestion/sync_reddit.py` | Confirm no `.warm(` caller. Stop if one remains. |
| `/workspace/data_platform/preprocessing/runner.py` | Confirm no `.warm(` caller. Stop if one remains. |
| `/workspace/data_platform/utils/storage.py` | Confirm no `.warm(` caller. Stop if one remains. |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Mentions `append_deduped_records`. Do not invent a warm stage. |
| `origin/add-how-to-get-stimuli-runbook:docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` | Draft mermaid warm node and `_drop_already_preprocessed` prose |

## Files allowed to change

- `/workspace/data_platform/utils/deduplication.py`
- `/workspace/tests/data_platform/utils/test_deduplication.py`
- `/workspace/tests/data_platform/utils/test_storage.py` (only if a leftover `warm` remains)
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` (only if a leftover `warm` remains)
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`

Plan package files under `/workspace/docs/plans/2026-09-02_remove_warmup_api_and_rewrite_stimuli_runbook_c63a77/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py`
- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/data_platform/preprocessing/preprocess_reddit.py`
- `/workspace/data_platform/utils/storage.py`
- `/workspace/backlog.md`
- `/workspace/data_platform/generate_features/**`
- `/workspace/docs/plans/2026-09-01_incremental_identity_skip_124df6/**`
- `/workspace/docs/plans/2026-09-02_explicit_skip_set_load_helpers_c4e91a/**`
- `/workspace/docs/plans/2026-09-02_switch_ingest_to_explicit_skip_set_loads_a74c89/**`
- `/workspace/docs/plans/2026-09-02_switch_preprocess_to_skip_then_collapse_d2084b/**`

Unrelated uses of the word "warm" (HF CLI, LR warmup, climate text) are out of scope. Do not grep-replace those.

## Contracts to lock

`DedupeConfig` after this PR:

```text
id_column: str
filename: str | None = None
# include_prior_runs is gone
```

Constructing `DedupeConfig(id_column="uri", include_prior_runs=True)` raises TypeError (unexpected keyword).

`DedupeSession` public methods after this PR:

```text
load_seen_ids
load_seen_ids_from_all_runs
exclude_seen_ids
add_seen_ids
```

Keep existing attributes `config` and `seen_ids`. `policy_includes_prior_runs` remains. `PRIOR_RUN_POLICIES` remains.

Runbook mermaid (Stage 2 extra details) becomes:

```text
cli → validate → gate → load skip set → load raw → drop known IDs → collapse candidates → transform → filter → save
```

Prose must say:

- Skip-set load is not a preprocess stage.
- Load all prior preprocessed IDs before creating the new run directory.
- Drop known IDs with pandas. Collapse remaining IDs last-wins.
- Do not name `warm` or `_drop_already_preprocessed`.

Keep `policy_includes_prior_runs` / YAML policy discussion out of this runbook unless it already exists there (it does not).

## Test design

Rename (do not drop coverage). `#68` already added explicit-method tests. After deleting wrappers:

- `test_session_warm_loads_current_run_only_by_default` is covered by `test_load_seen_ids_unions_current_run_only`. Rename that existing test to `test_load_seen_ids_loads_current_run_only` if you keep one. Do not keep two copies.
- `test_session_warm_unions_prior_runs_when_enabled` mixed two cases. Those cases already exist as `test_load_seen_ids_from_all_runs_does_not_call_disk` and `test_load_seen_ids_unions_into_existing_seen_ids`. Delete the warm test. Do not add a third copy.
- `test_session_filter_rows_skips_seen` is covered by `test_exclude_seen_ids_skips_seen`. Delete the filter_rows test.
- `test_note_appended_updates_seen_ids` is covered by `test_add_seen_ids_updates_seen_ids`. Delete the note_appended test.

given no `include_prior_runs` on `DedupeConfig`
when constructing `DedupeConfig(id_column="uri", include_prior_runs=True)`
then TypeError (unexpected keyword)

Name that test `test_dedupe_config_rejects_include_prior_runs`.

Keep `test_policy_includes_prior_runs` green.

Repo-wide grep after the change must not find production `warm` / `include_prior_runs` / `filter_rows` / `note_appended` except `policy_includes_prior_runs` and comments in `policy_includes_prior_runs` itself.

## Implementation notes (implement-from-spec)

Files already exist except the stimuli runbook. There are no new Python modules. Phase 2 scaffold and Phase 3 contracts do not add files or stub existing callers, because stubbing `DedupeSession` would break current tests before the deletion. If a phase does not change the repo, skip that commit. Full auto. Do not wait for Phase 3 approval.

Flesh order (delete compatibility wrappers first, then fix tests, then runbook). One Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. Grep ingest, preprocess, and storage for `.warm(`. If any production caller remains, stop. No product-code commit if nothing on disk changes.
2. Phase 4 test design. Add `test_dedupe_config_rejects_include_prior_runs`. Do not delete wrappers in this commit. The TypeError test must fail because `include_prior_runs` is still accepted.
3. Phase 5 units, in this order, one commit each:
   1. Delete `warm`, `filter_rows`, `note_appended`, and `DedupeConfig.include_prior_runs` from `/workspace/data_platform/utils/deduplication.py`. Do not add replacement wrappers.
   2. Remove tests that still call `warm`, `filter_rows`, or `note_appended`. Rename `test_load_seen_ids_unions_current_run_only` to `test_load_seen_ids_loads_current_run_only` if that name is not already present. Keep `test_policy_includes_prior_runs`. The TypeError test must now pass.
   3. Copy the stimuli runbook from `origin/add-how-to-get-stimuli-runbook`, then rewrite Stage 2 extra details to the mermaid and prose contracts above. Use `PlatformSpecificColumns` / `columns` where the draft says `PlatformIdBinding` / `binding`. Do not name `warm` or `_drop_already_preprocessed`. Do not fill Stage 1, Stage 3, or Stage 4.
4. Phase 6. Run the must-pass commands.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0.

```bash
rg -n "include_prior_runs|\.warm\(|filter_rows|note_appended|_drop_already_preprocessed" data_platform tests docs/runbooks
```

Expected: matches only `policy_includes_prior_runs` (and its docstring/tests). No `DedupeSession.warm`. No mermaid node named warm. Unrelated uses of the word "warm" outside this grep are out of scope.

## Must fail / not happen

- Reintroducing `include_prior_runs` on `DedupeConfig`.
- Changing YAML `dedupe_policy` token strings.
- Touching `FeatureLabelQuery`.
- Rewriting `DATA_INGESTION_PIPELINE_ARCHITECTURE.md` unless a leftover `warm` reference is found there.
- Editing ingest, preprocess, or storage files in this layer.
- Filling empty Stage 1 / Stage 3 / Stage 4 headings in the stimuli runbook.
