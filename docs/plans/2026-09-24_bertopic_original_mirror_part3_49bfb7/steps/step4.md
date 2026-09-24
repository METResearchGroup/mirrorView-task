# Step 4: Smoke run and production fits

## Goal

Apply dedupe before every BERTopic fit. Run a fixed 50-pair smoke pipeline (seed 42, `min_cluster_size=5`) through fit, LLM label, and viz for `original`, `mirror`, and `joint`. **Stop and wait for explicit user approval before production.** After approval, run production fits (Part 2 hyperparameters, `min_cluster_size=15`) for `original`, `mirror`, and `joint`. Assign mirror texts with the production original model via `transform`. Write post-hoc LLM labels (`gpt-5.4-nano`) and six overlay figures per role. Upload gitignored `model/` dirs and `umap_2d.npy` to S3 after each topics run.

## Prerequisites

Assume Steps 1 to 3 are complete:

1. **Step 1:** `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` is registered. Modal labels expose `post_id`, `decision`, `keep_rate`, `n_raters`, `sampled_stance`, `sample_toxicity_type`, `platform`, `original_text`, `mirror_text`. Minimum 3 raters is **not** baked into the label table; apply it only in outcome analyses (Step 6).
2. **Step 2:** `experiments/bertopic_original_mirror_part3_2026_09_24/src/` exists with ported Part 2 stages (`paths.py`, `data.py`, `dedupe.py`, `load_embeddings.py`, `fit_bertopic.py`, `label_topics_llm.py`, `visualize_clusters.py`) parameterized by `--text-role {original,mirror,joint}`, plus `dedupe_stimuli()` and `build_joint_frame()` (joint rows include `pair_post_id`, which equals `post_id` because Part 3 has one post per pair).
3. **Step 3:** Titan caches exist at `outputs/embeddings/{original,mirror}/` (`embeddings.npy`, `index.parquet`, `metadata.json`) covering all **18,899** stimulus posts. MiniLM ablation caches exist at `outputs/embeddings_minilm/{original,mirror}/` (unused in this step). If `embeddings.npy` is missing locally, pull from S3 per Step 3 before fit (see Step 3 pull commands).

## Caller / unit of work

**Smoke (approval gate, all three roles):**

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py \
  --text-role original --sample-pairs 50 --seed 42
# Repeat for --text-role mirror and --text-role joint
```

Then label and viz each smoke topics run. Then run `assign_mirrors.py` on the smoke original run (optional for smoke checklist; required before production sign-off).

**Production (blocked until user approval):**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py --text-role original
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py --text-role mirror
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py --text-role joint
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/assign_mirrors.py \
  --original-topics-run-dir <PROD_ORIGINAL_TOPICS_RUN>
```

Label and viz each production topics run.

**In scope:** dedupe integration, smoke + production fit/label/viz, `assign_mirrors.py`, unit tests with synthetic embeddings.

**Out of scope:** cross-role analyses (Step 5), outcome overlays Q1/Q5 (Step 6), ablations (Step 7), S3 upload (Step 8), edits to `experiments/bertopic_modeling_2026_08_05/`, MiniLM ablation fits.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md` | Dedupe-before-fit decision; production hyperparameters |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | Part 2 fit contract, smoke `min_cluster_size` override |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/label_topics_llm.py` | Post-hoc OpenAI labeling; skip topic `-1` |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py` | Three overlays, six figure files |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/paths.py` | Role dirs, `assignments_dir`, timestamps |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/dedupe.py` | Dedupe rules from Step 2 |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/data.py` | Part 3 label load, pair ids |
| `/workspace/lib/load_env_vars.py` | `OPENAI_API_KEY` for labeling |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/label_topics_llm.py` (role + joint text column wiring only if needed)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/visualize_clusters.py` (role parameter only if needed)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/paths.py` (add `assignments_dir`, allow `joint` role)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/assign_mirrors.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_fit_bertopic_dedupe.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_assign_mirrors.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_joint_corpus.py` (create)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (smoke vs production CLI)
- Runtime artifacts under `experiments/bertopic_original_mirror_part3_2026_09_24/outputs/{topics,labels,figures,assignments}/`

## Files forbidden to change

