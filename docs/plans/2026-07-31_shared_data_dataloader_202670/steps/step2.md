# Step 2: Implement registry module

## Goal

Add `shared/data/registry.py` that exposes the five frozen dataset names from Step 1 and resolves each to an absolute filesystem path. No CSV I/O.

## Caller / unit of work

**Main caller:** `shared.data.dataloader` (Step 3) will call into this module to resolve a name before reading.

**In scope:** Catalog constants, entry metadata, `get_dataset` / path resolution helpers.

**Out of scope:** `pd.read_csv`; transforms; tests; experiment migrations; changing files under `shared/data/raw/`.

## Prep references

- Name → path table: [step1.md](step1.md) § Registry contract
- Parent plan: [plan.md](../plan.md)

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_shared_data_dataloader_202670/steps/step1.md` | Authoritative name→path map |
| `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/data/dataloader.py` | Prior path-resolution style (`Path(__file__).resolve()`) for consistency only |
| `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` | Currently empty; do not implement load here |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` (create)
- `/Users/mark/src/work/mirrorview-wt/shared/data/__init__.py` (create only if needed so `shared.data` imports cleanly; keep empty or re-export registry names—no load logic)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` (Step 3)
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`

## Contract freeze

Implement exactly these public surfaces (names may be attributes or string constants, but callers must be able to use the five SCREAMING_SNAKE identifiers):

```text
DatasetKind: "results" | "stimuli"   (Literal or Enum)
DatasetEntry: frozen record with fields
  - name: str
  - relative_path: Path   # repo-relative
  - kind: DatasetKind
  - study_phase: str

DATASETS: mapping name -> DatasetEntry   # exactly the five Step 1 rows

REPO_ROOT: Path   # parents of shared/data/ until repo root
  # shared/data/registry.py -> parent=data, parent=shared, parent=repo root
  # i.e. Path(__file__).resolve().parents[2]

get_dataset(name: str) -> DatasetEntry
  # KeyError if unknown, message must include the unknown name

resolve_path(name: str) -> Path
  # absolute path = REPO_ROOT / entry.relative_path
  # does NOT check file existence (existence check is dataloader’s job)
```

Also export the five name strings as module-level constants matching Step 1 exactly:

- `STUDY_PHASE_2_PART_1_RESULTS_PILOT`
- `STUDY_PHASE_2_PART_1_RESULTS_FULL`
- `STUDY_PHASE_2_PART_1_STIMULI`
- `STUDY_PHASE_2_PART_2_RESULTS_FULL`
- `STUDY_PHASE_2_PART_2_STIMULI`

## Implementation notes

- Use `dataclasses.dataclass(frozen=True)` or equivalent for `DatasetEntry`.
- `relative_path` values must match Step 1 paths character-for-character.
- Do not glob the filesystem to discover datasets.
- Do not read CSV headers.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# After registry.py exists — import and resolve without reading CSV
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
from shared.data import registry

names = [
    registry.STUDY_PHASE_2_PART_1_RESULTS_PILOT,
    registry.STUDY_PHASE_2_PART_1_RESULTS_FULL,
    registry.STUDY_PHASE_2_PART_1_STIMULI,
    registry.STUDY_PHASE_2_PART_2_RESULTS_FULL,
    registry.STUDY_PHASE_2_PART_2_STIMULI,
]
assert set(names) == set(registry.DATASETS.keys())
for name in names:
    p = registry.resolve_path(name)
    assert p.is_absolute(), p
    assert p == registry.REPO_ROOT / registry.get_dataset(name).relative_path
    print(name, "->", p.relative_to(registry.REPO_ROOT))

try:
    registry.get_dataset("NOT_A_DATASET")
except KeyError as e:
    print("OK_UNKNOWN:", e)
else:
    raise SystemExit("expected KeyError for unknown name")
print("STEP2_OK")
PY
```

### Expected outputs (pass signals)

```text
STUDY_PHASE_2_PART_1_RESULTS_PILOT -> shared/data/raw/study_phase_2_part_1/results/pilot.csv
STUDY_PHASE_2_PART_1_RESULTS_FULL -> shared/data/raw/study_phase_2_part_1/results/full.csv
STUDY_PHASE_2_PART_1_STIMULI -> shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv
STUDY_PHASE_2_PART_2_RESULTS_FULL -> shared/data/raw/study_phase_2_part_2/results/full.csv
STUDY_PHASE_2_PART_2_STIMULI -> shared/data/raw/study_phase_2_part_2/stimuli/flips.csv
OK_UNKNOWN: ...
STEP2_OK
```

## Pass / fail

**Pass:** `registry.py` exists; five constants resolve to the Step 1 relative paths; unknown name raises `KeyError`; no CSV is read.

**Fail:** Extra datasets; wrong relative paths; existence checks or `read_csv` inside the registry; experiment files touched.
