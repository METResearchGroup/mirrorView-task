# Step 6: Outcome overlays and Part 2 comparison (Q5 + Q1)

## Goal

Implement `experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_outcomes.py` (Q5) and `experiments/bertopic_original_mirror_part3_2026_09_24/src/compare_part2.py` (Q1). Join keep/remove labels and metadata overlays to production topic assignments. Restrict outcome tables to rated posts with `n_raters >= 3`. Write analysis artifacts under `outputs/analyses/outcomes/<UTC_TS>/` and `outputs/analyses/part2_comparison/<UTC_TS>/`. Download Part 3 `embeddings.npy` from S3 when missing locally.

## Prerequisites

- Step 1 complete: `shared/data/transformed/study_phase_2_part_3/keep_remove_labels.csv` registered as `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` with columns `post_id`, `decision`, `keep_remove_label`, `n_raters`, `keep_rate`, `n_keep`, `n_remove`, `sampled_stance`, `sample_toxicity_type`, `platform`, `original_text`, `mirror_text`.
- Step 2 complete: experiment `src/` scaffold with `data.py`, `paths.py`, pure helpers.
- Step 4 complete: production runs exist under `outputs/topics/original/<UTC_TS>/`, `outputs/topics/joint/<UTC_TS>/`, `outputs/labels/original/<UTC_TS>/`, `outputs/labels/joint/<UTC_TS>/`.
- Step 5 optional: reuse `cross_role_metrics.py` Hungarian helpers if already extracted (not required for Q5 or Q1).
- Raw ratings available at `shared/data/raw/study_phase_2_part_3/results/full.csv` with `party_group` in `{democrat, republican}` for linked-fate scored rows.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md` | Q1/Q5 definitions; min 3 raters at analysis time; fit vs analysis corpus |
| `/workspace/experiments/bertopic_modeling_2026_08_05/RESULTS.md` | Part 2 production run id `20260805T135853Z`; 53 topics; 34% noise |
| `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/metadata.json` | Part 2 fit hyperparameters for deterministic refit |
| `/workspace/experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/assignments.parquet` | Part 2 topic ids (column `message_id`; map to Part 3 `post_id` via carryover join) |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv` | Part 2 column `message_id` (alias of results `post_id`); reference only |
| `/workspace/shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` | Part 2 catalog `post_primary_key` for carryover join to Part 3 stimuli |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | Model save path `{run_dir}/model/`; `BERTopic.load` contract |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/.gitignore` | S3-primary patterns for `model/`, `umap_2d.npy`, `embeddings.npy` |
| `/workspace/shared/data/raw/study_phase_2_part_3/results/full.csv` | Rating-level `party_group`, `post_id`, `decision` |
| Step 5 outputs under `outputs/analyses/cross_role/<UTC_TS>/` | Hungarian matching helpers if already extracted |
| `/workspace/experiments/model_errors_analysis_2026_07_15/analyze/cluster.py` | `adjusted_rand_score` usage pattern |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_outcomes.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/compare_part2.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/outcomes.py` (new; pure helpers: bootstrap, BH FDR, facet filters)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/part2_model.py` (new; load or refit Part 2 model)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_outcomes.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_compare_part2.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_outcomes.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (Stage Q5/Q1 CLI blocks only)
- Runtime artifacts under `outputs/analyses/outcomes/` and `outputs/analyses/part2_comparison/`

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**` (read-only; do not modify Part 2 experiment)
- `/workspace/shared/**` except reading datasets
- `/workspace/pyproject.toml`
- Production topics runs under `outputs/topics/**` (read-only)
- Ablation outputs (`outputs/ablations/**`)

## Implementation details

### Shared analysis filters (both scripts)

1. Load `STUDY_PHASE_2_PART_3_KEEP_REMOVE_LABELS` via `shared.data.dataloader.load_dataset`.
2. Join topic assignments from `--topics-run-dir` on `post_id` (assignments parquet uses `post_id` from Step 4).
3. **Outcome analysis corpus:** keep rows where `n_raters >= 3` and `decision` in `{keep, remove}`. Do not filter at label-build time (Step 1 stores all 18,866 rated posts).
4. **Noise topic:** report topic `-1` in separate tables/figures; do not drop from overall counts.

### Q5: `analyze_outcomes.py`

**Primary model:** Part 3 production original topics run (`--topics-run-dir`, default latest under `outputs/topics/original/`).

**Secondary model:** Part 3 production joint topics run (`--joint-topics-run-dir`, default latest under `outputs/topics/joint/`). Write parallel tables with suffix `_joint` in filenames.

