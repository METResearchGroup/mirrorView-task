# Step 1: Scaffold experiment inputs, schemas, and batching

## Goal

Create experiment-local schemas, prompts, and a pure (no LLM) sampling/batching module under `experiments/llm_based_feature_generation_2026_07_31/`. Load raw Study Phase 2 Part 2 results through the shared registry/loader, then derive the modal keep/remove training frame in this experiment. Do **not** add a `tests/` package; end-to-end verification comes later via `smoke_tests/` (Step 4).

**Current folder state:** only `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` exists. Create the modules listed below from scratch (do not resurrect deleted implementation unless a later decision says so).

## Caller / unit of work

**Main caller:** later stages will call the batching API; this step’s immediate caller is a small `__main__` print on the batching module.

**In scope:** `__init__.py`, `schemas.py`, `prompts.py`, `batching.py`.

**Out of scope:** any LLM calls, `research_tools.llm.runner.run`, CLI, `smoke_tests/`, `RESULTS.md`, the frozen 50% `data/sampled_subset.csv` persistence (Step 5 only), edits to `shared/schemas.py`, edits to `shared/data/**`, any `tests/` package.

## Why this dataset (not the others)

| Registry name | Use for this experiment? | Why |
|---|---|---|
| `STUDY_PHASE_2_PART_2_RESULTS_FULL` | **Yes — required** | Canonical Study 2 / Phase 2 Part 2 human keep/remove trial rows (`decision`, `original_text`, `mirror_text`, `post_id`). Matches the prior Study 2 training-frame size when aggregated. |
| `STUDY_PHASE_2_PART_2_STIMULI` | No | Stimuli only (`flips.csv`); no keep/remove labels. |
| `STUDY_PHASE_2_PART_1_RESULTS_*` | No | Different collection round; not the Study 2 keep/remove frame this experiment targets. |
| `STUDY_PHASE_2_PART_1_STIMULI` | No | Part 1 stimuli only. |

**Obsolete runtime path:** do **not** call `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` at runtime. That module pins an experiment-local CSV. Inspect it **read-only** only as the aggregation recipe lineage (linked-fate filter → modal keep/remove per post, tie → remove, expose `message_id`).

