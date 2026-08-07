# Step 3: Point the sample script at the new curated root

## Goal

Make `sample_data_to_mirror.py` discover curated `metadata.json` files under the landed package data tree so a new curation run can feed sampling without restoring missing CSVs under the old experiment snapshot folder.

## Caller / unit of work

**Main caller:**

```bash
cd /Users/mark/src/work/mirrorview-wt2
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
```

After this step, with at least one curated export per platform under the new root (fixture or real), the script finds metadata and either samples successfully or fails only on sampling/content rules, not on "No metadata.json files found".

**In scope:** Change the curated discovery root (and only what is required for that) in the sample script.

**Out of scope:** Changing normalize/sample quotas; flip generation; copying historical CSVs into git; live sync.

## Decision (locked)

1. Default discovery root becomes:

`/Users/mark/src/work/mirrorview-wt2/data_platform/data/{platform}/{dataset_id}/curated/{timestamp}/metadata.json`

via glob `*/*/curated/*/metadata.json` under `REPO_ROOT / "data_platform" / "data"`.

2. Keep writing `concatenated_records/` under `experiments/scaled_mirrors_generation_2026_06_02/` (output location unchanged).

3. Do not keep a silent fallback to `experiments/scaled_mirrors_generation_2026_06_02/data` unless both trees are empty would confuse operators. Single root only: `data_platform/data`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt2/docs/plans/2026-08-06_migrate_data_ingestion_486894/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | `main()` discovery at `data_root` |
| `/Users/mark/src/work/mirrorview-wt2/data_platform/utils/dataset.py` | Confirms on-disk layout under package `data/` |
| One existing `experiments/.../data/*/.../curated/*/metadata.json` | Export filename key `files.export` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- Module docstring at top of that file (update the discovery path description)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt2/data_platform/**` (except if Step 2 left unfinished work; do not mix)
- `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/generate_flips.py`
- `/Users/mark/src/work/mirrorview-wt2/experiments/scaled_mirrors_generation_2026_06_02/balance_flips.py`
- `/Users/mark/src/work/mirrorview-wt2/webapp/**`
- `/Users/mark/src/work/mirrorview-wt2/jobs/**`

## Exact code change

In `main()`:

- Replace

```python
data_root = (
    REPO_ROOT / "experiments/scaled_mirrors_generation_2026_06_02/data"
).resolve()
```

with

```python
data_root = (REPO_ROOT / "data_platform" / "data").resolve()
```

- Keep `output_dir` as the experiment directory for `concatenated_records/`.
- Update the module docstring line that mentions discovery under `experiments/scaled_mirrors_generation_2026_06_02/data/...` to name `data_platform/data/...` instead.

No other sampling logic changes.

## Fixture verification (no live sync required)

Create a minimal three-platform curated layout under `data_platform/data/` with tiny CSVs that satisfy `normalize_mirrorview_df`, then run the sample script. Delete the fixture afterward or leave it untracked (do not commit large data). Prefer writing under a disposable dataset id prefix such as `twitter_fixture-...` only if needed for a local smoke; otherwise use `TemporaryDirectory` and monkeypatch in a one-off script.

Minimum columns per platform (see `normalize_mirrorview_df`):

| Platform | Required columns |
|----------|------------------|
| Twitter | `tweet_id`, `text`, `political_stance`, `toxicity_tier` or `sample_toxicity_type` |
| Bluesky | `uri`, `text`, `political_stance`, toxicity col |
| Reddit | `post_reddit_id`, `comment_id`, `body`, `political_stance`, toxicity col |

Stance values must include `left`/`right` (unclear/neutral are dropped). Toxicity values must map through `TOXICITY_TIER_MAP`.

`metadata.json` must include `"files": {"export": "mirrorview.csv"}` (or matching export name on disk).

```bash
cd /Users/mark/src/work/mirrorview-wt2
# After placing fixtures under data_platform/data/.../curated/.../
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py
```

Pass if the script prints value_counts tables and writes `experiments/scaled_mirrors_generation_2026_06_02/concatenated_records/<timestamp>/records.csv`. If fixtures are too small to hit `TARGET_TOTAL` of 10000, either temporarily lower `TARGET_TOTAL` only in a throwaway local edit you revert, or accept that sampling may return fewer rows if the script already allows shortfall. If the script hard-requires 10k and raises, use enough fixture rows or a temporary `TARGET_TOTAL = 6` local override that you revert before commit.

Prefer: add a tiny pytest in Step 4 for discovery path rather than committing fixtures. For Step 3 pass criteria, a one-off temp layout + run that gets past metadata discovery is enough:

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
from lib.constants import REPO_ROOT

expected = (REPO_ROOT / "data_platform" / "data").resolve()
assert expected == Path("/Users/mark/src/work/mirrorview-wt2/data_platform/data").resolve()

src = (
    REPO_ROOT / "experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py"
).read_text(encoding="utf-8")
assert 'REPO_ROOT / "data_platform" / "data"' in src
# data_root assignment must not still point at the experiment snapshot tree
assign_block = src.split("data_root =", 1)[1].split("output_dir", 1)[0]
assert "scaled_mirrors_generation_2026_06_02/data" not in assign_block
print("DISCOVERY_ROOT_OK")
PY
```

## Pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Source | `data_root` points at `data_platform/data` | Still points at experiment `data/` |
| Docstring | Describes new discovery path | Stale path text |
| Discovery | With fixtures, no "No metadata.json files found" | Empty discovery against fixtures under new root |
| Output dir | Still under the scaled_mirrors experiment folder | Output relocated without plan approval |

## Out of scope reminders

- Do not generate flips or balance.
- Do not commit `data_platform/data/` artifacts.
- Do not restore historical experiment snapshot CSVs into git.
