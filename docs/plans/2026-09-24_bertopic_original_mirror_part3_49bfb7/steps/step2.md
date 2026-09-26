# Step 2: Scaffold experiment and port Part 2 pipeline

## Goal

Create `experiments/bertopic_original_mirror_part3_2026_09_24/` with README (1 to 2 lines pointing to SETUP.md and RESULTS.md), SETUP.md (required data), and RESULTS.md stub. Copy Part 2 stage scripts from `experiments/bertopic_modeling_2026_08_05/src/` into `src/` with dataset and text role (`original` | `mirror` | `joint`) as CLI inputs. Add `dedupe.py` with the approved dedupe rule (before fit, not in this step). Add unit tests for pure helpers (`paths`, `dedupe`, text-role selection). Leave `experiments/bertopic_modeling_2026_08_05/` untouched.

## Caller / unit of work

**Main caller (import + dedupe smoke):**

```bash
PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths, data, dedupe
from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import load_stimuli_posts
from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import dedupe_stimuli, build_dedupe_report

stim = load_stimuli_posts()
deduped, report = dedupe_stimuli(stim)
assert len(stim) == 18899
assert report['n_after_dedupe'] == 18698
assert paths.embeddings_dir('original').name == 'original'
print('scaffold OK', report['n_removed_duplicate_original'], report['n_removed_identical_pair'])
"
```

**In scope:** New experiment folder, ported stubs, `dedupe.py`, `data.py`, `paths.py`, docs, tests.

**Out of scope:** Embedding resolution, BERTopic fit, LLM labeling, visualization logic, edits to Part 2 experiment, S3 upload.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/paths.py` | Path helper pattern |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/data.py` | Loader / join patterns |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/load_embeddings.py` | Stage stub shape |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | Stage stub shape |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py` | Stage stub shape |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py` | Stage stub shape |
| `/workspace/experiments/bertopic_modeling_2026_08_05/README.md` | Hyperparameters and stage order |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_3_STIMULI`, `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` |
| `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md` | Dedupe decision; fit vs outcome corpora |

**Verified dedupe counts on live stimuli (stable sort by `post_id` ascending):**

| Step | Rows removed | Rows remaining |
|------|--------------|----------------|
| Start | 0 | 18,899 |
| Drop duplicate `original_text` (keep first by `post_id`) | 173 | 18,726 |
| Drop rows where `original_text == mirror_text` | 28 | 18,698 |

(35 identical pairs exist in raw stimuli; 7 are already removed by duplicate-original dedupe.)

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/SETUP.md` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md` (create stub)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/__init__.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/paths.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/data.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/dedupe.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py` (create; copy stub from Part 2, retarget imports)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings_minilm.py` (create stub only; implemented in Step 3)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py` (create stub)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/label_topics_llm.py` (create stub)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/visualize_clusters.py` (create stub)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_paths.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_dedupe.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_text_role.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/conftest.py` (create if needed)
- Optional empty dir markers: `outputs/embeddings/original/.gitkeep`, `outputs/embeddings/mirror/.gitkeep`

## Files forbidden to change

- `/workspace/experiments/bertopic_modeling_2026_08_05/**` (read-only reference)
- `/workspace/shared/**` (except reading registry; Step 1 owns transform changes)
- `/workspace/pyproject.toml`
- `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md`
- Any other file

## Implementation details

### Docs

**`README.md`** (1-2 lines only):

```markdown
# BERTopic original and mirror (Part 3)

See [SETUP.md](SETUP.md) for required data. Results: [RESULTS.md](RESULTS.md).
```

**`SETUP.md`** must list:

- `STUDY_PHASE_2_PART_3_STIMULI` (18,899 posts; `post_primary_key`, `original_text`, `mirrored_text`)
- `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` (18,866 rated posts; outcome overlays only)
- `STUDY_PHASE_2_PART_3_RESULTS_FULL` (rater-party cuts in later steps)
- `uv sync --extra bertopic`
- AWS export for embedding backfill (Step 3): `export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"; export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"`
- Large artifacts (`embeddings.npy`, BERTopic `model/` dirs, `umap_2d.npy`) are gitignored and S3-primary under `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/` (same relative paths). Small artifacts stay in git.

