# Step 1: Scaffold package, paths, data join, and optional dependencies

## Goal

Create `experiments/bertopic_modeling_2026_08_05/src/` with package marker, path helpers, data loader (keep/remove + unanimous join), and four stage-module stubs. Declare an optional `bertopic` extra in `pyproject.toml`. Append stage CLI order to the existing README. Do **not** implement embedding resolution, BERTopic fit, LLM labeling, or visualization logic in this step.

**Current folder state:** only `experiments/bertopic_modeling_2026_08_05/README.md` exists.

## Caller / unit of work

**Main caller:** a `python -c` import check that:

1. Loads `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset`.
2. Joins an `is_unanimous` boolean from `STUDY_PHASE_2_PART_2_RESULTS_FULL` using the frozen unanimous rule below.
3. Resolves experiment output roots for text role `"original"` (v1 only).

**In scope:** `src/__init__.py`, `src/paths.py`, `src/data.py`, four stage stubs, `pyproject.toml` optional-deps entry, README run-order commands.

**Out of scope:** DynamoDB/S3/Bedrock calls, `BERTopic.fit_transform`, OpenAI calls, Plotly figures, `RESULTS.md`, any `tests/` package, mirror role outputs, `export_features.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Spec: layout, params, stage order, unanimous join |
| `/workspace/docs/plans/2026-08-05_bertopic_modeling_83263d/plan.md` | Confirmed file list and happy flow |
| `/workspace/shared/data/dataloader.py` | `load_dataset(name)` |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`, `STUDY_PHASE_2_PART_2_RESULTS_FULL` |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Modal label columns; ~8791 rows |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | Linked-fate trial filter + modal aggregation (reuse filter logic for unanimous counts) |
| `/workspace/pyproject.toml` | Existing `modernbert-training` optional-extra shape to mirror |

## Files allowed to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/src/__init__.py` (create)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` (create)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` (create)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` (create stub)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` (create stub)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py` (create stub)
- `/workspace/experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py` (create stub)
- `/workspace/pyproject.toml` (`[project.optional-dependencies]` only — add `bertopic` extra)
- `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` (append run-order commands only; do not redesign the scientific approach)
- Optional empty dir markers: `outputs/embeddings/original/.gitkeep`, `outputs/topics/original/.gitkeep`, `outputs/labels/original/.gitkeep`, `outputs/figures/original/.gitkeep`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/shared/embeddings/bedrock.py`
- `/workspace/shared/schemas.py`
- Default `dependencies` list and `dependency-groups.dev` in `pyproject.toml` (only add under `[project.optional-dependencies]`)
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- `/workspace/experiments/create_llm_features_2026_08_05/**`
- Do **not** create `experiments/bertopic_modeling_2026_08_05/tests/`
- Do **not** create `RESULTS.md` in this step
- Do **not** create `outputs/**/mirror/` trees in v1

## Contracts to freeze

### Experiment roots (`paths.py`)

```text
EXPERIMENT_ROOT = experiments/bertopic_modeling_2026_08_05/
TEXT_ROLE_V1 = "original"   # mirror is out of scope for v1

embeddings_dir(role) = EXPERIMENT_ROOT / "outputs" / "embeddings" / role
topics_dir(role)     = EXPERIMENT_ROOT / "outputs" / "topics" / role
labels_dir(role)     = EXPERIMENT_ROOT / "outputs" / "labels" / role
figures_dir(role)    = EXPERIMENT_ROOT / "outputs" / "figures" / role
```

`role` must be exactly `"original"` in v1. Raise `ValueError` for `"mirror"` or any other string (mirror support is deferred; do not silently create mirror paths).

UTC run stamps for stages 2–4 use a single format, e.g. `YYYYMMDDTHHMMSSZ` (document the exact format chosen in README). Helper: `new_run_timestamp() -> str`.

### Loader / unanimous join (`data.py`)

Public helpers (names may vary; behavior must match):

1. `load_keep_remove_posts() -> pd.DataFrame`  
   - Calls `load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)`.  
   - Requires columns: `message_id`, `original_text`, `mirror_text`, `decision`, `keep_remove_label`.  
   - Asserts `decision` values ⊆ `{"keep", "remove"}` after normalizing to lowercase stripped strings if needed.  
   - Does **not** re-aggregate modal labels.

2. `UNANIMOUS_RULE_ID = "all_linked_fate_raters_same_decision"`  
   Rule text (must appear verbatim in any run `metadata.json` that uses the flag):

   > Among `STUDY_PHASE_2_PART_2_RESULTS_FULL` rows with `evaluation_mode == "linked_fate"` and `decision ∈ {keep, remove}` and non-empty `post_id`, group by `post_id`. `is_unanimous = True` iff all decisions in the group are identical (`nunique(decision) == 1`). Else `False`. Join to modal labels on `message_id == post_id`.

3. `load_posts_with_unanimous() -> pd.DataFrame`  
   - Starts from `load_keep_remove_posts()`.  
   - Left-joins `is_unanimous: bool` (and optionally `n_raters`, `keep_count`, `remove_count` for provenance).  
   - Every modal `message_id` must receive a non-null `is_unanimous` (inner-join semantics after the filter; raise `ValueError` if any modal row lacks a matching results-full group).  
   - Does **not** filter by keep/remove for the fit corpus — the full modal frame is the clustering population.

### Stage stubs

Each of `load_embeddings.py`, `fit_bertopic.py`, `label_topics_llm.py`, `visualize_clusters.py` must:

- Be importable under `experiments.bertopic_modeling_2026_08_05.src`.
- Expose a `main` / `run_*` entry that raises `NotImplementedError` (or documents “implemented in Step N”).
- Contain **no** live Bedrock / DynamoDB / BERTopic fit / OpenAI / Plotly calls in this step.

### Optional dependency (`pyproject.toml`)

Add under `[project.optional-dependencies]`, mirroring the `modernbert-training` shape:

```toml
bertopic = [
    "bertopic>=0.17.0",
    "openai>=1.0.0",
    "plotly>=5.0.0",
    "kaleido>=0.2.1",
]
```

Rules:

1. Do **not** add `bertopic` / `openai` / `plotly` / `kaleido` to default `dependencies` or `dependency-groups.dev`.
2. Do **not** pin standalone `umap-learn` / `hdbscan` unless `uv sync --extra bertopic` fails without them; prefer bertopic’s transitive deps. If an explicit pin is required after sync failure, add it only under the `bertopic` extra and document the reason in the commit message.
3. Operators install with `uv sync --extra bertopic` and run with `PYTHONPATH=. uv run --extra bertopic python …`.

### README run-order block (append)

```bash
# Install optional BERTopic stack (once per env)
uv sync --extra bertopic

