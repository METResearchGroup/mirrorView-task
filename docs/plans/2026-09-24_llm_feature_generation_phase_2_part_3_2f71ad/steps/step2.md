# Step 2: Naive baselines per text arm on discovery posts

Step 2 runs on discovery-split posts only. Compute document-frequency unigrams and bigrams separately for keep versus remove (not TF-IDF), embed posts with Titan, and run K-Means with k=2 through 10 for each of three random seeds (42, 43, 44). Run once per text arm (`original_only`, `mirror_only`, `paired`), and upload outputs to S3.

## Scope

- **Caller / entrypoint:** `experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines` CLI (`if __name__ == "__main__"`).
- **In scope:** `baselines.py`, `tests/test_baselines.py`, baseline outputs under `outputs/<arm>/baselines/<run_timestamp>/`, S3 upload via existing `s3_sync.py`.
- **Out of scope:** LLM feature generation, embedding generated features (Step 4), edits to `cohort.py`, `split.py`, `s3_sync.py`, or any Step 3 plus modules.

## Files to inspect (read-only)

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/cohort.py`: cohort parquet schema and text columns (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/paths.py`: `baselines_dir`, `make_run_timestamp`, `post_split_dir`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/constants.py`: `TEXT_ARMS`, `CLUSTER_SEEDS`, `DEFAULT_SEED`, `EMBEDDING_MODEL_ID`, `EMBEDDING_DIM`, `S3_*`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/discovery_post_ids.csv`: discovery post IDs from Step 1.
- `shared/embeddings/bedrock.py`: `create_embedding(text, normalize=True)`; 256-d L2-normalized vectors.
- [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md): lemmatize with spaCy `en_core_web_sm`, remove stopwords, document frequency (not TF-IDF), experiment-specific noisy word stoplist.
- `experiments/create_llm_features_2026_08_05/src/cluster_embeddings.py`: `select_k_silhouette` and `k_selection.json` shape (adapt for post-level K-Means baseline).
- `experiments/create_llm_features_2026_08_05/src/generate_embeddings.py`: `_make_run_timestamp()` pattern (`%Y-%m-%dT%H-%M-%S`).

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/baselines.py`: baseline CLI and logic.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_baselines.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/<arm>/baselines/<run_timestamp>/`: gitignored outputs.

## Files forbidden to change

- `shared/` (read only)
- Other `experiments/*`
- Step 1 modules except reading: `cohort.py`, `split.py`, `s3_sync.py` (call only; do not edit)
- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md` and sibling step files except this file
- Any Step 3 through 7 modules

## Implementation phases (TDD: mandatory order)

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Name caller, inputs, outputs | CLI flags and output tree listed |
| 2: Scaffold | Create `baselines.py` with stubs | Import resolves; `raise NotImplementedError` |
| 3: Contracts | Function signatures and output schemas | Matches Artifact contract below; stubs only |
| 4: Test design | Failing tests with mocks for Bedrock | Tests fail for the right reason |
| 5: Implement | One unit per commit until green | Targeted tests pass |
| 6: Done | CLI smoke per arm plus pytest | Pass/fail criteria met |

### Phase 4: Named test cases

**`test_baselines.py`**

| Test | Asserts |
|------|---------|
| `test_load_discovery_posts_filters_split` | Given cohort fixture, loader keeps only `post_id` in `discovery_post_ids.csv` and `split=="discovery"`. |
| `test_arm_original_only_uses_original_text` | Text extraction for `original_only` equals `original_text` column only. |
| `test_arm_mirror_only_uses_mirror_text` | Text extraction for `mirror_only` equals `mirror_text` column only. |
| `test_arm_paired_concatenates_texts` | `paired` joins `original_text` and `mirror_text` with `"\n\n"` separator. |
| `test_docfreq_not_tfidf` | Term score equals document count (number of posts containing term), not TF-IDF weight. |
| `test_docfreq_separates_keep_and_remove` | Keep and remove document sets are disjoint filters on `modal_decision`. |
| `test_tokenizer_lemmatizes_and_drops_stopwords` | Tokens `"running"`, `"The"`, `"thinking"` map/strip per preprocessing rules. |
| `test_bigrams_are_adjacent_lemma_pairs` | `"free speech"` counted as bigram only when adjacent after tokenization. |
| `test_kmeans_sweep_k_two_through_ten` | `k_selection.json` rows include k=2..10 exactly nine entries per seed. |
| `test_three_seeds_written` | Output dirs `kmeans/seed_42`, `seed_43`, `seed_44` each contain assignments. |
| `test_post_embeddings_shape` | `post_embeddings.npy` shape `(n_discovery_posts, 256)` aligned with `post_ids.json`. |
| `test_metadata_records_arm_and_split` | `metadata.json` includes `arm`, `split`, `seeds`, `n_posts`. |
| `test_cli_requires_arm_and_split_discovery` | Missing `--arm` exits non-zero. |
| `test_bedrock_called_once_per_post` | Mock `create_embedding`; call count equals number of discovery posts (integration or mocked). |

Use pytest fixtures with small synthetic cohorts for unit tests; mark optional full-data smoke test `@pytest.mark.integration`.

## Pass / fail criteria

### Must pass

- For each arm in `TEXT_ARMS`, the CLI with `--split discovery` writes a timestamped output directory under `outputs/<arm>/baselines/<run_timestamp>/`.
- Document-frequency outputs list unigrams and bigrams separately for keep-labeled versus remove-labeled discovery posts, filtered by `modal_decision`.
- Post embeddings use `shared.embeddings.bedrock.create_embedding` with `EMBEDDING_MODEL_ID`, `EMBEDDING_DIM=256`, `EMBEDDING_NORMALIZE=True` from constants.
- K-Means runs for k=2..10 (nine k values) for each seed in `CLUSTER_SEEDS` (42, 43, 44).
- `s3_sync.py --paths outputs/original_only/baselines outputs/mirror_only/baselines outputs/paired/baselines` uploads baseline trees.
- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_baselines.py -q` exits 0.