**`RESULTS.md`** stub:

```markdown
# Results

TBD after production runs (Step 8).
```

### `paths.py`

```text
EXPERIMENT_ROOT = experiments/bertopic_original_mirror_part3_2026_09_24/
ALLOWED_TEXT_ROLES = {"original", "mirror", "joint"}

embeddings_dir(role)       -> outputs/embeddings/<role>/
embeddings_minilm_dir(role)-> outputs/embeddings_minilm/<role>/
topics_dir(role)           -> outputs/topics/<role>/
labels_dir(role)           -> outputs/labels/<role>/
figures_dir(role)          -> outputs/figures/<role>/
analyses_dir()             -> outputs/analyses/
ablations_dir()            -> outputs/ablations/
dedupe_report_path()       -> outputs/dedupe_report.json

new_run_timestamp() -> UTC format %Y%m%dT%H%M%SZ
```

Raise `ValueError` for roles outside `ALLOWED_TEXT_ROLES`.

### `data.py`

| Function | Behavior |
|----------|----------|
| `POST_ID_COLUMN = "post_id"` | Standard id column name in experiment frames |
| `load_stimuli_posts() -> pd.DataFrame` | Load `STUDY_PHASE_2_PART_3_STIMULI`; rename `post_primary_key` to `post_id` (stripped str); rename `mirrored_text` to `mirror_text`; derive `platform` |
| `load_keep_remove_posts() -> pd.DataFrame` | Load `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS`; validate required columns including `is_unanimous` (nullable bool) |
| `select_text_column(role: str) -> str` | `"original"` -> `"original_text"`; `"mirror"` -> `"mirror_text"`; `"joint"` -> raise `ValueError` (joint handled separately) |
| `texts_for_role(frame: pd.DataFrame, role: str) -> list[str]` | Return text list for `original` or `mirror` |
| `build_joint_frame(deduped: pd.DataFrame) -> pd.DataFrame` | Two rows per post: columns `post_id`, `text`, `text_role` (`original` or `mirror`), `pair_post_id` (= `post_id`) |
| `load_fit_corpus(role: str) -> pd.DataFrame` | `load_stimuli_posts()` then `dedupe_stimuli()`; for `joint`, return `build_joint_frame` output; else return deduped with `text` column added |

Outcome overlays use `load_keep_remove_posts()` (18,866 rated posts). Fit corpus uses deduped stimuli (18,698 posts for original/mirror; 37,396 rows for joint).

### `dedupe.py`

| Function | Behavior |
|----------|----------|
| `dedupe_stimuli(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]` | Sort by `post_id` ascending. Step 1: `drop_duplicates(subset=["original_text"], keep="first")`. Step 2: drop rows where `original_text == mirror_text`. Return deduped frame + report dict |
| `build_dedupe_report(before: pd.DataFrame, after: pd.DataFrame, removed_dup_orig: int, removed_identical: int) -> dict` | See schema below |
| `write_dedupe_report(path: Path, report: dict) -> None` | Write JSON |

**`dedupe_report.json` schema** (written to `outputs/dedupe_report.json` when `write_dedupe_report` is called from a future fit stage; Step 2 must produce the report dict via tests and expose `write_dedupe_report`):

```json
{
  "n_stimuli_raw": 18899,
  "n_removed_duplicate_original": 173,
  "n_removed_identical_pair": 28,
  "n_after_dedupe": 18698,
  "dedupe_rule_duplicate_original": "drop_duplicates on original_text keep first by post_id ascending",
  "dedupe_rule_identical_pair": "drop rows where original_text == mirror_text"
}
```

### Stage stubs

Copy from Part 2 and retarget package imports to `experiments.bertopic_original_mirror_part3_2026_09_24.src`. Each stage exposes `main()` raising `NotImplementedError("implemented in Step N")` with a docstring naming the target step:

| Module | Stub note |
|--------|-----------|
| `load_embeddings.py` | Step 3 |
| `load_embeddings_minilm.py` | Step 3 |
| `fit_bertopic.py` | Step 4 |
| `label_topics_llm.py` | Step 4 |
| `visualize_clusters.py` | Step 4 |

