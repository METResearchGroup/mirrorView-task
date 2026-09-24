# Step 7: Ablations A0 to A5 and human topic review

## Goal

Implement `experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py` and supporting modules to run ablations **A0 through A5** in isolated timestamped folders under `outputs/ablations/<ablation_id>/<UTC_TS>/`. Each ablation changes one setting from production (except A4, which compares fit designs). Record sensitivity metrics including Q5 topic keep-rate ranking stability. Write `outputs/ablations/summary.csv`. Generate human review markdown for production original and joint models. Pull Titan and MiniLM `embeddings.npy` from S3 when missing locally.

## Prerequisites

- Steps 1 through 6 complete: production fits, labels, Q5 outcome tables, cross-role metrics (Q2/Q3).
- Titan embedding caches at `outputs/embeddings/{original,mirror}/` and MiniLM caches at `outputs/embeddings_minilm/{original,mirror}/` (Step 3). Pull `embeddings.npy` from S3 if missing locally (Step 3 pull commands).
- Production original topics run and joint topics run paths recorded in Step 4/6 metadata.
- Lab baseline guidance: [HOW_TO_CLUSTER_TEXT.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_CLUSTER_TEXT.md) (naive baselines, K-Means k sweep, UMAP seed stability).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md` | Ablation definitions A0 to A5 |
| `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py` | Production hyperparameter builder; override hooks |
| Step 6 `outputs/analyses/outcomes/<UTC_TS>/outcomes_by_topic.csv` | Q5 reference ranking for A3/A5 |
| Step 5 `outputs/analyses/cross_role/<UTC_TS>/` | Q2/Q3 reference metrics for A4 |
| `/workspace/experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py` | UMAP/HDBSCAN defaults |
| `/workspace/experiments/model_errors_analysis_2026_07_15/analyze/cluster.py` | ARI computation pattern |

## Files allowed to change

- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py` (new CLI)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/src/ablations/` (new package: `a0_baselines.py`, `a1_umap_seeds.py`, `a2_min_cluster.py`, `a3_minilm.py`, `a4_design.py`, `a5_outliers.py`, `review_samples.py`, `summary.py`)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_ablations.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_review_samples.py` (new)
- `/workspace/experiments/bertopic_original_mirror_part3_2026_09_24/README.md` (ablation CLI section)
- Runtime artifacts under `outputs/ablations/` and `outputs/reviews/`

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_bertopic_original_mirror_part3_49bfb7/plan.md`
- `/workspace/experiments/bertopic_modeling_2026_08_05/**`
- `/workspace/shared/**`
- Production runs under `outputs/topics/{original,mirror,joint}/` (read-only; never overwrite)
- Production analyses under `outputs/analyses/outcomes/` and `outputs/analyses/cross_role/` (read-only)

## Implementation details

### Output layout (all ablations)

```text
outputs/ablations/<ablation_id>/<UTC_TS>/
  metadata.json
  metrics.json
  ... ablation-specific artifacts ...
outputs/ablations/summary.csv
outputs/reviews/<UTC_TS>/
  review_original.md
  review_joint.md
  samples.parquet
```

`summary.csv` columns (one row per ablation run):

`ablation_id`, `run_ts`, `setting_changed`, `setting_value`, `n_topics`, `n_noise`, `noise_share`, `ari_vs_production`, `nmi_vs_production`, `spearman_q5_keep_rate`, `q2_pair_agreement`, `q3_role_dominated_topics`, `notes`.

### A0: Naive baselines (`ablation_id=a0_naive`)

**Does not use BERTopic fit.** Run on deduplicated original-role corpus (same ids as production original fit).

1. **Top-word document-frequency grouping:** tokenize with English stopwords; for each of top 50 global terms, form a group of docs containing that term; write `doc_freq_groups.csv` with group size and sample ids.
2. **K-Means on Titan embeddings:** for `k` in `2..30`, `random_state=42`, L2-normalized Titan vectors:
   - Fit `sklearn.cluster.KMeans(n_clusters=k, random_state=42, n_init=10)`.
   - Report `silhouette_score` (cosine or euclidean on normalized vectors) in `kmeans_sweep.csv`.
   - **Model selection:** do not auto-pick k by silhouette alone. For each k in `{5, 10, 15, 20, 25, 30}`, write `samples_k{k}.md` with **20 random docs per cluster** (or fewer if cluster smaller). Record chosen `k_chosen` and justification string in `metadata.json` after human inspection (delegate runs script; human edits `k_chosen` in metadata or passes `--k-chosen`).

Artifacts: `kmeans_sweep.csv`, `kmeans_assignments_k<k_chosen>.parquet`, `doc_freq_groups.csv`.

### A1: UMAP seed stability (`ablation_id=a1_umap_seeds`)

Change only UMAP `random_state` in `{42, 43, 44, 45, 46}`. Hold HDBSCAN, vectorizer, embeddings, dedupe corpus identical to production original fit.

Per seed run:

- Fit BERTopic; save under `outputs/ablations/a1_umap_seeds/<UTC_TS>/seed_<s>/` (assignments + topic_info + model; `model/` gitignored, S3-primary).
- Record `n_topics`, `n_noise`, `noise_share`.

Pairwise comparison across seeds:

- For each pair of seeds, Hungarian-match topics on **topic centroid cosine similarity** in embedding space (mean Titan embedding of assigned docs per topic, exclude noise).
- Compute **ARI** on doc assignments after mapping matched topic ids.
- Write `pairwise_ari.csv` and `seed_summary.csv`.

### A2: HDBSCAN min cluster size (`ablation_id=a2_min_cluster`)

Values: `15`, `30`, `50`. Only change `min_cluster_size`. UMAP seed 42. Original role, Titan embeddings, deduped corpus.

Per value subdirectory: `mcs_<n>/` with assignments, topic_info, metrics.

### A3: MiniLM vs Titan (`ablation_id=a3_minilm`)

Use `outputs/embeddings_minilm/original/` (384-d, L2-normalized per Step 3). Download `embeddings.npy` from S3 if absent locally. Production hyperparameters otherwise.

Compare to production original Titan run:

- ARI/NMI on same post ids (Hungarian match for ARI if topic counts differ).
- `n_topics`, `n_noise`, `noise_share`.
- **Q5 ranking change:** run lightweight outcome overlay (reuse `outcomes.summarize_outcomes_by_topic` from Step 6 `outcomes.py` on ablation assignments) and Spearman correlation of per-topic keep rates vs production `outcomes_by_topic.csv` (exclude topic -1). Store `spearman_q5_keep_rate` and list topics entering/leaving top/bottom 5 by keep rate in `q5_rank_shift.json`.

### A4: Design comparison (`ablation_id=a4_design`)

Three variants (subfolders `separate/`, `joint/`, `original_assign_mirror/`):

| Variant | Fit | Assignment for metrics |
|---------|-----|------------------------|
| `separate` | original + mirror models separately (production original + production mirror runs; read-only) | paired posts: original topic vs mirror topic |
| `joint` | joint pooled model (production joint run; read-only) | co-assignment under joint model |
| `original_assign_mirror` | original model only | mirror texts via `transform` (production `outputs/assignments/mirror_via_original/<UTC_TS>/`) |

For each variant, recompute **Q2** (pair topic agreement rate) and **Q3** (role-dominated topic flags, per-topic role share) using the same definitions as Step 5. Write `q2_q3_metrics.json` per variant. No refit unless production run missing (fail fast).

### A5: Outlier reduction (`ablation_id=a5_outliers`)

Toggle BERTopic `reduce_outliers` with `strategy="embeddings"`:

- `off`: production default (no reduction pass).
- `on`: after fit, `topic_model.reduce_outliers(docs, embeddings, strategy="embeddings")` then update assignments.

Report `noise_share` before/after and Spearman Q5 keep-rate correlation vs production (same as A3). Write `assignments_off.parquet`, `assignments_on.parquet`, `noise_comparison.json`.

### Human review samples (`review_samples.py`)

**Not an ablation.** Run after production Step 4 labels exist.

For **original** and **joint** production models:

- For each topic `t != -1`: sample **10 nearest-to-centroid** docs (cosine similarity to topic mean Titan embedding) and **10 random** docs from topic `t`.
- For noise: sample **30 random** noise docs.
- Write `outputs/reviews/<UTC_TS>/review_original.md` and `review_joint.md` with sections per topic: LLM label (if available), keywords (top 10 c-TF-IDF), then bullet list of doc ids and truncated text (first 200 chars).
- Also write `samples.parquet` with columns: `model_role`, `topic`, `sample_kind` (`centroid`/`random`/`noise`), `post_id`, `text_excerpt`.

**Human review step (mandatory gate before Step 8):** operator reads both markdown files and records in `outputs/reviews/<UTC_TS>/review_notes.md`:

```text
reviewed_by: <name>
reviewed_at: <ISO8601>
original_topics_ok: yes|no
joint_topics_ok: yes|no
notes: <free text>
```

Do not block ablation code on review completion, but Step 8 must record whether review notes exist.

### CLI: `run_ablations.py`

```bash
PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py \
  --ablation all|a0|a1|a2|a3|a4|a5|review \
  --production-original-run-dir <path> \
  --production-joint-run-dir <path> \
  --q5-outcomes-csv <path> \
  --cross-role-dir <path> \
  --seed 42
```

`--ablation all` runs A0 through A5 sequentially, then appends rows to `summary.csv`. `--ablation review` only builds review markdown.

## TDD tests first

No network, no Bedrock, no OpenAI, no full BERTopic fit in unit tests.

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_ablations.py`

```python
# test_kmeans_sweep_records_all_k
# Given: synthetic embeddings shape (40, 8) and 40 doc ids
# When: run_kmeans_sweep(k_min=2, k_max=5, seed=42)
# Then: 4 rows in result; each has silhouette_score float; same result on repeat

# test_hungarian_pairwise_ari_identical_clusterings
# Given: two label vectors [0,0,1,1] and [1,1,0,0] (permutation)
# When: pairwise_ari_hungarian(...)
# Then: ari == 1.0

# test_spearman_q5_rank_unchanged
# Given: production keep rates [0.9,0.5,0.1]; ablation [0.9,0.5,0.1]
# When: spearman_q5_keep_rate(...)
# Then: rho == 1.0

# test_a4_reads_production_paths_without_writing_topics
# Given: fake production run dirs with assignments.parquet only
# When: run_a4_design_comparison(...)
# Then: writes q2_q3_metrics.json; does not create outputs/topics/*
```

### `experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_review_samples.py`

```python
# test_review_samples_centroid_picks_nearest
# Given: 3 docs in topic 0; embeddings where doc_a closest to centroid
# When: select_centroid_samples(n=1)
# Then: returns doc_a

# test_review_markdown_includes_noise_section
# Given: assignments with 2 noise docs
# When: build_review_markdown(..., noise_n=2)
# Then: markdown contains "## Topic -1 (noise)" and 2 bullets
```

Run:

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_ablations.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_review_samples.py -q
```

## Exact commands

### 1. Unit tests

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_ablations.py \
  experiments/bertopic_original_mirror_part3_2026_09_24/tests/test_review_samples.py -q
```

Expected: all passed.

### 2. Run all ablations (long-running; requires GPU not required, CPU OK)

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PROD_ORIG=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original | tail -1)
PROD_JOINT=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint | tail -1)
Q5_CSV=$(ls -d experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/outcomes/*/outcomes_by_topic.csv | tail -1)
CROSS=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/cross_role | tail -1)

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py \
  --ablation all \
  --production-original-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/${PROD_ORIG}" \
  --production-joint-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint/${PROD_JOINT}" \
  --q5-outcomes-csv "$Q5_CSV" \
  --cross-role-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/analyses/cross_role/${CROSS}" \
  --seed 42
