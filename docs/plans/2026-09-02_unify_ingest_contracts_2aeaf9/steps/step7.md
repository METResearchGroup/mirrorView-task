# Step 7: Split global ingest row caps by posts versus comments

## Goal

One YAML key `max_rows` names a global run cap for Bluesky/Twitter posts and Reddit comments, but the unit differs by platform. This PR introduces explicit canonical keys (`max_posts`, `max_comments`), keeps `max_rows` as a deprecated alias with platform-specific meaning, and renames checkpoint helpers so “row cap” is not confused with Reddit `post_row_count`.

## Caller / unit of work

**Main callers:** `run_sync_tasks` in `sync_bluesky.py`, `sync_twitter.py`, `sync_reddit.py`; shared stop logic in `sync_checkpoint.py` (`run_checkpointed_sync`, `stop_at_max_rows`).

**Slice:** resolve global run cap from YAML → pass cap into checkpoint loop and per-task remaining budget → committed configs use canonical keys.

**Out of scope:** per-task fetch caps (`limit_per_task`, step 6). Preprocess, features, curate. Changing what `metadata["row_count"]` counts (still deduped primary output rows: posts for Bluesky/Twitter, comments for Reddit).

## Decision (locked)

- Bluesky/Twitter canonical YAML key: `max_posts`.
- Reddit canonical YAML key: `max_comments` (still compared to `metadata["row_count"]`, which is comment count, **not** `post_row_count`).
- Deprecated alias on all three platforms: `max_rows`. Bluesky/Twitter: means `max_posts`. Reddit: means `max_comments`.
- If canonical and alias both set and unequal → `ValueError`. If equal, use it and emit `DeprecationWarning` when the alias is present.
- Shared helper in `data_platform/ingestion/sync_checkpoint.py`: `parse_run_row_cap(ingestion_params, *, canonical_key: str) -> int | None`.
- Rename `stop_at_max_rows` → `stop_at_run_row_cap`; update all callers. Rename `run_checkpointed_sync(..., max_rows_int=...)` kwarg to `run_row_cap_int`.
- `parse_max_rows` is only referenced from ingest sync modules and `test_sync_checkpoint.py` (grep the repo). **Delete** `parse_max_rows`; do not leave a wrapper.
- Update committed YAML: Bluesky/Twitter `max_rows` → `max_posts`; Reddit `max_rows` → `max_comments`. Files without a cap stay uncapped.
- Bluesky `fetch_posts_for_keyword(..., max_rows=remaining)` parameter renames to `max_posts` (remaining post budget for one task, same semantics).
- Twitter `_remaining_row_budget` renames to `_remaining_run_row_cap` (or equivalent); it still subtracts `metadata["row_count"]` from the resolved cap. If step 6 landed, `_effective_limit_per_task` still mins with this remaining budget.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 7 |
| `data_platform/ingestion/sync_checkpoint.py` | `parse_max_rows`, `stop_at_max_rows`, `run_checkpointed_sync` |
| `data_platform/ingestion/sync_bluesky.py` | `parse_max_rows`, `fetch_posts_for_keyword(max_rows=...)`, `run_sync_tasks` remaining budget |
| `data_platform/ingestion/sync_twitter.py` | `parse_max_rows`, `_remaining_row_budget`, `run_sync_tasks` |
| `data_platform/ingestion/sync_reddit.py` | `parse_max_rows`, `metadata["row_count"]` vs `post_row_count` |
| `data_platform/ingestion/configs/bluesky/default.yaml` | `max_rows: 200` |
| `data_platform/ingestion/configs/bluesky/smoke.yaml` | `max_rows: 100` |
| `data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml` | `max_rows: 20000` |
| `data_platform/ingestion/configs/twitter/default.yaml` | `max_rows: 50` |
| `data_platform/ingestion/configs/twitter/mirrorview.yaml` | `max_rows: 1000` |
| `data_platform/ingestion/configs/twitter/mirrorview_scale.yaml` | `max_rows: 10000` |
| `data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml` | `max_rows: 15000` |
| `data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml` | `max_rows: 10000` |
| `data_platform/ingestion/configs/reddit/default.yaml` | `max_rows: 100` |
| `tests/data_platform/ingestion/test_sync_checkpoint.py` | `test_parse_max_rows_*`, `test_stop_at_max_rows_*` |
| `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | `test_run_sync_tasks_caps_fetch_by_remaining_max_rows` |

## Files allowed to change

- `data_platform/ingestion/sync_checkpoint.py`
- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/ingestion/configs/bluesky/default.yaml`
- `data_platform/ingestion/configs/bluesky/smoke.yaml`
- `data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml`
- `data_platform/ingestion/configs/twitter/default.yaml`
- `data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `data_platform/ingestion/configs/twitter/mirrorview_scale.yaml`
- `data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml`
- `data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml`
- `data_platform/ingestion/configs/reddit/default.yaml`
- `tests/data_platform/ingestion/test_sync_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `tests/data_platform/ingestion/conftest.py` and `reddit_conftest.py` / `twitter_conftest.py` as needed for fixture cap keys
- `CHANGELOG.md`

## Files forbidden to change