Add argparse placeholders: `--text-role {original,mirror,joint}` on fit/label/viz stubs; `--text-role {original,mirror}` on embedding stubs.

### `.gitignore` (S3-primary large artifacts)

Create `experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore`:

```gitignore
# Identity-cache download scratch (local only)
outputs/embeddings/.identity_disk_cache/

# S3-primary large artifacts (same relative paths under mirrorview-experimental-artifacts)
outputs/embeddings/**/embeddings.npy
outputs/embeddings_minilm/**/embeddings.npy
outputs/topics/**/model/
outputs/topics/**/umap_2d.npy
```

Keep these in git: `index.parquet`, `metadata.json`, `dedupe_report.json`, `assignments.parquet`, `topic_info.parquet`, label tables, analysis CSV/parquet/json, `summary.json`, and figure PNGs.

S3 bucket: `mirrorview-experimental-artifacts`  
S3 prefix: `experiments/bertopic_original_mirror_part3_2026_09_24/`

## TDD tests to write first

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_paths.py`

| Test name | Assert |
|-----------|--------|
| `test_embeddings_dir_original` | Path ends with `outputs/embeddings/original` |
| `test_embeddings_minilm_dir_mirror` | Path ends with `outputs/embeddings_minilm/mirror` |
| `test_invalid_role_raises` | `embeddings_dir("bogus")` raises `ValueError` |
| `test_joint_role_allowed_for_topics_dir` | `topics_dir("joint")` resolves without error |

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_dedupe.py`

| Test name | Given | Assert |
|-----------|-------|--------|
| `test_dedupe_removes_duplicate_original_keeps_lowest_post_id` | Two rows, same `original_text`, post_ids `b` and `a` | Keeps `a` after sort |
| `test_dedupe_removes_identical_pair` | `original_text == mirror_text` | Row dropped |
| `test_dedupe_report_counts` | 3-row synthetic fixture | Report keys match schema |
| `test_live_stimuli_counts` | Real `load_stimuli_posts()` | `n_after_dedupe == 18698`, `n_removed_duplicate_original == 173`, `n_removed_identical_pair == 28` |

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_text_role.py`

| Test name | Assert |
|-----------|--------|
| `test_texts_for_role_original` | Returns `original_text` values |
| `test_texts_for_role_mirror` | Returns `mirror_text` values |
| `test_build_joint_frame_doubles_rows` | Deduped 2-row fixture yields 4 rows with `text_role` in `{"original","mirror"}` |
| `test_load_fit_corpus_original_row_count` | `len(load_fit_corpus("original")) == 18698` |

## Exact commands

```bash
cd /workspace
uv sync --extra bertopic

# Tests first (expect FAIL)
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/ -v

# Scaffold import check (after implementation)
PYTHONPATH=. uv run --extra bertopic python -c "
from experiments.bertopic_original_mirror_part3_2026_09_24.src import (
    paths, data, dedupe, load_embeddings, load_embeddings_minilm,
    fit_bertopic, label_topics_llm, visualize_clusters,
)
print('imports OK')
"

# Confirm Part 2 untouched
git diff -- experiments/bertopic_modeling_2026_08_05/

# Tests (expect PASS)
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/ -v
```

Expected pytest tail:

```text
====== N passed in X.XXs ======
```

Expected `git diff` on Part 2: empty.

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Part 2 isolation | No diff under `experiments/bertopic_modeling_2026_08_05/` | Any change |
| Roles | `original`, `mirror`, `joint` supported in paths/data | Missing joint |
| Dedupe | Live counts 18899 -> 18698 | Wrong counts or order-dependent dedupe |
| Stubs | All stage modules import; bodies raise `NotImplementedError` | Live AWS/BERTopic calls |
| Tests | All tests green | Any failure |
| Docs | README 1 to 2 lines; SETUP lists Part 3 datasets | Missing SETUP |

## Commit message(s)

```
Scaffold Part 3 BERTopic experiment with dedupe helpers

Copy Part 2 stage stubs into bertopic_original_mirror_part3_2026_09_24,
add paths/data/dedupe modules with original|mirror|joint roles, docs,
and unit tests. Part 2 experiment folder unchanged.
```