**Shared loader contract:** `shared/data/dataloader.py` is raw-only (no filters, no modal aggregation). All keep/remove shaping lives in this experiment’s `batching.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` | Problem statement / batch shape |
| `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` | Canonical raw loader (`load_dataset`) |
| `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py` | Registry name `STUDY_PHASE_2_PART_2_RESULTS_FULL` → CSV path |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/results/full.csv` | On-disk Part 2 results (columns include `decision`, `post_id`, `original_text`, `mirror_text`, `evaluation_mode`) |
| `/Users/mark/src/work/mirrorview-wt/shared/data/raw/study_phase_2_part_2/README.md` | Part 2 data docs |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-07-31_shared_data_dataloader_202670/plan.md` | Shared loader intent + replaceability note for this experiment |
| `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/data/dataloader.py` | Aggregation recipe lineage only (not runtime import) |
| `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py` | Prompt lineage to adapt |
| `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/extract/schemas.py` | Feature/theme schema lineage (adapt; drop confusion buckets) |
| `/Users/mark/src/work/mirrorview-wt/shared/schemas.py` | Confirm keep/remove-only; do not extend |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/__init__.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/schemas.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/prompts.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` (create)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/raw/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- Any file under `webapp/`
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/tests/`
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv` (frozen 50% subset is Step 5 only)

## Contracts to freeze

### `schemas.py`

- Feature-generation response: a batch-level structured object with a batch index, lists of keep-group and remove-group post feature objects (each post has `message_id` and a list of features). Each feature has name, value, category string, confidence in `[0,1]`, evidence span, and short rationale. No confusion-bucket fields (`tp`/`tn`/`fp`/`fn`).
- Theme-synthesis response: a list of themes, each with id, label, defining features, example message ids, keep/remove mix counts, and interpretation; plus a top-level list of cross-cutting themes. No FP-specific theme field.

### `prompts.py`

- Stage-1 prompt: ask for high-confidence linguistic/content features that distinguish or characterize keep-rated vs remove-rated posts in the batch; include original + mirror text; do not predict labels; do not mention Qwen or FP/FN.
- Stage-2 prompt: synthesize recurring themes from stage-1 feature JSON; no FP-vs-TN overrepresentation language.

### `batching.py`

Public functions (behavior, not naming theater):

1. Load Part 2 results with `shared.data.dataloader.load_dataset` using registry name `STUDY_PHASE_2_PART_2_RESULTS_FULL` (prefer `low_memory=False` for this CSV).
2. Derive the training frame **in this module** (same semantics as the 2026-07-01 dataloader recipe, without importing that module):
   - Normalize `decision` to lowercase stripped strings.
   - If `evaluation_mode` is present, keep only `linked_fate` rows.
   - Keep only rows whose `decision` is `keep` or `remove`.
   - Require columns `post_id`, `original_text`, `mirror_text`, `decision`.
   - Aggregate to **one row per `post_id`**: modal decision across raters; **ties → `remove`**.
   - Rename `post_id` → `message_id` for downstream batch keys.
   - Output columns at least: `message_id`, `original_text`, `mirror_text`, `decision` (keep/remove strings).
3. Sample a fraction in `(0, 1]` of posts **without replacement**, stratified by `decision` (`keep` / `remove`) so each class is sampled at that fraction (use `math.ceil` so tiny fractions, e.g. smoke, still get at least one row per class when the class is non-empty). Deterministic given an integer seed. Scaffolding **may** expose a fraction parameter for smoke / ad-hoc runs; the **frozen 50% subset CSV** (`experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`) is **Step 5’s responsibility** — do not implement or write that persistence in this step.
4. From the sample, form as many batches as possible of exactly `keep_per_batch` keep rows and `remove_per_batch` remove rows (defaults 10 and 10). Each row’s `message_id` appears in **at most one** batch. Leftover rows that cannot fill a full batch are returned separately (not silently dropped without visibility).
5. Optional exclude set of `message_id`s: those ids are removed before sampling (for re-run safety).
6. Raise if zero full batches can be formed after sampling.

**Sanity expectation after derive (full corpus, no sample):** ~8791 posts with modal split ≈ 5978 keep / 2813 remove (matches prior Study 2 training frame derived from the same Part 2 source).

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.llm_based_feature_generation_2026_07_31.batching import load_posts, sample_posts, form_batches
df = load_posts()
assert set(df['decision'].unique()) <= {'keep', 'remove'}
assert 'message_id' in df.columns
sample = sample_posts(df, fraction=0.50, seed=42)
batches, leftover = form_batches(sample, keep_per_batch=10, remove_per_batch=10)
ids = [m for b in batches for m in b['message_ids']]
assert len(ids) == len(set(ids)), 'duplicate message_id across batches'
print('posts', len(df), 'sample', len(sample), 'batches', len(batches), 'leftover', len(leftover))
"
# Expect: posts ~= 8791; prints positive batch count; no AssertionError
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Schemas import | `from experiments.llm_based_feature_generation_2026_07_31.schemas import ...` works | ImportError / missing fields |
| Load path | `load_posts` uses `shared.data.dataloader.load_dataset` + `STUDY_PHASE_2_PART_2_RESULTS_FULL` | Imports `experiments.predict_keep_remove_2026_07_01` dataloader |
| Batching check | uniqueness assert holds; positive batch count; full `load_posts()` ≈ 8791 rows | AssertionError / zero batches / wrong source |
| No shared edits | `git diff -- shared/schemas.py shared/data/` empty for this step | Diff touches shared schemas or shared data modules |
| Prompt text | Stage-2 prompt has no substrings `FP`, `false positive`, `TN`, `false negative`, `over-represent` | Those strings present |
| No unit tests | `tests/` does not exist under the experiment | Pytest suite added |

## Done when

- Experiment-local schemas and prompts exist.
- Batching loads Part 2 via `shared/data/`, derives modal keep/remove, samples without replacement, forms unique-id batches.
- No runtime dependency on `experiments/predict_keep_remove_2026_07_01/data/dataloader.py`.
- No `tests/` package under the experiment.
- `shared/schemas.py` and `shared/data/**` unchanged.
