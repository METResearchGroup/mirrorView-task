# Step 8: Analysis (error clustering and GEPA criteria mining)

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run.py` `main` (thin orchestrator calling the two analysis modules)
- **Task:** Build `analysis/cluster_errors.py` and `analysis/mine_gepa_criteria.py`. Cluster test-set false positives and false negatives from A1 and B1. Embed with `all-MiniLM-L6-v2` (precomputed, seeded). Run K-means as a baseline, then BERTopic. Cluster original and mirror texts separately. Separate grouping errors from label errors. Spot-check clusters. Split final GEPA prompts (B1, B1-T, B2, B3, B4) into atomic criteria with a conservative hardcoded synonym list. Compare with `KEEP_REMOVE_FEATURES_ADDENDUM`. Run a held-out spot-check. Answer the eight key questions from `plan.md` in `RESULTS.md`. Wandb group `analysis`, `job_type=analyze`. Upload outputs to `analysis/` on S3.
- **Out of scope:** New Jev API calls, re-running GEPA, editing Stage A or B runners.

## Dependencies

- Step 5: `jev_baseline/outputs/A1_pair_study_prompt/labels.parquet` (filter `split == "test"` for clustering)
- Step 7: `jev_gepa/outputs/B1_gepa_pair/test_eval/` and `final_prompt.txt` for B1 through B4 and B1-T
- Lab wiki manuals (read-only): `HOW_TO_CLUSTER_TEXT.md`, `HOW_TO_MINE_TEXT_FOR_FEATURES.md`

## Dependency check (`pyproject.toml`)

Before adding packages, inspect `/workspace/pyproject.toml`:

| Package | Status in repo (2026-09-24) | Action |
|---------|----------------------------|--------|
| `scikit-learn` | Present in `[dependency-groups] dev` | Use as-is via `uv run` |
| `bertopic` | Present in `[project.optional-dependencies] bertopic` | Install with `uv sync --extra bertopic` if not already synced |
| `sentence-transformers` | **Not present** | Add to `[project.optional-dependencies] analysis` (or extend `bertopic` extra) in this step only if import fails |

Do not add `sentence-transformers` if another installed package already provides `all-MiniLM-L6-v2` loading. Verify with:

```bash
PYTHONPATH=. uv run python -c "from sentence_transformers import SentenceTransformer; print('ok')"
```

If that fails, add `sentence-transformers>=3.0.0` to `pyproject.toml` and run `uv lock && uv sync --extra bertopic`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md` | Eight key questions |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Analysis inputs, embedding model, wiki links |
| `HOW_TO_CLUSTER_TEXT.md` (lab_wiki) | K-means baseline then BERTopic, MiniLM default |
| `HOW_TO_MINE_TEXT_FOR_FEATURES.md` (lab_wiki) | Atomic criteria, conservative synonyms, avoid TF-IDF for feature frequency |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | `KEEP_REMOVE_FEATURES_ADDENDUM` ground truth |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/outputs/A1_pair_study_prompt/labels.parquet` | A1 test errors |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/B1_gepa_pair/test_eval/labels.parquet` | B1 test errors |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/cluster_errors.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/mine_gepa_criteria.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/synonyms.py` (new, conservative hardcoded synonym map)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/tests/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/tests/test_cluster_errors.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/tests/test_mine_gepa_criteria.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` (append analysis answers section)
- `/workspace/pyproject.toml` (only if `sentence-transformers` import check fails)
- `/workspace/uv.lock` (only when `pyproject.toml` changes)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/**` (except reading)
- `/workspace/webapp/**`

## Contracts

### Error extraction inputs

Read test split only (`split == "test"` from labels.parquet). Use columns `keep_remove_label`, `predicted_label`, `p_remove`, `sample_toxicity_type`, `remove_share`. Error types:

| `error_type` | Rule (threshold 0.5) |
|--------------|----------------------|
| `false_negative` | `keep_remove_label == 1` and `predicted_label == 0` |
| `false_positive` | `keep_remove_label == 0` and `predicted_label == 1` |

Sources:

| `model_id` | Labels path |
|------------|-------------|
| `A1` | `jev_baseline/outputs/A1_pair_study_prompt/labels.parquet` |
| `B1` | `jev_gepa/outputs/B1_gepa_pair/test_eval/labels.parquet` |

### `analysis/cluster_errors.py`

```python
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_SEED = 20260924

@dataclass(frozen=True)
class ErrorRecord:
    post_id: str
    model_id: str  # A1 or B1
    error_type: str  # false_positive or false_negative
    text_role: str  # original or mirror
    text: str
    sampled_stance: str
    sample_toxicity_type: str
    p_remove: float
    remove_share: float

def extract_errors(labels_path: Path, model_id: str) -> list[ErrorRecord]:
    """Return FN and FP rows for test split; one ErrorRecord per (post, text_role)."""

def precompute_embeddings(
    texts: list[str],
    *,
    model_name: str = EMBEDDING_MODEL,
    seed: int = EMBEDDING_SEED,
    cache_path: Path,
) -> np.ndarray:
    """Write embeddings to cache_path (npy). Reuse cache when present and hash matches."""

def kmeans_baseline(
    embeddings: np.ndarray,
    *,
    n_clusters: int,
    seed: int = EMBEDDING_SEED,
) -> np.ndarray:
    """Return cluster labels."""

def run_bertopic(
    texts: list[str],
    embeddings: np.ndarray,
    *,
    seed: int = EMBEDDING_SEED,
) -> pd.DataFrame:
    """Return topic table with topic id, representative terms, and post_id mapping."""

def classify_error_kind(record: ErrorRecord) -> str:
    """
    Return grouping_error or label_error.
    grouping_error: model likely confused by pair framing or the wrong text view.
    label_error: model saw the relevant text but disagreed with the majority label.
    Codify the heuristic in tests; do not leave it as undocumented judgment.
    """

def spot_check_table(cluster_df: pd.DataFrame, n_per_topic: int = 3) -> pd.DataFrame:
    """Sample post ids and texts for manual review."""

def run_cluster_analysis(
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """
    For A1 and B1 separately:
      - extract FN/FP on test
      - cluster original texts and mirror texts separately
      - K-means with k in {5, 10} as baseline
      - BERTopic on same embeddings
      - write cluster_assignments.parquet, topic_summary.json, spot_checks.csv
    """
```

Output layout:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/outputs/cluster_errors/
  A1/
    original/
    mirror/
  B1/
    original/
    mirror/
  embeddings_cache/
```

### `analysis/mine_gepa_criteria.py`

```python
ABLATION_PROMPT_PATHS: dict[str, Path]  # keys: B1_gepa_pair, B1T_gepa_pair_terra, B2_gepa_original, B3_gepa_mirror, B4_gepa_asymmetric_reward

def split_into_atomic_criteria(prompt_text: str) -> list[str]:
    """
    Split on numbered lists, bullets, and newlines.
    Drop fragments shorter than 8 characters after strip.
    """

def normalize_criterion(text: str, synonyms: dict[str, str]) -> str:
    """Lowercase, strip, apply conservative hardcoded synonym merges from synonyms.py."""

def load_human_mined_criteria() -> list[str]:
    """Parse KEEP_REMOVE_FEATURES_ADDENDUM from llm_prompt_engineering prompt.py into atomic strings."""

def compare_criteria(
    gepa_criteria: list[str],
    human_criteria: list[str],
    *,
    synonyms: dict[str, str],
) -> pd.DataFrame:
    """
    Columns: gepa_criterion, best_human_match, exact_or_synonym_match (bool), notes.
    Use conservative matching only (no fuzzy LLM match at runtime).
    """

def held_out_spot_check(
    gepa_criteria: list[str],
    *,
    holdout_fraction: float = 0.2,
    seed: int = 20260924,
) -> pd.DataFrame:
    """Reserve 20% of criteria strings; document manual review rows in spot_check.csv."""

def run_criteria_mining(*, output_dir: Path) -> dict[str, Any]:
    """Process B1_gepa_pair, B1T_gepa_pair_terra (ablation id B1-T), B2_gepa_original, B3_gepa_mirror, B4_gepa_asymmetric_reward; write criteria tables and comparison summary."""
```

### `analysis/synonyms.py`

Conservative hardcoded map (example entries, extend in implementation):

```python
SYNONYM_MAP: dict[str, str] = {
    "vulgar": "profanity",
    "slur": "profanity",
    "insult": "derisive ridicule",
    # err on the side of NOT merging near-synonyms
}
```

### `analysis/run.py`

```python
def main(argv: list[str] | None = None) -> None:
    """
    1. run_cluster_analysis
    2. run_criteria_mining
    3. write_analysis_summary_json
    4. append RESULTS.md analysis section (eight questions)
    5. Wandb: group analysis, job_type analyze
    6. S3 upload under analysis/
    """
```

## Tests to write first

### `analysis/tests/test_cluster_errors.py`

Class `TestExtractErrors`, `TestClassifyErrorKind`, `TestKmeansBaseline`.

```text
given labels.parquet with test split containing one FN and one FP at threshold 0.5
when extract_errors for A1
then four ErrorRecords return (FN and FP times original and mirror text roles)

given identical texts and embeddings with seed 20260924
when kmeans_baseline twice
then cluster labels are identical

given a record where p_remove is high but gold is keep on mirror-only clustering arm
when classify_error_kind with documented heuristic
then label_error is returned

given embeddings cached on disk with matching hash
when precompute_embeddings called again
then no recomputation (mtime unchanged or log line says cache hit)
```

Use tiny synthetic `labels.parquet` fixtures in `conftest.py`. Do not download MiniLM weights in unit tests (mock `SentenceTransformer`).

### `analysis/tests/test_mine_gepa_criteria.py`

Class `TestSplitAtomicCriteria`, `TestNormalizeCriterion`, `TestCompareCriteria`.

```text
given a prompt with two numbered criteria items
when split_into_atomic_criteria
then two strings are returned

given normalize_criterion with synonym vulgar to profanity
when input contains Vulgar
then normalized string uses profanity token

given one GEPA criterion that exactly matches a human-mined line after normalization
when compare_criteria
then exact_or_synonym_match is True for that row

given 10 criteria and holdout_fraction 0.2 seed 20260924
when held_out_spot_check
then holdout set size is 2 and is disjoint from mining set
```

## Implementation order

One Git commit per unit. Full auto.

1. Verify or add `sentence-transformers` dependency.
2. Scaffold `analysis/` modules, `synonyms.py`, and tests.
3. Implement `extract_errors` and `classify_error_kind` until tests pass.
4. Implement embedding cache and `kmeans_baseline` with mocked embeddings in tests.
5. Implement `run_bertopic` (skip BERTopic in unit tests; smoke with 20 texts in integration).
6. Implement `run_cluster_analysis` orchestration.
7. Implement `split_into_atomic_criteria`, `normalize_criterion`, `load_human_mined_criteria`.
8. Implement `compare_criteria` and `held_out_spot_check`.
9. Implement `run_criteria_mining` and `run.py` main.
10. Run full analysis, upload S3, append RESULTS.md answers.

## Commands

Unit tests:

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/tests -q
```

Expected: exit 0 without downloading models (mocked).

Install analysis extras (if needed):

```bash
uv sync --extra bertopic
PYTHONPATH=. uv run python -c "from sentence_transformers import SentenceTransformer; print(SentenceTransformer('all-MiniLM-L6-v2').get_sentence_embedding_dimension())"
```

Expected: prints `384`.

Full analysis run:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run.py
```

Expected stdout ends with:

```text
cluster_errors_written=4  # A1/B1 x original/mirror
criteria_ablations=5
wandb_group=analysis job_type=analyze
results_section=appended
```

S3 upload:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import upload_under_prefix
prefix = 'experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/'
root = Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/outputs')
for path in root.rglob('*'):
    if path.is_file():
        upload_under_prefix(path, prefix)
print('uploaded analysis outputs')
"
```

Expected: objects under `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/`.

## RESULTS.md analysis template (eight key questions)

Append section answering each question from `plan.md` with pointers to tables above and analysis outputs.

```markdown
## Analysis

### Q1. Jev baseline vs trivial baselines
A1 test F1 **0.0000** beats keep-all (**0.0000**), remove-all (**0.0000**), and prevalence-random (**0.0000**). See Stage A table.

### Q2. GEPA improvement and cost
B1 test F1 **0.0000** vs A1 **0.0000** (delta **0.0000**). B1-T test F1 **0.0000** at reflection cost **$0.00** vs B1 **$0.00**. See Stage B and spend table.

### Q3. Which text carries signal (pair vs original vs mirror)
| Arm | Test F1 |
| --- | --- |
| A1 pair | 0.0000 |
| A2 original | 0.0000 |
| A3 mirror | 0.0000 |
| B2 original-trained | 0.0000 |
| B3 mirror-trained | 0.0000 |
Transfer: B1 on original **0.0000**, B1 on mirror **0.0000**.

### Q4. Errors by stance and toxicity
See Stage A subgroup tables for A1 (`analysis/outputs/cluster_errors/` summarizes concentration).

### Q5. P(remove) vs human disagreement
Spearman rho on full cohort: A1 **0.0000** (see Stage A).

### Q6. GEPA prompt transfer across views
See Stage B transfer table.

### Q7. GEPA criteria vs human-mined criteria
`analysis/outputs/criteria/comparison_summary.csv`: **N** GEPA atomic criteria, **M** matched to `KEEP_REMOVE_FEATURES_ADDENDUM` by conservative synonym rules, **K** novel.

### Q8. Latency percentiles (batch 10)
A1 per-request p50 **0.0** ms, p90 **0.0** ms, p99 **0.0** ms; per-post p50 **0.0** ms (Stage A latency table).

### Error clustering summary
K-means and BERTopic top topics for A1 and B1 FN/FP on original and mirror texts: see `analysis/outputs/cluster_errors/**/topic_summary.json` and `spot_checks.csv`.
```