# Stage 1 — Titan cache for original posts (no Bedrock when cache complete)
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py

# Stage 2 — fit BERTopic (no LLM); smoke uses --sample-size 50
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --sample-size 50

# Stage 3 — post-hoc LLM labels (gpt-5.4-nano); skip topic -1
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>

# Stage 4 — three overlays from shared umap_2d.npy
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \
  --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>

# Smoke (Step 6): --sample-size 50, then stop for approval
# Production (Step 7, after approval): omit --sample-size (all original posts)
```

Exact flags finalized in Steps 2–5; this step records order, `--extra bertopic`, smoke size **50**, and production = full corpus.

## Exact commands

```bash
cd /workspace

uv sync --extra bertopic

PYTHONPATH=. uv run --extra bertopic python -c "
from pathlib import Path
from experiments.bertopic_modeling_2026_08_05.src import paths, data

assert paths.TEXT_ROLE_V1 == 'original'
for fn in (paths.embeddings_dir, paths.topics_dir, paths.labels_dir, paths.figures_dir):
    p = fn('original')
    assert isinstance(p, Path)
    assert 'original' in str(p)
try:
    paths.embeddings_dir('mirror')
    raise SystemExit('expected ValueError for mirror in v1')
except ValueError:
    pass

df = data.load_posts_with_unanimous()
assert {'message_id','original_text','decision','is_unanimous'} <= set(df.columns)
assert set(df['decision'].unique()) <= {'keep', 'remove'}
assert df['is_unanimous'].dtype == bool or set(df['is_unanimous'].dropna().unique()) <= {True, False}
assert abs(len(df) - 8791) < 5
assert data.UNANIMOUS_RULE_ID == 'all_linked_fate_raters_same_decision'
print('posts', len(df), 'unanimous', int(df['is_unanimous'].sum()), 'not', int((~df['is_unanimous']).sum()))
print('paths OK')
"

PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_modeling_2026_08_05.src import (
    load_embeddings,
    fit_bertopic,
    label_topics_llm,
    visualize_clusters,
)
print('stubs import OK')
"

# Confirm optional-extra isolation
python -c "
import tomllib
from pathlib import Path
data = tomllib.loads(Path('pyproject.toml').read_text())
extras = data['project']['optional-dependencies']
assert 'bertopic' in extras
deps = set(data['project']['dependencies'])
dev = set(data.get('dependency-groups', {}).get('dev', []))
assert not any('bertopic' in d for d in deps | dev)
print('extra isolation OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Load + join | prints `posts ~8791` and unanimous counts; no null `is_unanimous` | Wrong registry / missing join / KeyError |
| Paths | `paths OK`; `mirror` raises `ValueError` | Silent mirror paths |
| Stubs | `stubs import OK` | ImportError / missing modules |
| Extra | `bertopic` only under optional-dependencies; `extra isolation OK` | bertopic in default/dev deps |
| Sync | `uv sync --extra bertopic` exits 0 | Unresolvable deps |
| Shared isolation | `git diff -- shared/` empty for this step | Diff touches shared |

## Done when

- `src/__init__.py`, `paths.py`, `data.py`, and four stage stubs exist and import.
- Unanimous join implements `all_linked_fate_raters_same_decision` and exposes `UNANIMOUS_RULE_ID`.
- Stage output roots resolve under `outputs/{embeddings,topics,labels,figures}/original/`.
- `pyproject.toml` has optional `bertopic` extra only; `uv sync --extra bertopic` succeeds.
- README documents stage CLI order with `--extra bertopic`, smoke `--sample-size 50`, and production = full corpus.
- No embedding/fit/LLM/viz logic and no shared-library edits.