**Per-topic pair-level keep rate (post level):**

- For each topic `t`, `keep_rate_t = mean(keep_rate)` over posts assigned to `t` (use post-level `keep_rate` from labels table, equivalent to `n_keep / n_raters`).
- Overall keep rate: mean over all posts in the filtered corpus.
- **Cluster bootstrap by post:** resample posts with replacement `n_bootstrap=2000`, `seed=42`. For each resample, recompute per-topic keep rate. Report 2.5th and 97.5th percentiles as CI endpoints.
- **BH FDR test vs overall:** for each non-noise topic, two-sided binomial test using post-level successes `n_keep` and trials `n_raters` pooled per topic vs corpus-wide keep rate; apply `statsmodels.stats.multitest.multipletests(..., method="fdr_bh")` at `q < 0.05`. Store `p_value`, `q_value`, `significant_bh`.

**Rating-level rater-party cuts:**

- Load `full.csv`; filter `evaluation_mode == "linked_fate"`, `decision` in `{keep, remove}`, `party_group` in `{democrat, republican}`.
- Join `post_id` to topic assignments.
- Per topic and party: `keep_rate = n_keep_ratings / n_ratings`.
- Bootstrap CIs by **post** (cluster): for each bootstrap draw, resample posts, re-aggregate ratings within drawn posts, recompute party-specific keep rates.
- Write `outcomes_by_topic_party.csv`.

**Facets:** `sampled_stance`, `sample_toxicity_type`, `platform` from labels table.

- For each facet value `f`, subset posts with that facet value, still requiring `n_raters >= 3`.
- Report a topic-facet cell only when `n_posts >= 30` for that topic within the facet subset.
- Write `outcomes_by_topic_facet.csv` with columns: `facet`, `facet_value`, `topic`, `n_posts`, `keep_rate`, `ci_low`, `ci_high`.
- Emit facet overlay figures (bar or dot with CI) under `figures/` using Plotly HTML + PNG.

**Outputs:** `outputs/analyses/outcomes/<UTC_TS>/`

```text
metadata.json
outcomes_by_topic.csv              # original model; includes topic -1 row
outcomes_by_topic_joint.csv
outcomes_by_topic_party.csv
outcomes_by_topic_facet.csv
overall_keep_rate.json
figures/
  keep_rate_by_topic_original.{html,png}
  keep_rate_by_topic_joint.{html,png}
  keep_rate_by_topic_party_democrat.{html,png}
  keep_rate_by_topic_party_republican.{html,png}
  keep_rate_facet_sampled_stance.{html,png}
  keep_rate_facet_sample_toxicity_type.{html,png}
  keep_rate_facet_platform.{html,png}
```

`metadata.json` keys: `source_topics_run`, `source_joint_topics_run`, `min_raters`, `n_bootstrap`, `bootstrap_seed`, `fdr_alpha`, `facet_min_posts`, `n_posts_analyzed`, `overall_keep_rate`.

### Q1: `compare_part2.py`

**Carryover set (catalog overlap):** inner join Part 2 and Part 3 stimulus catalogs on stripped string equality:

```python
p2_stim = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)  # or read shared/data/raw/study_phase_2_part_2/stimuli/flips.csv
p3_stim = load_stimuli_posts()  # post_id renamed from post_primary_key
carryover_post_ids = set(p2_stim["post_primary_key"].astype(str).str.strip()) & set(p3_stim["post_id"].astype(str).str.strip())
```

**Expected match count:** `len(carryover_post_ids) == 8899` (assert in metadata; do not hard-fail if off by a few).

**ID mapping:** Part 2 transformed labels (`shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv`) expose the same ids as Part 3 `post_id`, but under the column name `message_id`. For Q1 topic assignment, use the **stimulus catalog join above**, not `message_id` intersect alone (that yields 7690 rated overlap and drops 1209 unrated catalog carryover posts).

**Part 3 side:** topic ids from Part 3 production original run assignments for carryover `post_id`s (after the same dedupe subset used at fit time).

**Part 2 side:** assign carryover posts to the **saved Part 2 BERTopic model** via `topic_model.transform(docs, embeddings)`:

1. **Preferred path:** load model from  
   `experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model/`  
   (safetensors serialization; `embedding_model=None` on load).
