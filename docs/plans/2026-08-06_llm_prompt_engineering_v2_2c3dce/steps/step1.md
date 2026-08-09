# Step 1: Scaffold v2 package, brief README, and balanced 1,000-post subset

## Goal

Create `experiments/llm_prompt_engineering_v2_2026_08_05/` with a **brief** README that points at v1 and states only the three deltas (1,000 posts; 500 keep / 500 remove; Qwen 3.6). Add `build_subset.py` that **imports** load/write helpers from v1 and freezes a **class-balanced** `subset_labels.csv` (500 keep + 500 remove, seed 42).

Do **not** call any LLM in this step.

## Caller / unit of work

**Main caller:** `experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py` as a CLI:

1. Import `load_keep_remove_labels` and `write_subset` from `experiments.llm_prompt_engineering_2026_08_05.build_subset`.
2. Split the loaded frame by `decision` ∈ `{keep, remove}` (after the same normalize/validate that v1 already applied inside `load_keep_remove_labels`).
3. Sample **500 keep** and **500 remove** without replacement, each with `random_state=42` (same seed for both class draws; concat keep then remove, then optionally shuffle with the same seed for row order stability — **must be deterministic**).
4. Write `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv`.
5. Print row count, keep count, remove count, and path; exit 0.

**Also in this step:** create the experiment directory + terse README (link to v1; list the three deltas; document the build-subset command only).

**Out of scope:** LLM calls, `run_classifier.py`, `evaluate.py`, `RESULTS.md`, edits to `shared/**`, edits to the v1 tree (import-only), prompt redesign.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/README.md` | v1 shape to mirror briefly |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/build_subset.py` | Import `load_keep_remove_labels`, `write_subset`; do **not** reuse `sample_subset` (unbalanced) |
| `/workspace/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` | `sample_class_posts` — per-class sample pattern to mirror |
| `/workspace/shared/data/registry.py` | Same catalog entry as v1 (`STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`) |
| `/workspace/docs/plans/2026-08-06_llm_prompt_engineering_v2_2c3dce/plan.md` | Confirmed deltas |

## Files allowed to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/README.md` (create; brief)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py` (create)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (create by running the script)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/__init__.py` (optional empty package marker if needed for imports)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/pyproject.toml`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**` (import source only)
- Do **not** create `run_classifier.py`, `evaluate.py`, or `RESULTS.md` in this step
- Do not `git commit` unless the user asks

## Contracts to freeze

### Constants

| Name | Value |
|------|-------|
| Keep sample size | `500` |
| Remove sample size | `500` |
| Total rows | `1000` |
| Seed | `42` |
| Output path | `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` |
| Label source | same as v1 via imported `load_keep_remove_labels()` |

### Sampling behavior

1. `frame = load_keep_remove_labels()` (imported from v1).
2. `keep_df = frame[frame["decision"] == "keep"]`; `remove_df = frame[frame["decision"] == "remove"]`.
3. Assert `len(keep_df) >= 500` and `len(remove_df) >= 500`.
4. Sample each class with `n=500`, `random_state=42` (same pattern as `sample_class_posts` in `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py`).
5. Concatenate to exactly 1000 rows; reset index.
6. Assert keep count == 500 and remove count == 500 on the written frame.
7. `write_subset(subset, output_path, force)` (imported from v1) — refuse to clobber unless `--force`.

### README (exact tone)

Terse. Must:

1. Link to `../llm_prompt_engineering_2026_08_05/README.md` as the base experiment.
2. State only: larger balanced subset (1000 = 500 keep + 500 remove); model = latest Qwen 3.6 via research_tools; otherwise same as v1 (import).
3. Document the build-subset command.

Do **not** paste the full v1 README.

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py [--force]
```

Defaults: 500 keep + 500 remove, seed 42.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py

PYTHONPATH=. uv run python -c "
import pandas as pd
from pathlib import Path
p = Path('experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv')
assert p.is_file(), p
df = pd.read_csv(p)
assert len(df) == 1000, len(df)
for col in ('message_id', 'original_text', 'mirror_text', 'decision', 'keep_remove_label'):
    assert col in df.columns, col
assert df['message_id'].is_unique
dec = df['decision'].astype(str).str.lower().str.strip()
assert set(dec) <= {'keep', 'remove'}
assert (dec == 'keep').sum() == 500, (dec == 'keep').sum()
assert (dec == 'remove').sum() == 500, (dec == 'remove').sum()
print('v2 subset OK', len(df), 'keep', (dec=='keep').sum(), 'remove', (dec=='remove').sum())
"
```

Reproducibility check:

```bash
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/build_subset.py --force
PYTHONPATH=. uv run python -c "
import pandas as pd
a = pd.read_csv('experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv')
# second force rewrite in same process after re-run above should match ids
print('message_id sample', sorted(a['message_id'].astype(str).tolist())[:3])
"
# Re-run --force again and diff message_id sets — must be identical
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Script exits | exit code 0 | Non-zero / traceback |
| Row count | exactly 1000 | Any other count |
| Balance | exactly 500 keep and 500 remove | Unbalanced |
| Columns | five required columns present | Missing column |
| `message_id` | unique within subset | Duplicates |
| Sampling | `--force` + seed 42 reproduces same `message_id` set | Different rows on re-run |
| Imports | uses v1 `load_keep_remove_labels` / `write_subset` | Copied full v1 load/write logic |
| No LLM | no runner / API imports in `build_subset.py` | Runner or API key required |
| README | brief; links v1; states three deltas | Full v1 paste / missing deltas |

## Done when

1. `experiments/llm_prompt_engineering_v2_2026_08_05/README.md` exists and is brief.
2. `build_subset.py` imports v1 helpers and writes a balanced 1000-row CSV.
3. Re-running with `--force` and seed 42 reproduces the same `message_id` set.
4. No LLM code; no edits under `shared/` or the v1 experiment tree.