## Must pass

- Test-set errors only (no dev or GEPA pool rows in clustering).
- Original and mirror clustered separately for each model (A1, B1).
- K-means runs before BERTopic on the same embeddings.
- Grouping vs label error classification is explicit and tested.
- Five GEPA final prompts mined; comparison uses `KEEP_REMOVE_FEATURES_ADDENDUM`.
- Held-out 20% spot-check file exists.
- Eight questions answered in `RESULTS.md`.
- Wandb run with group `analysis`, `job_type=analyze`.
- S3 `analysis/` prefix populated.
- Unit tests pass without network.

## Must fail

- Re-scoring posts with Jev in analysis scripts.
- Clustering train or dev splits.
- Using TF-IDF instead of embedding clustering for the primary pipeline.
- Aggressive synonym merging without entries in `synonyms.py`.
- Adding `sentence-transformers` when import already succeeds.
- Editing frozen Stage A or B label files.

## Commit messages

1. `feat(jev-gepa): scaffold analysis runners and synonym map`
2. `feat(jev-gepa): extract test-set errors for A1 and B1`
3. `feat(jev-gepa): add MiniLM embedding cache and K-means baseline`
4. `feat(jev-gepa): add BERTopic clustering for error texts`
5. `feat(jev-gepa): classify grouping vs label errors`
6. `feat(jev-gepa): mine atomic criteria from GEPA prompts`
7. `feat(jev-gepa): compare GEPA criteria to human-mined addendum`
8. `docs(jev-gepa): answer eight key questions in RESULTS.md`
9. `chore(jev-gepa): add sentence-transformers optional dep` (only if import check failed)

## Implement-from-spec notes

Phase 1 names `analysis/run.py` `main` as the caller. Phase 2 scaffolds analysis modules and tests. Phase 3 locks dataclasses and function signatures. Phase 4 writes analysis tests with mocks for embeddings and BERTopic. Phase 5 builds cluster_errors, then mine_gepa_criteria, then the orchestrator. Phase 6 is complete when analysis outputs exist on S3, the RESULTS.md analysis section is filled, and pytest exits 0.