- `/workspace/shared/**` (except read via dataloader)
- `/workspace/pyproject.toml`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/dedupe.py` (Step 2 owns rules; call it, do not redefine)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/load_embeddings.py`
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/RESULTS.md` (Step 8)
- Do **not** run production fits before explicit user approval

## Implementation details

### Dedupe before fit (call Step 2 `dedupe_stimuli`)

After loading the full embedding cache and Part 3 posts via `load_stimuli_posts()`, call `dedupe.dedupe_stimuli(posts_df)` which returns `(deduped_posts, dedupe_report)`:

| Rule | Action |
|------|--------|
| Duplicate `original_text` (173 groups) | Keep one row per normalized original text; keep first by `post_id` ascending |
| Identical original and mirror text (35 pairs total; 28 removed after duplicate-original pass) | Drop rows where `original_text == mirror_text` |

Write `dedupe_report.json` via `dedupe.write_dedupe_report(paths.dedupe_report_path(), report)` using the Step 2 schema:

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

Fit corpus = all deduplicated stimuli (18,698 posts for original/mirror; 37,396 joint rows). Do **not** filter to rated posts at fit time.

### `fit_bertopic.py` extensions

**CLI:**

```
--text-role {original,mirror,joint}   (required)
--sample-pairs N                      smoke only; sample N post_ids (one pair each) with seed (default None = full deduped corpus)
--seed 42                             default 42
```

**Corpus by role:**

| Role | `docs` source | Embeddings cache | `assignments.parquet` columns |
|------|---------------|------------------|-------------------------------|
| `original` | `original_text` | `outputs/embeddings/original/` | `post_id`, `pair_post_id` (= `post_id`), `text_role=original`, `topic`, `probability` |
| `mirror` | `mirror_text` | `outputs/embeddings/mirror/` | `post_id`, `pair_post_id` (= `post_id`), `text_role=mirror`, `topic`, `probability` |
| `joint` | role-specific text per row | concat original then mirror rows per post | `post_id`, `pair_post_id` (= `post_id`), `text_role`, `row_id`, `topic`, `probability` |

Joint row order: sort `post_id` ascending; within each post emit `original` row then `mirror` row. Part 3 has one post per pair, so `pair_post_id == post_id` everywhere (Step 2 `build_joint_frame`).

**Smoke sampling:** when `--sample-pairs 50`, draw 50 `post_id` values without replacement using `numpy.random.default_rng(seed)`. Keep all joint rows for those posts (100 rows). Record `sample_post_ids` in metadata.

**Production hyperparameters (exact, match Part 2):**

```python
UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)
HDBSCAN(min_cluster_size=15, metric="euclidean", cluster_selection_method="eom", prediction_data=True)
CountVectorizer(stop_words="english", min_df=2)
BERTopic(embedding_model=None, calculate_probabilities=True, verbose=True)
```

**Smoke override:** when `--sample-pairs` is set, `min_cluster_size=5`. Record effective value in `metadata.json`.

**Separate 2-D viz UMAP:** `UMAP(n_neighbors=15, n_components=2, min_dist=0.0, metric="cosine", random_state=42)` on the same embeddings used for fit.

Keep/remove, `sampled_stance`, `sample_toxicity_type`, `platform` must **not** enter fit inputs.

### Topics run output layout

`experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/<role>/<UTC_TS>/`

| File | Schema / content |
|------|------------------|
| `metadata.json` | `text_role`, `sample_post_ids` (null if full), `seed`, `dedupe_report_path`, `n_docs`, `n_topics` (excl. -1), `n_noise`, `llm_used: false`, full UMAP/HDBSCAN/vectorizer params |
| `assignments.parquet` | `post_id` (str), `pair_post_id` (str, equals `post_id`), `text_role` (str), `topic` (int), `probability` (float or null) |
| `topic_info.parquet` | BERTopic `get_topic_info()` |
| `umap_2d.npy` | `(n_docs, 2)` aligned to assignments row order; **gitignored**, S3-primary |
| `probabilities.npy` | optional when `calculate_probabilities=True` |
| `model/` | `topic_model.save(..., serialization="safetensors", save_ctfidf=True, save_embedding_model=False)`; **gitignored**, S3-primary |
| `dedupe_report.json` | copy or symlink of dedupe stats for this run |

After each topics run, upload gitignored large files to S3 (same prefix as Step 3). Upload `model/` and `umap_2d.npy` under the run directory. Step 8 uploads the full tree and verifies keys.

### `assign_mirrors.py` (new)

**CLI:**

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/assign_mirrors.py \
  --original-topics-run-dir outputs/topics/original/<UTC_TS>
```

**Logic:**