2. **If `model/` missing locally** (gitignored; common on fresh clones):
   - **Option A (deterministic refit):** run Part 2 fit without modifying Part 2 sources:

     ```bash
     cd /workspace
     PYTHONPATH=. uv run --extra bertopic python \
       experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --seed 42
     ```

     Use the new run only if `metadata.json` hyperparameters match production (`min_cluster_size=15`, UMAP/HDBSCAN blocks identical). Record `part2_model_source: refit` in metadata.
   - **Option B (S3):** if the Part 2 model was uploaded to  
     `s3://mirrorview-experimental-artifacts/experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model/`  
     (Step 8 upload; optional on fresh clones), download with `lib.aws.s3.S3` before transform. Record `part2_model_source: s3`.
   - Fail with actionable error if neither local model, refit, nor S3 object exists.

**Embeddings for transform:** load Titan vectors for carryover `post_id`s from Part 3 `outputs/embeddings/original/` aligned to Part 2 `original_text` for those ids. If `embeddings.npy` is missing locally, download from `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/outputs/embeddings/original/embeddings.npy` (Step 3 upload). Keep `index.parquet` from git for row alignment.

**Analyses:**

- Cross-tab: `crosstab_part2_part3_topics.csv` (rows Part 2 topic, cols Part 3 topic, counts).
- Topic share tables: `topic_shares_part2.csv`, `topic_shares_part3.csv`, `topic_share_delta.csv` (Part 3 minus Part 2 share on overlap).
- **ARI and NMI** on paired topic label vectors for carryover posts (`sklearn.metrics.adjusted_rand_score`, `normalized_mutual_info_score`).
- Facet figures: repeat share comparison faceted by `sampled_stance`, `sample_toxicity_type`, `platform` (same 30-post cell rule for facet-specific share bars).

**Outputs:** `outputs/analyses/part2_comparison/<UTC_TS>/`

```text
metadata.json
carryover_post_ids.parquet
part2_assignments.parquet
part3_assignments.parquet
crosstab_part2_part3_topics.csv
topic_shares_part2.csv
topic_shares_part3.csv
topic_share_delta.csv
agreement_metrics.json          # ari, nmi, n_carryover
figures/
  crosstab_heatmap.{html,png}
  topic_share_comparison.{html,png}
  topic_share_facet_sampled_stance.{html,png}
  topic_share_facet_sample_toxicity_type.{html,png}
  topic_share_facet_platform.{html,png}
```

## TDD tests first

Write failing tests before implementation. No network, no Bedrock, no OpenAI.

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_outcomes.py`

Pure helper tests only.

```python
# test_cluster_bootstrap_keep_rate_ci_bounds
# Given: 4 posts, topics [0,0,1,1], keep_rates [1.0, 0.0, 1.0, 0.0]
# When: cluster_bootstrap_keep_rate_by_topic(..., n_bootstrap=500, seed=42)
# Then: CI for topic 0 is within [0,1]; point estimate 0.5; reproducible across two calls

# test_bh_fdr_flags_high_deviation
# Given: 3 topics, corpus keep_rate=0.5; topic A 40/40 keep, topic B 5/40 keep, topic C 20/40 keep
# When: benjamini_hochberg_topic_tests(...)
# Then: topic A q_value < 0.05; topic B q_value < 0.05; topic C q_value >= 0.05

# test_facet_cell_suppressed_below_30
# Given: facet_value "left" has 29 posts in topic 3
# When: build_facet_outcome_table(..., facet_min_posts=30)
# Then: no row for (facet=sampled_stance, facet_value=left, topic=3)

# test_noise_topic_included
# Given: assignments include topic -1 with 2 posts
# When: summarize_outcomes_by_topic(...)
# Then: output contains topic=-1 row; not merged into other topics
```

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_outcomes.py`

Use synthetic parquet fixtures in `tests/fixtures/outcomes/` (create minimal CSV/parquet in test setup).

```python
# test_analyze_outcomes_filters_min_raters
# Given: labels with post A n_raters=2, post B n_raters=3
# When: load_outcome_corpus(min_raters=3)
# Then: only post B retained

# test_analyze_outcomes_writes_expected_csv_columns
# Given: tmp topics run dir with assignments.parquet (3 posts, 2 topics + noise)
# When: run_analyze_outcomes(tmp_dirs..., n_bootstrap=50)
# Then: outcomes_by_topic.csv columns ==
#   [topic, n_posts, keep_rate, ci_low, ci_high, p_value, q_value, significant_bh]

# test_party_keep_rate_uses_rating_level
# Given: one post, topic 1; 3 democrat keep + 1 republican remove ratings
# When: compute_party_outcomes(...)
# Then: democrat keep_rate=1.0; republican keep_rate=0.0
```

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_compare_part2.py`

Mock `BERTopic.load` and `transform` with a fake class; no real model files.

```python
# test_carryover_intersection_ids
# Given: Part 2 stimuli post_primary_key {a,b,c}; Part 3 post_id {b,c,d}
# When: find_carryover_post_ids(...)
# Then: {b,c}; live catalog join expects 8899