- Preprocess (`data_platform/preprocessing/**`)
- Features / curate / stimuli
- `data_platform/models/**`
- Ingest YAML files that have no global cap (leave uncapped): `data_platform/ingestion/configs/bluesky/mirrorview.yaml`, `mirrorview2.yaml`, `trump_econ_iran.yaml`; `data_platform/ingestion/configs/reddit/mirrorview.yaml`, `mirrorview_scale.yaml`, `mirrorview_scale_run_2.yaml`
- Per-task limit keys and resolution (`limit`, `limit_per_keyword`, `limit_per_subreddit`, `limit_per_task` — step 6)

## Contracts

```text
DEPRECATED_RUN_ROW_CAP_ALIAS: str = "max_rows"

parse_run_row_cap(
    ingestion_params: dict[str, Any],
    *,
    canonical_key: str,
) -> int | None
  canonical = ingestion_params.get(canonical_key)
  alias = ingestion_params.get(DEPRECATED_RUN_ROW_CAP_ALIAS)
  If canonical is not None and alias is not None and int(canonical) != int(alias):
      raise ValueError (message names both keys and the conflict)
  If canonical is not None:
      if alias is not None: warnings.warn(DeprecationWarning) for max_rows
      return int(canonical)
  If alias is not None:
      warnings.warn(DeprecationWarning) for max_rows
      return int(alias)
  return None

stop_at_run_row_cap(
    metadata, storage, output_dir, run_row_cap_int: int | None,
) -> bool
  Same behavior as stop_at_max_rows today:
  if run_row_cap_int is None or metadata["row_count"] < run_row_cap_int: return False
  else mark remaining tasks skipped, flush metadata, return True

run_checkpointed_sync(..., run_row_cap_int: int | None, ...)
  Calls stop_at_run_row_cap before and after each process_task (unchanged control flow).
```

Platform wiring:

- Bluesky: `parse_run_row_cap(ingestion_params, canonical_key="max_posts")`.
- Twitter: `parse_run_row_cap(ingestion_params, canonical_key="max_posts")`.
- Reddit: `parse_run_row_cap(ingestion_params, canonical_key="max_comments")`; cap still gates on `metadata["row_count"]` (comments), never `post_row_count`.

Committed YAML after this PR (numeric values unchanged, keys only):

| File | Old | New |
|------|-----|-----|
| `configs/bluesky/default.yaml` | `max_rows: 200` | `max_posts: 200` |
| `configs/bluesky/smoke.yaml` | `max_rows: 100` | `max_posts: 100` |
| `configs/bluesky/mirrorview_scale.yaml` | `max_rows: 20000` | `max_posts: 20000` |
| `configs/twitter/default.yaml` | `max_rows: 50` | `max_posts: 50` |
| `configs/twitter/mirrorview.yaml` | `max_rows: 1000` | `max_posts: 1000` |
| `configs/twitter/mirrorview_scale.yaml` | `max_rows: 10000` | `max_posts: 10000` |
| `configs/twitter/mirrorview_scale_2.yaml` | `max_rows: 15000` | `max_posts: 15000` |
| `configs/twitter/keyword_politics_econ_7000.yaml` | `max_rows: 10000` | `max_posts: 10000` |
| `configs/reddit/default.yaml` | `max_rows: 100` | `max_comments: 100` |

## Tests (write first)

`TestParseRunRowCap` in `tests/data_platform/ingestion/test_sync_checkpoint.py` (replace `TestParseMaxRows` / `test_parse_max_rows_*`):

- given `{}`, then returns `None`.
- given `{"max_posts": 100}` with `canonical_key="max_posts"`, then `100`.
- given `{"max_comments": 50}` with `canonical_key="max_comments"`, then `50`.
- given only `{"max_rows": 100}` and `canonical_key="max_posts"`, then `100` and `pytest.warns(DeprecationWarning)`.
- given `{"max_posts": 100, "max_rows": 100}`, then `100` and `DeprecationWarning`.
- given `{"max_posts": 100, "max_rows": 99}`, then `pytest.raises(ValueError)`.

`TestStopAtRunRowCap` (rename from `test_stop_at_max_rows_*`): pending tasks skipped when `metadata["row_count"] >= run_row_cap_int`; no-op when cap is `None` or count below cap.

Platform checkpoint tests:

- Bluesky: update `test_run_sync_tasks_caps_fetch_by_remaining_max_rows` to set `max_posts` (add a sibling test that `max_rows` alias still caps the same way with warning).
- Twitter: if a cap test exists or is added, assert stop/skip behavior with `max_posts` and alias `max_rows`.
- Reddit: assert run stops when comment `row_count` reaches `max_comments`; `post_row_count` above cap does not trigger early stop (posts-only growth must not satisfy the comment cap).

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per helper function.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Exit 0.

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0. No new failures.

## Must not happen

- Removing `max_rows` alias support in this PR (external configs may still use it).
- Capping Reddit ingest on `post_row_count` or renaming `metadata["row_count"]` for Reddit.
- Changing numeric cap values in committed YAML (key rename only).
- Adding `max_posts` to Reddit YAML or `max_comments` to Bluesky/Twitter YAML.
- Leaving `parse_max_rows` or `stop_at_max_rows` exported after rename (grep must be clean).
- Touching per-task limit resolution (step 6) or preprocess.