### Must fail (until implemented)

- CLI with `--split test` exits with error (baselines are discovery-only by design).
- Doc-frequency test fails if implementation uses TF-IDF or combines keep/remove into one list.
- K-Means test fails if only a single k or single seed is written.

## Commands (exact)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for ARM in original_only mirror_only paired; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines \
    --arm "$ARM" \
    --split discovery \
    --seed 42
done

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \
  --paths outputs/original_only/baselines outputs/mirror_only/baselines outputs/paired/baselines

PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_baselines.py -q
```

### Expected output (representative lines)

```
arm=original_only split=discovery n_posts=9449 docfreq_terms=... kmeans_k_values=9 kmeans_seeds=42,43,44
Wrote outputs/original_only/baselines/2026-09-24T12-34-56/
arm=mirror_only split=discovery n_posts=9449 docfreq_terms=... kmeans_k_values=9 kmeans_seeds=42,43,44
Wrote outputs/mirror_only/baselines/2026-09-24T12-34-56/
arm=paired split=discovery n_posts=9449 docfreq_terms=... kmeans_k_values=9 kmeans_seeds=42,43,44
Wrote outputs/paired/baselines/2026-09-24T12-34-56/
s3_uploaded_prefix=s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/
```

## Artifact contract (this step's outputs)

### Output root

`outputs/<arm>/baselines/<run_timestamp>/` where `<run_timestamp>` is local `%Y-%m-%dT%H-%M-%S`.

### Directory layout

```text
outputs/<arm>/baselines/<run_timestamp>/
  docfreq_keep_unigrams.json
  docfreq_remove_unigrams.json
  docfreq_keep_bigrams.json
  docfreq_remove_bigrams.json
  post_ids.json
  post_embeddings.npy
  kmeans/
    seed_42/
      k_selection.json
      assignments_kmeans.json
    seed_43/
      k_selection.json
      assignments_kmeans.json
    seed_44/
      k_selection.json
      assignments_kmeans.json
  metadata.json