# test_agreement_metrics_perfect_match
# Given: part2_topics=[0,1,0]; part3_topics=[0,1,0]
# When: compute_topic_agreement(...)
# Then: ari==1.0 and nmi==1.0

# test_part2_model_loader_falls_back_to_refit_flag
# Given: model dir missing; monkeypatch refit to write sentinel path
# When: resolve_part2_model(...)
# Then: returns path; metadata part2_model_source == "refit"
```

Run tests:

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_outcomes.py -q
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_outcomes.py -q
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_compare_part2.py -q
```

## Exact commands

### 1. Run unit tests (must pass before live analysis)

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_outcomes.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_analyze_outcomes.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_compare_part2.py -q
```

Expected: `N passed` (no failures).

### 2. Q5 outcome analysis (requires Step 4 production runs)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

ORIG_TOPICS=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original | tail -1)
JOINT_TOPICS=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint | tail -1)

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/analyze_outcomes.py \
  --topics-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/${ORIG_TOPICS}" \
  --joint-topics-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint/${JOINT_TOPICS}" \
  --min-raters 3 \
  --n-bootstrap 2000 \
  --bootstrap-seed 42 \
  --facet-min-posts 30
```

Expected stdout (example):

```text
outcomes_run_dir=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes/20260924T150000Z
n_posts_analyzed=... overall_keep_rate=0.696
n_topics_reported=... (includes noise topic -1)
```

### 3. Q1 Part 2 comparison

```bash
cd /workspace
PART2_MODEL_DIR=experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z/model
if [ ! -d "$PART2_MODEL_DIR" ]; then
  echo "Part 2 model missing; running deterministic refit"
  PYTHONPATH=. uv run --extra bertopic python \
    experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --seed 42
  PART2_RUN=$(ls -1 experiments/bertopic_modeling_2026_08_05/outputs/topics/original | tail -1)
  PART2_MODEL_DIR="experiments/bertopic_modeling_2026_08_05/outputs/topics/original/${PART2_RUN}/model"
fi

ORIG_TOPICS=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original | tail -1)

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/compare_part2.py \
  --part3-topics-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/${ORIG_TOPICS}" \
  --part2-model-dir "$PART2_MODEL_DIR" \
  --part2-topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z \
  --facet-min-posts 30
```

Expected stdout (example):

```text
part2_comparison_run_dir=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/part2_comparison/20260924T150500Z
n_carryover=8899 ari=... nmi=...
part2_model_source=local|refit|s3
```

### 4. Verification

```bash
cd /workspace
OUT=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes | tail -1)
test -f "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes/$OUT/outcomes_by_topic.csv"
test -f "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes/$OUT/outcomes_by_topic_party.csv"
python -c "import json; m=json.load(open('experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes/$OUT/metadata.json')); assert m['min_raters']==3; assert m['n_bootstrap']==2000"

P2=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/part2_comparison | tail -1)
test -f "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/part2_comparison/$P2/agreement_metrics.json"
test -f "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/part2_comparison/$P2/crosstab_part2_part3_topics.csv"
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Min raters filter | Only `n_raters >= 3` posts in Q5 tables | All rated posts included |
| Bootstrap | 2000 resamples, seed 42, cluster by post | Rating-level bootstrap or wrong seed |
| BH FDR | `q_value` column; `significant_bh` at q<0.05 | Uncorrected p-values only |
| Party cuts | Rating-level aggregation; bootstrap by post | Post-level modal only |
| Facet threshold | Cells with `<30` posts omitted | All cells reported |
| Noise topic | Topic `-1` in separate rows/figures | Noise dropped silently |
| Q1 carryover | Cross-tab + ARI/NMI on overlap | Part 3-only comparison |
| Part 2 model | Load, refit, or S3 documented in metadata | Hard crash without recovery path |
| Tests | All three test modules pass offline | Network or real model in unit tests |
| Part 2 folder | `git diff -- experiments/bertopic_modeling_2026_08_05/src/` empty | Part 2 sources edited |

## Commit messages

1. `test(part3-bertopic): add outcome and part2 comparison helper tests`
2. `feat(part3-bertopic): implement Q5 outcome overlays with bootstrap and BH FDR`
3. `feat(part3-bertopic): implement Q1 Part 2 topic comparison on carryover posts`
4. `docs(part3-bertopic): document Q5 and Q1 analysis CLI in README`
