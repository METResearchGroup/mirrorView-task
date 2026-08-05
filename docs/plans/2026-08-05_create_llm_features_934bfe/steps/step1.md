# Step 1: Scaffold `src/` package, keep/remove split, and output layout

## Goal

Create the experiment package under `experiments/create_llm_features_2026_08_05/src/` with four stage-module stubs, a shared paths/loader helper for keep/remove corpora, and documented output directories. Load posts from the shared transformed registry entry `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` (already modal). Do **not** implement LLM, Bedrock, or clustering logic in this step.

**Current folder state:** only `experiments/create_llm_features_2026_08_05/README.md` exists. Create the modules listed below from scratch.

## Caller / unit of work

**Main caller:** a small `__main__` / `python -c` import check that:

1. Loads the keep/remove labels CSV via `shared.data.dataloader.load_dataset`.
2. Splits into keep and remove frames.
3. Resolves the four stage output roots for a given label class (`keep` | `remove`).

**In scope:** `src/__init__.py`, four stage stubs, one small shared helper module under `src/` for paths + load/split (name it `paths.py` or `data.py` — pick one; do not invent a second tree outside `src/`).

**Out of scope:** live LLM calls, Bedrock calls, sklearn clustering, `RESULTS.md`, edits to `shared/**`, `pyproject.toml`, anything under `experiments/create_llm_feature_clusters_2026_08_02/`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` | Target layout and stage order |
| `/Users/mark/src/work/mirrorView-task/docs/plans/2026-08-05_create_llm_features_934bfe/plan.md` | Confirmed file list and happy flow |
| `/Users/mark/src/work/mirrorView-task/shared/data/dataloader.py` | `load_dataset(name)` |
| `/Users/mark/src/work/mirrorView-task/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/Users/mark/src/work/mirrorView-task/shared/data/transformed/study_phase_2_part_2/README.md` | Columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`; ~8791 rows |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Runner call-site shape for later stages; stub shape only now |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/batching.py` | Sampling/batching patterns to adapt for **single-class** batches in Step 2 |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/__init__.py` (create)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/data.py`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` (create stub)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/generate_embeddings.py` (create stub)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py` (create stub)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py` (create stub)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (append run-order commands only; do not redesign the scientific approach)
- Optional empty dir markers only if needed: `outputs/generated_features/{keep,remove}/.gitkeep`, `outputs/generated_embeddings/{keep,remove}/.gitkeep`, `outputs/clusters/{keep,remove}/.gitkeep`, `outputs/generated_labels/{keep,remove}/.gitkeep`

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/schemas.py`
- `/Users/mark/src/work/mirrorView-task/shared/embeddings/bedrock.py`
- `/Users/mark/src/work/mirrorView-task/shared/data/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/**`
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`
- Do **not** create `RESULTS.md` in this step

## Contracts to freeze

### Experiment root and output roots

```text
EXPERIMENT_ROOT = experiments/create_llm_features_2026_08_05/