```

### Document-frequency JSON (each of the four docfreq files)

Sorted list of objects (descending by `doc_count`):

| Field | Type | Notes |
|-------|------|-------|
| `term` | str | Lemmatized unigram or bigram joined with space |
| `doc_count` | int | Number of discovery posts in the class containing the term at least once |
| `n_docs` | int | Total discovery posts in the class (keep or remove) |

**Preprocessing rules (from [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md)):**

1. Lowercase; strip punctuation to spaces.
2. Tokenize; lemmatize with spaCy `en_core_web_sm` (add to experiment SETUP.md if model download required).
3. Remove NLTK English stopwords plus experiment-specific noisy word stoplist: `thinking`, `keeping`, `deciding`, `response`, `post`, `content`, `comment` (extend if needed; keep list in `baselines.py`).
4. Drop unigrams with length `< 2`.
5. Build bigrams from adjacent lemmatized tokens after stopword removal.
6. Score by document frequency only (count posts where term appears); do not use TF-IDF.

### Post embeddings

| File | Schema |
|------|--------|
| `post_ids.json` | `list[str]` length `n_posts` |
| `post_embeddings.npy` | `float32` array shape `(n_posts, 256)`; row order matches `post_ids.json` |

Embed the arm-specific text surface:

| Arm | Text embedded |
|-----|----------------|
| `original_only` | `original_text` |
| `mirror_only` | `mirror_text` |
| `paired` | `original_text + "\n\n" + mirror_text` |

### K-Means baseline (`kmeans/seed_<seed>/`)

Run K-Means on `post_embeddings.npy`. No additional scaling is required because the vectors are L2-normalized. You may add StandardScaler for parity with the feature clustering reference.

**`k_selection.json`**

```json
{
  "seed": 42,
  "k_min": 2,
  "k_max": 10,
  "rows": [
    {"k": 2, "inertia": 0.0, "silhouette": 0.0},
    {"k": 3, "inertia": 0.0, "silhouette": 0.0}
  ],
  "selected_k": 8,
  "selection_method": "silhouette_max"
}
```

Nine rows for k=2..10. `selected_k` is the k with maximum silhouette (tie-break to smaller k).

**`assignments_kmeans.json`**

```json
{
  "selected_k": 8,
  "assignments": {"<post_id>": 3, "...": 1}
}
```

Cluster ids are integers `0 .. selected_k-1`.

Repeat for each seed in `CLUSTER_SEEDS` (`42`, `43`, `44`). The CLI flag `--seed` sets the random state for silhouette subsampling and any shuffling. Still write all three seed subfolders on each run.

### `metadata.json`

```json
{
  "arm": "original_only",
  "split": "discovery",
  "run_timestamp": "2026-09-24T12-34-56",
  "n_posts": 9449,
  "n_keep": 0,
  "n_remove": 0,
  "bedrock_model_id": "amazon.titan-embed-text-v2:0",
  "embedding_dimensions": 256,
  "embedding_normalize": true,
  "kmeans_k_values": [2, 3, 4, 5, 6, 7, 8, 9, 10],
  "kmeans_seeds": [42, 43, 44],
  "discovery_post_ids_path": "data/post_split/discovery_post_ids.csv",
  "cohort_source_glob": "outputs/original_only/cohort/*/cohort.parquet"
}
```

Fill `n_keep` / `n_remove` from discovery subset counts.

### `baselines.py` CLI

```
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.baselines \
  --arm {original_only|mirror_only|paired} \
  --split discovery \
  [--seed 42] \
  [--cohort-run-dir PATH] \
  [--max-posts N]
```

| Flag | Required | Notes |
|------|----------|-------|
| `--arm` | yes | Must be in `TEXT_ARMS` |
| `--split` | yes | Only `discovery` accepted |
| `--seed` | no | Default `DEFAULT_SEED` (42); documents primary seed in metadata |
| `--cohort-run-dir` | no | Default: latest `outputs/<arm>/cohort/<ts>/` via `latest_timestamp_subdir` |
| `--max-posts` | no | Test hook only; omit in production runs |

Load discovery posts by intersecting cohort parquet rows with IDs from `data/post_split/discovery_post_ids.csv`. Skip posts with null `modal_decision` for doc-frequency class counts, but still embed all discovery IDs unless you set `--max-posts`.

## Human gates (if any)

None for Step 2.

## Commit message template

`step2: {short description}`

Suggested commits:

- `step2: scaffold baselines module and output schemas`
- `step2: add doc-frequency preprocessing and tests`
- `step2: add Titan post embeddings and K-Means sweep`
- `step2: upload baseline outputs to S3`

## Handoff to Step 3

Step 3 (LLM discovery) depends on the following:

- Committed discovery post IDs (9,449) and cohort with `split`, `modal_decision`, and text columns.
- Baseline outputs on S3 for comparison in later analysis (optional read; not blocking).
- Do not reuse baseline embeddings for LLM batches. Batching reads cohort directly.
- `llm_client.py` (Step 3) will call LiteLLM directly per orchestrator override. Step 2 does not touch LLM code.
