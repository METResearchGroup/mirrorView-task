# Step 1: Freeze registry entries and on-disk map

## Goal

Lock the five named datasets to exact on-disk CSVs under `shared/data/raw/` and define the registry entry metadata shape. No Python implementation in this step—document the contract that Steps 2–3 implement.

## Caller / unit of work

**Main caller:** Future experiment scripts that will call `shared.data.dataloader.load_dataset(...)`.

**In scope:** Final name → path table; metadata fields; error semantics for unknown names.

**Out of scope:** Writing `registry.py` / `dataloader.py` bodies; transforms; tests; experiment migrations.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_1/results/pilot.csv` | Part 1 pilot results |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_1/results/full.csv` | Part 1 full results |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv` | Part 1 stimuli |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/results/full.csv` | Part 2 full results |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Part 2 stimuli |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_1/results/README.md` | Part 1 docs |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/README.md` | Part 2 docs |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_shared_data_dataloader_202670/plan.md` | Parent plan + replaceability tracker |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_shared_data_dataloader_202670/steps/step1.md` (this file only, if clarifying)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` (must not exist yet, or leave untouched until Step 2)
- `/Users/mark/src/work/mirrorview-wt/experiments/**`
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**` (do not move or rename CSVs)

## Registry contract (authoritative)

### Names → paths

Paths are relative to the repository root (`/Users/mark/src/work/mirrorview-wt`).

| Registry name | Relative path |
|---|---|
| `STUDY_PHASE_2_PART_1_RESULTS_PILOT` | `shared/data/raw/study_phase_2_part_1/results/pilot.csv` |
| `STUDY_PHASE_2_PART_1_RESULTS_FULL` | `shared/data/raw/study_phase_2_part_1/results/full.csv` |
| `STUDY_PHASE_2_PART_1_STIMULI` | `shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv` |
| `STUDY_PHASE_2_PART_2_RESULTS_FULL` | `shared/data/raw/study_phase_2_part_2/results/full.csv` |
| `STUDY_PHASE_2_PART_2_STIMULI` | `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` |

These five names are the complete v1 catalog. Do not add aliases or “latest” discovery.

### Entry metadata

Each registry entry must expose:

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | Exact SCREAMING_SNAKE key from the table above |
| `relative_path` | `str` or `Path` | Repo-relative path from the table above |
| `kind` | `str` | `"results"` or `"stimuli"` |
| `study_phase` | `str` | `"study_phase_2_part_1"` or `"study_phase_2_part_2"` |

### Error semantics (for Steps 2–3)

| Condition | Error |
|---|---|
| Name not in catalog | `KeyError` including the unknown name and a hint that valid names live in the registry |
| Name valid but file missing on disk | `FileNotFoundError` including the resolved absolute path |

### Explicit non-goals for v1

- No column validation / schema enforcement
- No filtering (`linked_fate`, `phase > 0`, etc.)
- No write of derived tables under `shared/data/transformed/`
- No experiment import rewires

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# Confirm all five CSVs exist
test -f shared/data/raw/study_phase_2_part_1/results/pilot.csv && echo OK_PILOT
test -f shared/data/raw/study_phase_2_part_1/results/full.csv && echo OK_P1_FULL
test -f shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv && echo OK_P1_STIM
test -f shared/data/raw/study_phase_2_part_2/results/full.csv && echo OK_P2_FULL
test -f shared/data/raw/study_phase_2_part_2/stimuli/flips.csv && echo OK_P2_STIM
```

### Expected outputs (pass signals)

```text
OK_PILOT
OK_P1_FULL
OK_P1_STIM
OK_P2_FULL
OK_P2_STIM
```

## Pass / fail

**Pass:** All five paths exist; the name→path table above is treated as authoritative for Steps 2–3.

**Fail:** Any CSV missing; any desire to rename files or invent sixth names without updating this step first.
