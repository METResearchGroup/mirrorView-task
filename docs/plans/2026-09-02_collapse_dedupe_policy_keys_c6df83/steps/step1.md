# Step 1: Read one shared skip list, with optional Reddit type overrides

## Goal

Stop using two Reddit YAML names for skip lists that Bluesky and Twitter already share as `dedupe_policy`. Add `ingestion_params.dedupe_policy` as the shared list for every platform, keep `comments_dedupe_policy` and `posts_dedupe_policy` as optional Reddit overrides, drop the no-op `current_run` token from committed YAML, and keep `prior_runs_same_dataset` as the only token that loads earlier local runs.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `resolve_dedupe_policy`, reached from:

- `data_platform/ingestion/sync_bluesky.py` `run_sync_tasks`
- `data_platform/ingestion/sync_twitter.py` `run_sync_tasks`
- `data_platform/ingestion/sync_reddit.py` `_open_reddit_dedupe_sessions`

**Task:** resolve the YAML skip list, then pass it to `policy_includes_prior_runs` when building `DedupeConfig.include_prior_runs`.

**Out of scope:** Duplicate-skip counter unification (GitHub issue 111). Renaming `policy_includes_prior_runs`. Adding a `current_run` constant. Turning `current_run` into a switch that can disable within-run skip. A generic YAML alias framework. A deprecation logger. `CHANGELOG.md`. Experiment YAML under `experiments/`. Sibling GitHub issues 103 to 109 and 111 to 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Pattern: `resolve_limit_per_task` presence rules |
| `/workspace/data_platform/utils/deduplication.py` | `policy_includes_prior_runs` already ignores every token except `prior_runs_same_dataset` |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `run_sync_tasks` currently does `ingestion_params.get("dedupe_policy")` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `run_sync_tasks` currently does `ingestion_params.get("dedupe_policy")` |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `_open_reddit_dedupe_sessions` currently does `comments_dedupe_policy` and `posts_dedupe_policy` |
| `/workspace/data_platform/ingestion/configs/bluesky/*.yaml` | Shared key plus `current_run`. `smoke.yaml` lists only `current_run`. `trump_econ_iran.yaml` omits the key |
| `/workspace/data_platform/ingestion/configs/twitter/*.yaml` | Shared key plus `current_run` |
| `/workspace/data_platform/ingestion/configs/reddit/default.yaml` | Both type keys, same list |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml` | Both type keys, same list |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml` | Comments include `prior_runs_same_dataset`. Posts list only `current_run` |
| `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml` | Same split as `mirrorview_scale.yaml` |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Add resolver tests. Pattern: `TestResolveLimitPerTask` |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | `ALLOWED_DEDUPE_POLICY_TOKENS` currently includes `current_run` |
| `/workspace/tests/data_platform/utils/test_deduplication.py` | `TestPolicyIncludesPriorRuns` still uses `current_run` as a no-op token |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Leave `test_run_sync_tasks_respects_current_run_only_policy` on `["current_run"]` |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Leave `test_run_sync_tasks_does_not_skip_prior_runs_when_disabled` on `["current_run"]` |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Leave fixture-driven type keys. Add shared-key and override fetch tests |
| `/workspace/tests/data_platform/ingestion/conftest.py` | Bluesky fixture `dedupe_policy: ["current_run", PRIOR_RUN_POLICY]`. Do not change |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | Split type keys. Do not change |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/bluesky/default.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/smoke.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/default.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/default.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`
- `/workspace/tests/data_platform/utils/test_deduplication.py`

Plan package files under `/workspace/docs/plans/2026-09-02_collapse_dedupe_policy_keys_c6df83/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/utils/deduplication.py` except if a docstring must mention the shared key. Prefer leaving `policy_includes_prior_runs` unchanged.
- `/workspace/tests/data_platform/ingestion/conftest.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`
- `/workspace/tests/data_platform/ingestion/twitter_conftest.py`
- `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/**`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add module constants and helper in `sync_checkpoint.py`:

```text
DEDUPE_POLICY_KEY = "dedupe_policy"
COMMENTS_DEDUPE_POLICY_KEY = "comments_dedupe_policy"
POSTS_DEDUPE_POLICY_KEY = "posts_dedupe_policy"

def resolve_dedupe_policy(
    ingestion_params: dict[str, Any],
    override_key: str | None = None,
) -> object:
```

Behavior, matching `resolve_limit_per_task` presence rules, not a truthy `or`:

- If `override_key` is not None and that key is present (`override_key in ingestion_params`), return `ingestion_params[override_key]`. Do not fall back.
- Else return `ingestion_params.get(DEDUPE_POLICY_KEY)`.
- If neither the override nor the shared key is set, return None.
- An empty list is present. Return `[]`. Do not fall back to the shared key.
- An explicit None value on a present override key is present. Return None. Do not fall back.
- Bluesky and Twitter call `resolve_dedupe_policy(ingestion_params)` with no override, so Reddit type keys are ignored there.
- Reddit comments call `resolve_dedupe_policy(ingestion_params, COMMENTS_DEDUPE_POLICY_KEY)`.
- Reddit posts call `resolve_dedupe_policy(ingestion_params, POSTS_DEDUPE_POLICY_KEY)`.

Callers pass the resolved list into `policy_includes_prior_runs`. Do not change that function. Do not add a second helper that also returns the bool.

Do not add a platform registry, a deprecation logger, or a migration tool.

Rename committed YAML:

- Bluesky `default.yaml`, `mirrorview.yaml`, `mirrorview2.yaml`, `mirrorview_scale.yaml`: drop `current_run`. Keep `dedupe_policy: [prior_runs_same_dataset]`.
- Bluesky `smoke.yaml`: drop the `dedupe_policy` key after removing `current_run`. Do not replace it with an empty list.
- Twitter `default.yaml`, `mirrorview.yaml`, `mirrorview_scale.yaml`, `mirrorview_scale_2.yaml`, `keyword_politics_econ_7000.yaml`: drop `current_run`. Keep `dedupe_policy: [prior_runs_same_dataset]`.
- Reddit `default.yaml` and `mirrorview.yaml`: replace both type keys with `dedupe_policy: [prior_runs_same_dataset]`.
- Reddit `mirrorview_scale.yaml` and `mirrorview_scale_run_2.yaml`: set `dedupe_policy: [prior_runs_same_dataset]` and `posts_dedupe_policy: []`. Drop `comments_dedupe_policy` and drop `current_run`.

Do not add a skip list to `trump_econ_iran.yaml`.

Keep `run_sync_tasks`, `_open_reddit_dedupe_sessions`, `DedupeConfig`, and `policy_includes_prior_runs` signatures unchanged.

## Test design

Prefer calling `resolve_dedupe_policy` for key resolution. One test class for that function. Leave existing `current_run`-only fetch tests on that token so they keep proving the no-op. Add YAML assertions in the ingest YAML keys file. Add one Reddit fetch test that uses only the shared key, and one that uses an empty posts override.

```text
given ingestion_params with dedupe_policy [prior_runs_same_dataset]
when resolve_dedupe_policy(params)
then return that list

given ingestion_params with comments_dedupe_policy [prior_runs_same_dataset] and no dedupe_policy
when resolve_dedupe_policy(params, comments_dedupe_policy)
then return that list

given ingestion_params with posts_dedupe_policy [] and dedupe_policy [prior_runs_same_dataset]
when resolve_dedupe_policy(params, posts_dedupe_policy)
then return []

given ingestion_params with comments_dedupe_policy [prior_runs_same_dataset] and dedupe_policy []
when resolve_dedupe_policy(params, comments_dedupe_policy)
then return [prior_runs_same_dataset]

given ingestion_params with posts_dedupe_policy None and dedupe_policy [prior_runs_same_dataset]
when resolve_dedupe_policy(params, posts_dedupe_policy)
then return None

given ingestion_params empty
when resolve_dedupe_policy(params)
then return None

given ingestion_params with comments_dedupe_policy [prior_runs_same_dataset] only
when resolve_dedupe_policy(params)
then return None

given policy [prior_runs_same_dataset]
when policy_includes_prior_runs(policy)
then return True

given policy []
when policy_includes_prior_runs(policy)
then return False

given Reddit ingestion_params with dedupe_policy [prior_runs_same_dataset], no type keys, a prior comment on an earlier run of the same dataset
when run_sync_tasks(...)
then that comment is skipped

given Reddit ingestion_params with dedupe_policy [prior_runs_same_dataset], posts_dedupe_policy [], a prior post on an earlier run of the same dataset
when run_sync_tasks(...)
then that post is not skipped

given ingest YAML under data_platform/ingestion/configs/{bluesky,twitter,reddit}/
when each file is loaded
then no policy list contains current_run
and allowed tokens are only prior_runs_same_dataset
and bluesky and twitter files do not contain comments_dedupe_policy or posts_dedupe_policy
and reddit default.yaml and mirrorview.yaml set dedupe_policy and omit both type keys
and reddit scale files set dedupe_policy to [prior_runs_same_dataset] and posts_dedupe_policy to []
and bluesky/smoke.yaml omits dedupe_policy
```

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `resolve_dedupe_policy` as `raise NotImplementedError`, adding the three key constants, and calling the helper from Bluesky, Twitter, and Reddit. Do not put the real key preference in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add constants and `resolve_dedupe_policy` that raises `NotImplementedError`. Wire Bluesky and Twitter to `resolve_dedupe_policy(ingestion_params)`. Wire Reddit comments and posts to the matching override key. Existing fetch tests that open a dedupe session fail with `NotImplementedError` until Phase 5.
3. Phase 3 contracts. Confirm the signature returns `object` and the docstring states presence rules. Body stays a stub. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. Resolver and YAML tests must fail until Phase 5. Keep existing `current_run` fetch tests.
5. Phase 5 units, in this order, one commit each:
   1. Implement `resolve_dedupe_policy` so the override wins when present and `dedupe_policy` is the fallback. Add the extra `policy_includes_prior_runs` cases. Resolver tests, Reddit shared-key fetch, Reddit posts-override fetch, and skip-token tests pass. YAML tests stay red.
   2. Update committed ingest YAML as listed above so the YAML-key tests pass.
6. Phase 6. Run the must-pass commands. Confirm skip-counter field names, `limit_per_task`, `max_posts`, `max_comments`, and `policy_includes_prior_runs` stay unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py tests/data_platform/utils/test_deduplication.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py tests/data_platform/ingestion/test_sync_checkpoint.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures. Existing `current_run` fetch tests still collected and passing.

## Must fail / not happen

- Duplicate-skip counters unified (issue 111).
- `policy_includes_prior_runs` renamed or given a second token enum.
- Within-run skip becoming optional.
- A new generic ingest alias module or deprecation logger.
- `CHANGELOG.md` edited.
- Experiment YAML under `experiments/` edited.
- `trump_econ_iran.yaml` given a skip list.
- Sibling GitHub issues 103 to 109 and 111 to 116 implemented in this PR.