```

Expected stdout (example):

```text
ablation=a0_naive done
ablation=a1_umap_seeds done pairwise_mean_ari=0.85
ablation=a2_min_cluster done
ablation=a3_minilm done spearman_q5=0.92
ablation=a4_design done
ablation=a5_outliers done noise_off=0.34 noise_on=0.12 spearman_q5=0.88
summary_csv=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/ablations/summary.csv
```

### 3. Human review sample export

```bash
cd /workspace
PROD_ORIG=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original | tail -1)
PROD_JOINT=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint | tail -1)
LABELS_ORIG=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/labels/original | tail -1)
LABELS_JOINT=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/labels/joint | tail -1)

PYTHONPATH=. uv run --extra bertopic python \
  experiments/bertopic_original_mirror_part3_2026_09_24/src/run_ablations.py \
  --ablation review \
  --production-original-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/${PROD_ORIG}" \
  --production-joint-run-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/joint/${PROD_JOINT}" \
  --labels-original-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/labels/original/${LABELS_ORIG}" \
  --labels-joint-dir "experiments/bertopic_original_mirror_part3_2026_09_24/outputs/labels/joint/${LABELS_JOINT}" \
  --seed 42
```

Expected: `review_dir=experiments/bertopic_original_mirror_part3_2026_09_24/outputs/reviews/<UTC_TS>` with two markdown files.

### 4. Verification

```bash
cd /workspace
test -f experiments/bertopic_original_mirror_part3_2026_09_24/outputs/ablations/summary.csv
python -c "import pandas as pd; s=pd.read_csv('experiments/bertopic_original_mirror_part3_2026_09_24/outputs/ablations/summary.csv'); assert set(s['ablation_id'])>= {'a0_naive','a1_umap_seeds','a2_min_cluster','a3_minilm','a4_design','a5_outliers'}; print('summary OK', len(s))"

