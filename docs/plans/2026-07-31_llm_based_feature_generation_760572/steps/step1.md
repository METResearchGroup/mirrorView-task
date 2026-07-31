# Step 1: Scaffold experiment inputs, schemas, and batching

## Goal

Create experiment-local schemas, prompts, and a pure (no LLM) sampling/batching module under `experiments/llm_based_feature_generation_2026_07_31/`. End-to-end verification is via `smoke_tests/run_smoke.py` (not a unit-test suite).

## Caller / unit of work

**Main caller:** later stages will call the batching API; this step’s immediate caller is a small `__main__` smoke print on the batching module (full pipeline smoke lands with the CLI).

**In scope:** `__init__.py`, `schemas.py`, `prompts.py`, `batching.py`.

**Out of scope:** any LLM calls, `research_tools.llm.runner.run`, CLI, `RESULTS.md`, edits to `shared/schemas.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` | Problem statement / batch shape |
| `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/data/dataloader.py` | Study 2 training frame API (`Dataloader.load_training_dataframe`) |
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
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- Any file under `webapp/`

## Contracts to freeze

### `schemas.py`

- Feature-generation response: a batch-level structured object with a batch index, lists of keep-group and remove-group post feature objects (each post has `message_id` and a list of features). Each feature has name, value, category string, confidence in `[0,1]`, evidence span, and short rationale. No confusion-bucket fields (`tp`/`tn`/`fp`/`fn`).
- Theme-synthesis response: a list of themes, each with id, label, defining features, example message ids, keep/remove mix counts, and interpretation; plus a top-level list of cross-cutting themes. No FP-specific theme field.

### `prompts.py`

- Stage-1 prompt: ask for high-confidence linguistic/content features that distinguish or characterize keep-rated vs remove-rated posts in the batch; include original + mirror text; do not predict labels; do not mention Qwen or FP/FN.
- Stage-2 prompt: synthesize recurring themes from stage-1 feature JSON; no FP-vs-TN overrepresentation language.

### `batching.py`

Public functions (behavior, not naming theater):

1. Load the Study 2 training dataframe via `Dataloader().load_training_dataframe()`.
2. Sample a fraction in `(0, 1]` of posts **without replacement**, stratified by `decision` (`keep` / `remove`) so each class is sampled at that fraction (use `math.ceil` so tiny pilots still get at least one row per class when the class is non-empty). Deterministic given an integer seed.
3. From the sample, form as many batches as possible of exactly `keep_per_batch` keep rows and `remove_per_batch` remove rows (defaults 10 and 10). Each row’s `message_id` appears in **at most one** batch. Leftover rows that cannot fill a full batch are returned separately (not silently dropped without visibility).
4. Optional exclude set of `message_id`s: those ids are removed before sampling (for re-run safety).
5. Raise if zero full batches can be formed after sampling.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.llm_based_feature_generation_2026_07_31.batching import load_posts, sample_posts, form_batches
df = load_posts()
sample = sample_posts(df, fraction=0.01, seed=42)
batches, leftover = form_batches(sample, keep_per_batch=10, remove_per_batch=10)
ids = [m for b in batches for m in b['message_ids']]
assert len(ids) == len(set(ids)), 'duplicate message_id across batches'
print('posts', len(df), 'sample', len(sample), 'batches', len(batches), 'leftover', len(leftover))
"
# Expect: prints positive batch count; no AssertionError
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Schemas import | `from experiments.llm_based_feature_generation_2026_07_31.schemas import ...` works | ImportError / missing fields |
| Batching smoke | uniqueness assert holds; positive batch count | AssertionError / zero batches |
| No shared schema edit | `git diff -- shared/schemas.py` empty for this step | Diff touches shared schemas |
| Prompt text | Stage-2 prompt has no substrings `FP`, `false positive`, `TN`, `false negative`, `over-represent` | Those strings present |

## Done when

- Experiment-local schemas and prompts exist.
- Batching loads Study 2 data, samples without replacement, forms unique-id batches.
- `shared/schemas.py` unchanged.