stage1_root(label_class) = EXPERIMENT_ROOT / "outputs" / "generated_features" / label_class
stage2_root(label_class) = EXPERIMENT_ROOT / "outputs" / "generated_embeddings" / label_class
stage3_root(label_class) = EXPERIMENT_ROOT / "outputs" / "clusters" / label_class
stage4_root(label_class) = EXPERIMENT_ROOT / "outputs" / "generated_labels" / label_class
```

`label_class` is exactly the string `"keep"` or `"remove"`. Raise `ValueError` for any other value.

### Loader / split

Public helpers (names may vary; behavior must match):

1. `load_keep_remove_posts() -> pd.DataFrame`  
   - Calls `shared.data.dataloader.load_dataset("STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS", low_memory=False)` (or the registry constant).  
   - Requires columns: `message_id`, `original_text`, `mirror_text`, `decision`.  
   - Asserts `decision` values ⊆ `{"keep", "remove"}` after normalizing to lowercase stripped strings if needed.  
   - Does **not** re-aggregate modal labels (the CSV is already modal).

2. `split_by_decision(df) -> tuple[pd.DataFrame, pd.DataFrame]`  
   - Returns `(keep_df, remove_df)` where `keep_df` has only `decision == "keep"` and `remove_df` only `decision == "remove"`.  
   - Sanity expectation on full load: `len(keep_df) ≈ 5978`, `len(remove_df) ≈ 2813`, `len(df) ≈ 8791`.

### Stage stubs

Each of the four stage modules must:

- Be importable: `from experiments.create_llm_features_2026_08_05.src import llm_generate_features` (and siblings).
- Expose a `main`-callable entry or a named `run_*` function that currently raises `NotImplementedError` (or has an empty body that documents “implemented in Step N”).
- Contain **no** live OpenAI / Bedrock / sklearn fit calls in this step.

### README run-order block (append)

Document exact CLI order (stubs may fail until later steps), and pin the smoke vs production sample sizes:

```bash
# Per label class: keep | remove
# Smoke (Step 6): --sample-size 10 --posts-per-batch 10  → 1 prompt/class, ≤8 features/prompt
# Production (Step 7, after smoke approval): --sample-size 500 --posts-per-batch 10
#   → 50 keep + 50 remove feature-gen prompts; ≤8 features/prompt → ≤800 features to embed
# Clustering (Step 4): both HDBSCAN + KMeans; PNGs at outputs/clusters/{keep,remove}/cluster_{hdbscan,kmeans}.png
# Labeling (Step 5): HDBSCAN assignments only

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py --label-class keep ...
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py --label-class keep ...
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py --label-class keep ...
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_labels_for_embeddings.py --label-class keep ...
```

Exact flags are finalized in Steps 2–5; this step records the intended order, the `--label-class {keep,remove}` split, and the pinned production sizes (**500 keep / 500 remove**, **10 posts/batch**, **≤8 features/prompt**).

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.create_llm_features_2026_08_05.src import paths  # or data — match the name you chose
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

df = paths.load_keep_remove_posts()  # or data.load_keep_remove_posts
assert set(df['decision'].unique()) <= {'keep', 'remove'}
keep_df, remove_df = paths.split_by_decision(df)
assert len(df) == len(keep_df) + len(remove_df)
assert abs(len(df) - 8791) < 5
print('posts', len(df), 'keep', len(keep_df), 'remove', len(remove_df))
for cls in ('keep', 'remove'):
    for fn in (paths.stage1_root, paths.stage2_root, paths.stage3_root, paths.stage4_root):
        p = fn(cls)
        assert isinstance(p, Path)
        assert cls in str(p)
print('paths OK')
"

PYTHONPATH=. uv run python -c "
from experiments.create_llm_features_2026_08_05.src import (
    llm_generate_features,
    generate_embeddings,
    cluster_embeddings,
    generate_labels_for_embeddings,
)
print('stubs import OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Load | prints `posts 8791 keep 5978 remove 2813` (approx) | Wrong registry name / re-aggregation / KeyError |
| Paths | `paths OK` | Roots missing `{keep,remove}` segment |
| Stubs | `stubs import OK` | ImportError / missing modules |
| No shared edits | `git diff -- shared/ pyproject.toml` empty for this step | Diff touches shared or pyproject |
| No tests package | `tests/` does not exist under the experiment | Pytest suite added |

## Done when

- `src/__init__.py` and four stage stubs exist and import.
- Keep/remove load+split works against `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`.
- Stage output roots resolve under `outputs/{generated_features,generated_embeddings,clusters,generated_labels}/{keep,remove}/`.
- README documents stage run order and pinned smoke (`10`) vs production (`500` keep / `500` remove, 10 posts/batch, ≤8 features/prompt → ≤800 embeddings).
- No LLM/Bedrock/cluster logic and no shared-library edits.