1. Load production (or smoke) original BERTopic model from `{run}/model/` (download from S3 if missing locally; see Step 3 pull pattern with `outputs/topics/original/<UTC_TS>/model/`).
2. Load deduped posts and mirror embeddings aligned by `post_id` (same dedupe set as original fit).
3. For each post: `original_topic` from original assignments; `mirror_topic` from `topic_model.transform(mirror_docs, mirror_embeddings)`.
4. Write one row per deduped post (`pair_post_id == post_id`).

**Output:** `outputs/assignments/mirror_via_original/<UTC_TS>/`

| File | Schema |
|------|--------|
| `pair_assignments.parquet` | `post_id`, `pair_post_id` (= `post_id`), `original_topic` (int), `mirror_topic` (int), `original_probability` (float), `mirror_probability` (float), `topics_agree` (bool) |
| `metadata.json` | `source_original_topics_run`, `n_pairs`, `n_agree`, `n_agree_excl_noise` (both topics != -1), `seed`, `dedupe_report_path` |

### LLM labels

Run `label_topics_llm.py --topics-run-dir <run> --text-role <role>` for each smoke and production topics run.

`outputs/labels/<role>/<UTC_TS>/topic_labels.parquet`: `topic_id`, `ctfidf_name`, `llm_label`, `n_docs`.

Model: `gpt-5.4-nano`. Skip topic `-1` (`llm_label=null`, zero API calls). Requires `OPENAI_API_KEY`.

### Visualizations

Run `visualize_clusters.py --topics-run-dir <run> --labels-run-dir <labels_run> --text-role <role>`.

`outputs/figures/<role>/<UTC_TS>/`: six files (`clusters_by_topic`, `clusters_by_keep_remove`, `clusters_by_unanimous`, each `.html` + `.png`) plus `metadata.json`.

For `joint` role: overlay keep/remove joins on `post_id` from labels (both joint rows for a post share the same pair-level decision).

### Approval gate (mandatory)

After smoke completes for all three roles:

1. Confirm smoke `metadata.json` has `sample_post_ids` length 50 (or `n_docs` 50 for single-role, 100 for joint).
2. Confirm six figure files per role are non-empty.
3. Confirm no production run has `sample_post_ids` set.
4. **Stop. Ask the user to review smoke artifacts. Do not start production until the user approves explicitly.**

## TDD tests first

Write failing tests before implementation. Use synthetic `(n, 8)` float32 embeddings (no network, no Bedrock). Mock BERTopic only when necessary; prefer testing pure helpers from Step 2 (`build_joint_frame`, `dedupe_stimuli`, assignment merge logic).

### `tests/test_fit_bertopic_dedupe.py`

```python
class TestDedupeBeforeFit:
    def test_duplicate_originals_collapsed_before_row_count(self):
        # 4 posts, 2 share original_text -> deduped n=3
        assert len(deduped_ids) == 3

    def test_identical_original_mirror_pair_dropped(self):
        # 1 post with original_text == mirror_text -> excluded from deduped set
        assert "post-x" not in deduped_post_ids

class TestSmokePostSampling:
    def test_sample_pairs_50_is_deterministic_with_seed_42(self):
        ids_a = sample_post_ids(all_post_ids, n=50, seed=42)
        ids_b = sample_post_ids(all_post_ids, n=50, seed=42)
        assert ids_a == ids_b
        assert len(ids_a) == 50
```

### `tests/test_joint_corpus.py`

```python
class TestJointCorpus:
    def test_joint_row_order_original_then_mirror_per_post(self):
        frame = build_joint_frame(deduped_posts)
        assert list(frame.loc[frame.pair_post_id == "p1", "text_role"]) == ["original", "mirror"]

    def test_joint_embeddings_stack_matches_docs(self):
        docs, emb, ids = assemble_joint_corpus(posts, emb_o, emb_m)
        assert emb.shape[0] == len(docs) == 2 * n_posts
```

### `tests/test_assign_mirrors.py`

```python
class TestAssignMirrors:
    def test_topics_agree_true_when_same_topic_id(self):
        row = make_pair_row(original_topic=3, mirror_topic=3)
        assert row["topics_agree"] is True

    def test_transform_called_with_mirror_embeddings_only(self, mock_model):
        # assign_mirrors uses transform(docs, embeddings), not fit_transform
        ...
```

