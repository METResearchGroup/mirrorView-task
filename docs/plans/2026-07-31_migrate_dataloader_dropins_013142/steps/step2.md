# Step 2: Point Part 2 stimuli callers at the shared loader

## Goal

Replace hardcoded reads of `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv` with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`. That registry file is column- and key-equivalent to the combined flips CSV (10,000 rows). No truncation / generation logic changes.

## Caller / unit of work

**Main callers (in this step):**

1. `experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py` — defines the shared input for v1/v2/ablations
2. `experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths_v2.py`
3. `experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py`
4. `experiments/truncate_posts_2026_06_19/truncate_flips.py` — default input imported by v2/v3
5. `experiments/truncate_posts_2026_06_19/truncate_flips_v2.py`
6. `experiments/truncate_posts_2026_06_19/truncate_flips_v3.py`
7. `experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py`
8. `experiments/scaled_mirrors_generation_2026_06_02/validate_mirrors_equal_lengths.py`

**In scope:** Default / hardcoded stimuli ingress only. CLI overrides that already accept an explicit path may remain if present, but the **default** must be the shared loader.

**Out of scope:** Part 1 results migrations (Step 1); producers under `scaled_mirrors_generation` other than the validator; deleting `combined_flips/flips.csv`; registry changes.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` | `load_dataset` |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_STIMULI` |
| `/Users/mark/src/work/mirrorview-wt/strategy_planning/migrate_to_single_dataloader_2026_07_31/migration_plan.md` | Phase 1 stimuli rows |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_migrate_dataloader_dropins_013142/plan.md` | Parent plan |
| Each file in “Files allowed to change” | Current `INPUT_CSV` / `FLIPS_CSV` / `DEFAULT_INPUT_CSV` usage |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths_v2.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/truncate_posts_2026_06_19/truncate_flips.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/truncate_posts_2026_06_19/truncate_flips_v2.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/truncate_posts_2026_06_19/truncate_flips_v3.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/validate_mirrors_equal_lengths.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/balance_flips.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/scaled_mirrors_generation_2026_06_02/generate_flips.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/match_lengths_original_mirrors_2026_06_19/README.md` (docs optional; not required this step)
- Any Step 1 Part 1 results files (unless already finished in Step 1)

## Per-file changes (exact)

### Shared pattern (both experiment families)

Prefer a small helper in the **parent** module so siblings do not re-pin paths:

```python
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI

def load_default_stimuli() -> pd.DataFrame:
    return load_dataset(STUDY_PHASE_2_PART_2_STIMULI)
```

Remove `Path(.../combined_flips/flips.csv)` constants used as the default input. Replace `INPUT_CSV.exists()` / `pd.read_csv(INPUT_CSV)` with the helper (missing file → `FileNotFoundError` from `load_dataset`). For log lines that printed the path, use `registry.resolve_path(STUDY_PHASE_2_PART_2_STIMULI)`.

### 1–3. Match-lengths family

- `run_match_lengths.py`: add `load_default_stimuli()` (name may vary); remove `INPUT_CSV` Path constant; load via helper in `main`.
- `run_match_lengths_v2.py`: stop importing `INPUT_CSV`; import / call the helper from `run_match_lengths.py`.
- `run_ablations.py`: same as v2.

### 4–6. Truncate-posts v1–v3

- `truncate_flips.py`: replace `INPUT_CSV` Path with a load helper (or inline `load_dataset`); update the function that currently does `pd.read_csv(source_csv)` so the default path is the shared stimuli load. If the CLI still accepts an optional override path, keep that branch as `pd.read_csv(override)` only when an override is passed.
- `truncate_flips_v2.py` / `truncate_flips_v3.py`: they import `INPUT_CSV` from `truncate_flips`. After the parent change, import the helper instead and stop treating the default input as a `Path` that must `.exists()`.

### 7. `truncation_v5/generate_flips.py`

- Replace `DEFAULT_INPUT_CSV` Path with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)` as the default input to the chunked reader path.
- If the function signature takes `input_csv: Path = DEFAULT_INPUT_CSV`, change the default to `None` meaning “use shared loader”, and only `pd.read_csv` when an explicit path is passed.

### 8. `validate_mirrors_equal_lengths.py`

- Replace `FLIPS_CSV = .../combined_flips/flips.csv` + `pd.read_csv(FLIPS_CSV)` with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

test -f shared/data/raw/study_phase_2_part_2/stimuli/flips.csv && echo OK_P2_STIM

PYTHONPATH=. uv run python - <<'PY'
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI
df = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)
assert list(df.columns) == [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "mirrored_text",
]
assert len(df) == 10000
print("STIM_ROWS", len(df))
PY

# Validator after migration
PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/validate_mirrors_equal_lengths.py
```

### Expected outputs (pass signals)

```text
OK_P2_STIM
STIM_ROWS 10000
```

Plus whatever success / metrics print the validator already emits (must complete without `FileNotFoundError` on `combined_flips/flips.csv`).

## Pass / fail

**Pass:**

- All eight allowed files use `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)` for the default stimuli ingress.
- No remaining default Path constants pointing at `combined_flips/flips.csv` in those eight files.
- `v2`/`v3`/`ablations` no longer import a Path `INPUT_CSV` that points at combined flips.
- Commands above succeed when the Part 2 stimuli CSV is present.

**Fail:**

- Rewriting truncation / LLM generation logic.
- Deleting or moving `combined_flips/flips.csv`.
- Changing shared registry / loader.
- Migrating Part 1 results files in this step (belongs in Step 1).