# Production topics untouched (timestamp dirs only grow in ablations/)
PROD_COUNT=$(ls -1 experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original | wc -l)
echo "production original runs: $PROD_COUNT"
```

## Pass/fail criteria

| Check | Pass | Fail |
|-------|------|------|
| Isolation | Ablation outputs only under `outputs/ablations/` | Overwrites production topics |
| A0 | K-Means k=2..30 sweep + doc-freq groups + human k choice documented | Silhouette-only auto k |
| A1 | 5 UMAP seeds; pairwise ARI after Hungarian match | Single seed only |
| A2 | mcs 15/30/50 runs | Missing grid point |
| A3 | MiniLM vs Titan ARI + Q5 Spearman + rank shift file | Titan-only |
| A4 | Q2/Q3 under 3 designs without refit | Refits production |
| A5 | reduce_outliers off vs on + noise + Q5 Spearman | Missing toggle |
| Summary | `summary.csv` one row per ablation run | Partial summary |
| Review | 10+10 per topic + 30 noise per model in markdown | Missing noise section |
| Tests | ablation + review tests pass offline | Network in tests |

## Commit messages

1. `test(part3-bertopic): add ablation and review sample unit tests`
2. `feat(part3-bertopic): implement A0 naive baselines and K-Means sweep`
3. `feat(part3-bertopic): implement A1 UMAP seed stability ablation`
4. `feat(part3-bertopic): implement A2 min cluster size grid`
5. `feat(part3-bertopic): implement A3 MiniLM embedding ablation`
6. `feat(part3-bertopic): implement A4 fit design comparison metrics`
7. `feat(part3-bertopic): implement A5 outlier reduction ablation`
8. `feat(part3-bertopic): add human review sample export for original and joint`