Run tests:

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic pytest \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_fit_bertopic_dedupe.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_joint_corpus.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_assign_mirrors.py -q
```

Expect all tests green before live smoke.

## Exact commands

### Unit tests (no API)

```bash
cd /workspace
PYTHONPATH=. uv run --extra bertopic pytest \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_fit_bertopic_dedupe.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_joint_corpus.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_assign_mirrors.py -q
```

Expected: `3 passed` (or more if split into multiple test functions).

### Smoke fit (all roles)

```bash
cd /workspace
EXP=experiments/bertopic_original_mirror_part3_2026_09_24

for ROLE in original mirror joint; do
  PYTHONPATH=. uv run --extra bertopic python $EXP/src/fit_bertopic.py \
    --text-role $ROLE --sample-pairs 50 --seed 42
done
```

Expected stdout per role: `topics_run_dir=.../outputs/topics/<role>/<UTC_TS>` and `n_docs=50` (or `n_docs=100` for joint).

### Smoke label + viz (requires OPENAI_API_KEY)

```bash
EXP=experiments/bertopic_original_mirror_part3_2026_09_24
for ROLE in original mirror joint; do
  TOPICS_RUN=$(ls -1 $EXP/outputs/topics/$ROLE | tail -1)
  PYTHONPATH=. uv run --extra bertopic python $EXP/src/label_topics_llm.py \
    --text-role $ROLE --topics-run-dir $EXP/outputs/topics/$ROLE/$TOPICS_RUN
  LABELS_RUN=$(ls -1 $EXP/outputs/labels/$ROLE | tail -1)
  PYTHONPATH=. uv run --extra bertopic python $EXP/src/visualize_clusters.py \
    --text-role $ROLE --topics-run-dir $EXP/outputs/topics/$ROLE/$TOPICS_RUN \
    --labels-run-dir $EXP/outputs/labels/$ROLE/$LABELS_RUN
done
```

Expected: new dirs under `outputs/labels/<role>/` and `outputs/figures/<role>/` with six non-empty figure files each.

### Production (only after user approval)

```bash
EXP=experiments/bertopic_original_mirror_part3_2026_09_24

PYTHONPATH=. uv run --extra bertopic python $EXP/src/fit_bertopic.py --text-role original
PYTHONPATH=. uv run --extra bertopic python $EXP/src/fit_bertopic.py --text-role mirror
PYTHONPATH=. uv run --extra bertopic python $EXP/src/fit_bertopic.py --text-role joint

ORIG_RUN=$(ls -1 $EXP/outputs/topics/original | tail -1)
PYTHONPATH=. uv run --extra bertopic python $EXP/src/assign_mirrors.py \
  --original-topics-run-dir $EXP/outputs/topics/original/$ORIG_RUN

# Label + viz each production run (same pattern as smoke, omit --sample-pairs)
```

Expected production `metadata.json`: `sample_post_ids` is null; `hdbscan.min_cluster_size` is 15; `n_docs` is 18698 (original/mirror) or 37396 (joint).

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Dedupe | fit uses deduped rows only; `dedupe_report.json` present | Full 18,899 raw rows fitted |
| Smoke size | 50 pairs; joint `n_docs=100` | Full corpus or wrong N |
| Smoke HDBSCAN | `min_cluster_size=5` in smoke metadata | 15 on smoke |
| Production gate | no production runs before user approval | Production started early |
| Production params | UMAP/HDBSCAN/vectorizer match Part 2 | Param drift |
| assign_mirrors | `pair_assignments.parquet` one row per deduped post (`post_id`) | Missing or uses fit_transform |
| LLM | `gpt-5.4-nano`; topic `-1` skipped | Wrong model or noise labeled |
| Figures | 6 files per role, non-empty | Missing PNG/HTML |
| Tests | pytest green on synthetic data | No tests or network in unit tests |
| Part 2 untouched | `experiments/bertopic_modeling_2026_08_05/` unchanged | Edits to Part 2 tree |

## Commit messages

One commit per logical unit (implement-from-spec):

1. `feat(bertopic-part3): apply dedupe before fit in fit_bertopic`
2. `test(bertopic-part3): add dedupe and joint corpus unit tests`
3. `feat(bertopic-part3): add joint role fit and smoke pair sampling`
4. `feat(bertopic-part3): add assign_mirrors transform stage`
5. `test(bertopic-part3): add assign_mirrors unit tests`
6. `docs(bertopic-part3): document smoke vs production CLI in README`
7. `chore(bertopic-part3): smoke artifacts for 50-pair run (optional, if committing outputs)`

Do **not** commit production artifacts until after user approval. Do **not** batch commits 1 to 5 into one commit.
