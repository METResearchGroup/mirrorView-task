# Step 8: Collapse ingest dedupe policy keys and drop the unused current-run token

## Goal

Bluesky and Twitter use `dedupe_policy`; Reddit uses `comments_dedupe_policy` and `posts_dedupe_policy`. All committed YAML lists `current_run`, but within-run dedupe is always on via `DedupeSession.warm` → `load_seen_ids` — only `prior_runs_same_dataset` toggles cross-run loading. This PR unifies the YAML shape, drops the no-op `current_run` token, and keeps Reddit per-type overrides optional.

## Caller / unit of work

**Main callers:** `sync_bluesky.run_sync_tasks`, `sync_twitter.run_sync_tasks`, `sync_reddit._open_reddit_dedupe_sessions` (via `policy_includes_prior_runs` on resolved policy lists).

**Slice:** resolve `dedupe_policy` (+ optional Reddit per-record-type override and aliases) → `policy_includes_prior_runs` → existing `DedupeSession.warm` behavior unchanged for valid configs.

**Out of scope:** skip-counter key names (step 9), `DedupeSession` method renames, experiments YAML outside `data_platform/ingestion/configs/`.

## Decision (locked)

- Canonical YAML: `dedupe_policy: list[str]` on all platforms.
- Optional Reddit override: `dedupe_policy_by_record_type: { "reddit.post": [...], "reddit.comment": [...] }`. When a record type is missing from the map, use top-level `dedupe_policy`.
- Keep aliases `comments_dedupe_policy` / `posts_dedupe_policy` this PR: if present without the new override map, map them to `reddit.comment` / `reddit.post` and emit `DeprecationWarning`. If both an old alias and the new override map entry for the same record type are set and the lists differ → `ValueError`.
- `current_run` is **not** a policy switch. Within-run dedupe always happens via `DedupeSession.warm` → `load_seen_ids`. Remove `current_run` from documented/allowed policy tokens.
- Code only honors `prior_runs_same_dataset` (`PRIOR_RUN_POLICY` in `data_platform/utils/deduplication.py`). `policy_includes_prior_runs` stays; it ignores unknown tokens (including leftover `current_run`) and returns True only when `PRIOR_RUN_POLICY` is in the list.
- `test_ingest_yaml_keys.py` `ALLOWED_DEDUPE_POLICY_TOKENS` becomes only `{PRIOR_RUN_POLICY}`. Committed YAML must not list `current_run`.
- Update all committed ingest YAML under `data_platform/ingestion/configs/` to drop `current_run` and use `dedupe_policy`. Reddit: one shared list today (posts and comments policies match), so replace `comments_dedupe_policy` / `posts_dedupe_policy` with a single `dedupe_policy` — no `dedupe_policy_by_record_type` map unless a file truly needs differing lists.
- Configs that today include `prior_runs_same_dataset` keep that token after removing `current_run` (e.g. `[prior_runs_same_dataset]`). Configs that were `current_run`-only become `dedupe_policy: []` or omit the key.
- Independently shippable one PR.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 8 |
| `data_platform/utils/deduplication.py` | `PRIOR_RUN_POLICY`, `policy_includes_prior_runs`, `DedupeSession.warm` |
| `data_platform/ingestion/sync_bluesky.py` | `ingestion_params.get("dedupe_policy")` |
| `data_platform/ingestion/sync_twitter.py` | same |
| `data_platform/ingestion/sync_reddit.py` | `_open_reddit_dedupe_sessions`, per-type policy keys |
| `data_platform/ingestion/sync_checkpoint.py` | shared resolver home (pattern from step 6 `resolve_limit_per_task`) |
| `data_platform/ingestion/configs/**/*.yaml` | `current_run`, split Reddit keys |
| `tests/data_platform/ingestion/test_ingest_yaml_keys.py` | `ALLOWED_DEDUPE_POLICY_TOKENS`, `DEDUPE_POLICY_KEYS` |
| `tests/data_platform/utils/test_deduplication.py` | `TestPolicyIncludesPriorRuns`, `current_run` fixtures |
| `tests/data_platform/ingestion/test_sync_*_checkpoint.py` | `test_run_sync_tasks_respects_current_run_only_policy` |
| `tests/data_platform/ingestion/conftest.py`, `reddit_conftest.py` | default policy fixtures |

## Files allowed to change

