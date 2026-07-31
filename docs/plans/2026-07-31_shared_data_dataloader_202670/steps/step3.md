# Step 3: Implement raw runtime loader

## Goal

Implement `shared/data/dataloader.py` so a caller passes a registry dataset name and receives a pandas DataFrame of the raw CSV. No transforms.

## Caller / unit of work

**Main caller:** Any future experiment or script, e.g.:

```python
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL

df = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL)
```

**In scope:** Resolve name via registry, verify file exists, `pd.read_csv`, return DataFrame; clear errors.

**Out of scope:** Filtering, aggregation, column renaming, writes to `shared/data/transformed/`, unit test files, experiment migrations.

## Prep references

- Registry API: [step2.md](step2.md) § Contract freeze
- Name → path map: [step1.md](step1.md) § Registry contract
- Prior slim loader style (do **not** copy transforms): `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/data/dataloader.py` (`pd.read_csv(..., low_memory=False)` only)

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Must exist from Step 2 |
| `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/data/dataloader.py` | `low_memory=False` read pattern |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_shared_data_dataloader_202670/plan.md` | Replaceability tracker (do not migrate) |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` (implement)
- `/Users/mark/src/work/mirrorview-wt/shared/data/__init__.py` (optional re-export of `load_dataset` only)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` (unless a bug blocks load; prefer fix only if Step 2 contract broken)
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/**`
- `/Users/mark/src/work/mirrorview-wt/shared/data/transformed/**`

## Contract freeze

```text
load_dataset(name: str, *, low_memory: bool = False) -> pandas.DataFrame

Behavior:
  1. Call registry.resolve_path(name)   # KeyError if unknown name (propagate)
  2. If path does not exist: raise FileNotFoundError with absolute path in message
  3. return pd.read_csv(path, low_memory=low_memory)
  4. Do not filter rows, drop columns, rename columns, or aggregate
```

Optional convenience (allowed, not required):

```text
class Dataloader:
    def load(self, name: str, *, low_memory: bool = False) -> pd.DataFrame:
        return load_dataset(name, low_memory=low_memory)
```

Prefer the module-level `load_dataset` as the primary API so callers do not need a class.

## Implementation notes

- Import registry from `shared.data.registry` (not relative hacks that break `PYTHONPATH=.`).
- Do not pin CSV paths inside `dataloader.py`; all paths come from the registry.
- Keep the function body under ~20 lines.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data import registry

# Smoke: load each dataset header/shape only (nrows to stay fast on large files)
checks = [
    (registry.STUDY_PHASE_2_PART_1_RESULTS_PILOT, ["trial_type", "prolific_id"]),
    (registry.STUDY_PHASE_2_PART_1_RESULTS_FULL, ["trial_type", "prolific_id"]),
    (registry.STUDY_PHASE_2_PART_1_STIMULI, ["post_primary_key", "claude_mirror"]),
    (registry.STUDY_PHASE_2_PART_2_RESULTS_FULL, ["trial_type", "prolific_id"]),
    (registry.STUDY_PHASE_2_PART_2_STIMULI, ["post_primary_key", "mirrored_text"]),
]
for name, cols in checks:
    # Full load for stimuli (small); for large results use read via load_dataset then .head
    df = load_dataset(name)
    missing = [c for c in cols if c not in df.columns]
    assert not missing, (name, missing)
    print(name, "rows=", len(df), "cols=", len(df.columns))

try:
    load_dataset("NOT_A_DATASET")
except KeyError as e:
    print("OK_UNKNOWN:", type(e).__name__)
else:
    raise SystemExit("expected KeyError")

print("STEP3_OK")
PY
```

### Expected outputs (pass signals)

```text
STUDY_PHASE_2_PART_1_RESULTS_PILOT rows= ... cols= ...
STUDY_PHASE_2_PART_1_RESULTS_FULL rows= ... cols= ...
STUDY_PHASE_2_PART_1_STIMULI rows= ... cols= ...
STUDY_PHASE_2_PART_2_RESULTS_FULL rows= ... cols= ...
STUDY_PHASE_2_PART_2_STIMULI rows= ... cols= ...
OK_UNKNOWN: KeyError
STEP3_OK
```

(Row counts may match prior inventory: pilot ~8985, part1 full ~65581, part1 stimuli ~959, part2 full ~37696, part2 stimuli ~10000—exact equality not required if CSVs were refreshed, but columns listed above must exist.)

## Pass / fail

**Pass:** `load_dataset` returns DataFrames for all five names; unknown name → `KeyError`; missing file → `FileNotFoundError` (can be verified by temporarily pointing at a fake name only—do not delete real CSVs); no experiment files changed; no filtering applied (raw row counts ≈ full CSV).

**Fail:** Paths hardcoded in `dataloader.py`; transforms applied; new test files added; experiment imports rewritten.