- `data_platform/utils/deduplication.py` (docstrings; `policy_includes_prior_runs` ignores unknown tokens)
- `data_platform/ingestion/sync_checkpoint.py` (shared `resolve_dedupe_policy` helper)
- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/ingestion/configs/**/*.yaml` (dedupe keys/tokens only)
- `tests/data_platform/ingestion/test_ingest_yaml_keys.py`
- `tests/data_platform/utils/test_deduplication.py`
- `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `tests/data_platform/ingestion/conftest.py`
- `tests/data_platform/ingestion/reddit_conftest.py`
- `tests/data_platform/ingestion/test_sync_checkpoint.py` (resolver unit tests, if added there)
- `CHANGELOG.md`

## Files forbidden to change

- Preprocess / features / curate / stimuli
- `experiments/**` YAML (outside committed ingest configs)
- Skip-counter metadata field names (step 9)
- `DedupeSession` public method names

## Contracts

```text
PRIOR_RUN_POLICY: str = "prior_runs_same_dataset"

policy_includes_prior_runs(policy: object) -> bool
  Non-lists → False.
  True iff PRIOR_RUN_POLICY in policy list.
  Ignore all other tokens (including "current_run", "unknown_policy").

resolve_dedupe_policy(
    ingestion_params: dict[str, Any],
    *,
    record_type: str | None = None,
) -> list[str]
  Canonical top-level key "dedupe_policy" (default [] when absent).
  When record_type is set (Reddit only):
    - If dedupe_policy_by_record_type has record_type → use that list.
    - Else if record_type-specific alias present:
        "reddit.comment" → comments_dedupe_policy
        "reddit.post" → posts_dedupe_policy
      DeprecationWarning when alias used without override map.
    - Else → top-level dedupe_policy.
  Raise ValueError if alias and override map both set for same record_type and lists differ.
  Raise ValueError if record_type not in {"reddit.comment", "reddit.post", None}.
```

Bluesky/Twitter call sites:

```text
include_prior_runs = policy_includes_prior_runs(
    resolve_dedupe_policy(ingestion_params)
)
```

Reddit `_open_reddit_dedupe_sessions`:

```text
comments: resolve_dedupe_policy(ingestion_params, record_type="reddit.comment")
posts:    resolve_dedupe_policy(ingestion_params, record_type="reddit.post")
```

Within-run dedupe: unchanged — every session still calls `warm(storage, output_dir)` which always runs `load_seen_ids` for the current run directory.

## Tests (write first)

`TestResolveDedupePolicy` in `tests/data_platform/ingestion/test_sync_checkpoint.py` (or `tests/data_platform/utils/test_deduplication.py`):

- given top-level `dedupe_policy: [PRIOR_RUN_POLICY]`, when `record_type` is None, then returns that list.
- given `dedupe_policy: []`, then `policy_includes_prior_runs` is False; `warm` still loads current-run ids (existing `test_session_warm_loads_current_run_only_by_default` behavior).
- given Reddit alias `comments_dedupe_policy` without override map, then resolves for `reddit.comment` and warns.
- given `dedupe_policy_by_record_type` and matching alias, then no error.
- given override map and alias with different lists, then `ValueError`.

Update `TestPolicyIncludesPriorRuns`:

- `["current_run"]` → False (unchanged outcome; documents ignored token).
- `[PRIOR_RUN_POLICY]` → True (drop `current_run` from the combined case).
- `["current_run", "unknown_policy"]` → False.

Rename or repurpose `test_run_sync_tasks_respects_current_run_only_policy` in each platform checkpoint file:

- set `dedupe_policy: []` (or omit `prior_runs_same_dataset`) instead of `["current_run"]`.
- assert ids from another dataset's prior run are **not** skipped, but within-run dedupe still works.

`test_ingest_yaml_keys.py`:

- `ALLOWED_DEDUPE_POLICY_TOKENS = frozenset({PRIOR_RUN_POLICY})`.
- extend validation to walk `dedupe_policy_by_record_type` values.
- add assertion that committed YAML does not use `comments_dedupe_policy` / `posts_dedupe_policy` (migrate to canonical keys).

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py tests/data_platform/utils/test_deduplication.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0. No new failures.

## Must not happen

- Treating `current_run` as a YAML switch (no branch on that token).
- Removing within-run dedupe (`warm` must still call `load_seen_ids` every time).
- Breaking alias support for `comments_dedupe_policy` / `posts_dedupe_policy` in this PR.
- Changing skip-counter metadata field names (step 9).
- Editing `experiments/data_ingestion_smoke_2026_08_28/smoke.yaml` in this PR.
