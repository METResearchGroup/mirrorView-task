# Step 7: Analyze held-out test set and write RESULTS.md

Step 7 answers research questions Q1 through Q7 from `plan.md` on held-out test posts only (`split == test`). Discovery-half labels feed descriptive tables for feature description and June catalog overlap, while Q1 to Q7 hypothesis tests stay on the test split. June themes were mined from June labels, so the Q1 replication check uses September labels only (`participant_filter=september_only` cohort labels joined to the label matrix) on posts in the June catalog (`in_june_catalog`). Primary prevalence analyses use union labels unless an ablation sets `label_source=september_only`.

## Scope

- **Caller / entrypoint:** `map_june_themes`, `analyze`, `write_results`, and `s3_sync` CLIs.
- **In scope:** Load June themes and map them with Titan embeddings. Compute Q1 to Q7 on the test split only. Run ablation runners (including `label_source` union vs september_only). Assemble `RESULTS.md`. Upload the final experiment tree to S3. Write tests with mocked data and S3.
- **Out of scope:** Re-labeling or codebook edits, human validation set or kappa, discovery-half hypothesis tests, and editing earlier step modules except Step 7 owners.

## Files to inspect (read-only)

- `docs/plans/2026-09-24_llm_feature_generation_study_2_2f71ad/plan.md`: Q1 to Q7 table, ablation axes, "What is not answerable", June theme replication notes.
- `experiments/llm_based_feature_generation_2026_07_31/RESULTS.md`: 132 themes; model `gpt-5.4-nano`; rhetorical vs topic findings.
- `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/*.json`: stage-2 theme synthesis shards (verified path).
- `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/00000_2026_08_01-14:08:48.079120.json`: JSON shape: `result.themes[]` with `id`, `label`, `defining_features`, `example_message_ids`, `keep_count`, `remove_count`, `interpretation`.
- June collection keep/remove labels (`message_id`), loaded through the shared registry.
- `shared/embeddings/bedrock.py`: Titan embeddings for theme mapping.
- `experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py`: three-group label logic reference.
- `STUDY_2_RESULTS_FULL`: trial-level rows for Q6 (moderator party).
- `outputs/shared/label_matrix.parquet`: Step 6 output (sole label input for Step 7 analysis).
- `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`: Step 5 output.
- `outputs/shared/self_consistency/<run_timestamp>/scores.json`: Step 6 output.
- `data/post_split/test_post_ids.csv`: enforce test-only analyses.

## Files allowed to change

- `experiments/llm_feature_generation_study_2_2026_09_24/src/map_june_themes.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/src/analyze.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/src/write_results.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/tests/test_map_june_themes.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/tests/test_analyze.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/tests/test_write_results.py`: create.
- `experiments/llm_feature_generation_study_2_2026_09_24/RESULTS.md`: final content.
- `experiments/llm_feature_generation_study_2_2026_09_24/outputs/<arm>/analysis/<run_timestamp>/`: Q1 to Q7 JSON and tables.
- `experiments/llm_feature_generation_study_2_2026_09_24/outputs/shared/june_theme_map/<run_timestamp>/`: mapping artifacts.

## Files forbidden to change

- `shared/`, other `experiments/*` (read June collection JSON only).
- `docs/plans/.../plan.md`, sibling step files.
- `src/s3_sync.py` (call only).
- `src/llm_client.py`, `build_codebook.py`, `label_posts.py`, `self_consistency.py`.
- `data/post_split/*`, `data/feature_synonyms.csv`.

## Implementation phases (TDD: mandatory order)

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Callers, Q1 to Q7 mapping, out-of-scope | Listed |
| 2: Scaffold | Three modules; stubs | Imports resolve |
| 3: Contracts | Analysis output schemas, CLI flags | Stubs only |
| 4: Test design | Failing tests below | Right failures |
| 5: Implement | One Q or module per commit | Tests green |
| 6: Done | Full step pytest + CLI on fixtures | Criteria met |

### Phase 4: Named tests and assertions

| Test name | Given | When | Assert |
|-----------|-------|------|--------|
| `test_load_june_themes_reads_132_themes` | Glob on stage-2 JSON dir | `load_june_themes()` | `len(themes) == 132`; each has `id`, `label` |
| `test_map_june_embeds_name_plus_definition` | Mock Titan embed | `embed_feature_text(name, definition)` | Input string equals `"{name}. {definition}"` |
| `test_map_june_writes_rank1_table` | 3 codebook features, 132 themes | `map_june_themes --write` | CSV columns: `feature_id`, `june_theme_id`, `june_theme_label`, `cosine_similarity`, `rank` (rank 1 only; no human confirmation) |
| `test_analyze_filters_test_split_only` | Matrix with discovery and test rows | `load_test_labels()` | All rows `split == "test"`; count matches `test_post_ids.csv` |
| `test_q1_replication_uses_september_only_on_june_catalog` | Test matrix with union and september_only modal labels | `run_q1_replication()` | Replication subset is `in_june_catalog` test posts with september_only labels only |
| `test_q1_prevalence_bh_correction` | Test labels fixture (union modal labels) | `run_q1()` | Output includes raw p-values and BH-adjusted q-values; only test posts |
| `test_q2_stance_concordance` | Original+mirror labels per post | `run_q2()` | Per-feature concordance rate on test posts |
| `test_q3_flip_mismatch_rate` | Paired original/mirror presence | `run_q3()` | Per-feature rates: orig present mirror absent; mirror present orig absent |
| `test_q4_logistic_auc_log_loss` | Feature matrix + modal_decision | `run_q4()` | JSON has `auc` and `log_loss` per model arm; test split only |
| `test_q5_three_group_prevalence` | Posts with `three_group_label` | `run_q5()` | Groups: unanimous_keep, split, unanimous_remove; N per group reported |
| `test_q6_party_stance_feature_table` | Trial-level fixture | `run_q6()` | Columns include moderator party, post stance, feature_id, remove rate |
| `test_q7_nested_models_delta_auc` | Features + toxicity + stance | `run_q7()` | `delta_auc` for features-added model vs covariates-only |
| `test_write_results_includes_caveats` | Analysis dir fixture | `write_results.main()` | `RESULTS.md` contains `gpt-5.4-nano`, `gpt-6-luna`, and provisional LLM labels text |
| `test_write_results_flags_low_self_consistency` | scores.json with `cb_042` below 0.90 | `write_results` | `RESULTS.md` lists `cb_042` under self-consistency flags |
| `test_no_discovery_rows_in_q1_q7_metrics` | Spy on dataframe filter | Each `run_q*` | Zero rows with `split == discovery` in computation |

### Phase 5: Implementation units (dependency order)

1. `load_june_themes()`: parse all shards under `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/*.json`, then dedupe by theme `id`.
2. `map_june_themes`: Titan embed codebook features and June themes, compute cosine similarity, and write `theme_map.csv` with rank-1 nearest theme and `cosine_similarity` per feature. Set provisional `june_theme_id` on the codebook copy in map output, and do not mutate the approved codebook file.
3. `analyze.run_all`: primary run using primary ablation settings (mixed batches, HDBSCAN seed 42, modal labels, attention_pass filter, paired arm for June theme replication comparisons).
4. `analyze.run_ablations`: loop ablation axes (see below).
5. `write_results`: merge `summary_tables.md`, self-consistency flags, caveats, Q1 to Q7 tables into `RESULTS.md`.
6. `s3_sync --paths outputs data/post_split data/feature_synonyms.csv RESULTS.md`.

## Pass / fail criteria

### Must pass

- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_study_2_2026_09_24/tests/test_map_june_themes.py experiments/llm_feature_generation_study_2_2026_09_24/tests/test_analyze.py experiments/llm_feature_generation_study_2_2026_09_24/tests/test_write_results.py -q` exits 0.
- Full suite: `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_study_2_2026_09_24/tests -q` exits 0.
- Every Q1 to Q7 JSON under `outputs/<arm>/analysis/<run_timestamp>/` computed with `split == test` only.
- `RESULTS.md` answers Q1 to Q7 with tables and documents all ablation axes from plan.md.
- `RESULTS.md` states: (1) The June feature run used `gpt-5.4-nano`, Study 2 labeling used `gpt-6-luna`, and replication mixes model and data change. (2) Labels are provisional LLM labels without human validation.
- `outputs/shared/june_theme_map/<run_timestamp>/theme_map.csv` exists (rank-1 mapping per feature with similarity scores).
- S3 upload completes for experiment prefix.

### Must fail (until implemented)

- `analyze` including discovery rows in Q1 to Q7 metrics.
- `map_june_themes` with missing stage-2 directory.

## Commands (exact)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

CODEBOOK=outputs/shared/codebook/approved_<run_timestamp>/codebook.json
LABEL_MATRIX=outputs/shared/label_matrix.parquet
SELF_CONSISTENCY=outputs/shared/self_consistency/<run_timestamp>/scores.json

# June theme mapping (Step 7 owner)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.map_june_themes \
  --codebook "$CODEBOOK" \
  --june-themes-dir experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981 \
  --write

# Primary analysis on held-out test set
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --june-map outputs/shared/june_theme_map/<run_timestamp>/theme_map.csv \
  --write

# Ablations (same --split test)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation text_arm --values original_only,mirror_only,paired

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation batch_design --values mixed,single_class

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation label_definition --values modal,unanimous,three_group

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation participant_filter --values all,attention_pass,september_only

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation label_source --values union,september_only

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation clustering --values hdbscan,kmeans,docfreq

PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.analyze \
  --split test \
  --codebook "$CODEBOOK" \
  --label-matrix "$LABEL_MATRIX" \
  --write \
  --ablation seed --values 42,43,44

# Write RESULTS.md
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.write_results \
  --analysis-dir outputs/paired/analysis/<run_timestamp> \
  --self-consistency "$SELF_CONSISTENCY" \
  --june-map outputs/shared/june_theme_map/<run_timestamp>/theme_map.csv

# Upload everything
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_study_2_2026_09_24.src.s3_sync \
  --paths outputs data/post_split data/feature_synonyms.csv RESULTS.md

# Tests
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_study_2_2026_09_24/tests/test_map_june_themes.py \
  experiments/llm_feature_generation_study_2_2026_09_24/tests/test_analyze.py \
  experiments/llm_feature_generation_study_2_2026_09_24/tests/test_write_results.py -q

PYTHONPATH=. uv run pytest experiments/llm_feature_generation_study_2_2026_09_24/tests -q
```

### Expected output (representative lines)

```
june_themes_loaded=132
Wrote outputs/shared/june_theme_map/2026-09-24T16-00-00/theme_map.csv
analyze split=test n_posts=10001
Wrote outputs/paired/analysis/2026-09-24T16-05-00/q1_replication.json
...
Wrote experiments/llm_feature_generation_study_2_2026_09_24/RESULTS.md
s3_uploaded_prefix=s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_study_2_2026_09_24/
```

## Artifact contract (this step's outputs)

### June theme map (`outputs/shared/june_theme_map/<run_timestamp>/`)

| File | Content |
|------|---------|
| `theme_map.csv` | `feature_id`, `feature_name`, `june_theme_id`, `june_theme_label`, `cosine_similarity`, `rank` (1 = nearest; used provisionally in analysis) |
| `theme_map.md` | Human-readable table listing similarity scores |
| `metadata.json` | `june_themes_dir`, `n_themes`, `bedrock_model_id`, `built_at` |

**June stage-2 theme source:** `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/*.json` (132 themes per June collection `RESULTS.md`).

**June theme JSON parser:** Read each `*.json` in the themes dir, extract `result.themes[]`, and build `theme_id`, `label`, and `definition_text` by joining `defining_features` with `; `.

### Analysis outputs (`outputs/<arm>/analysis/<run_timestamp>/`)

| File | Purpose |
|------|---------|
| `q1_replication.json` | Feature prevalence keep vs remove on test set (union labels); BH-adjusted tests; June theme replication on June catalog test posts using september_only labels; themes replicated / new / disappeared |
| `q2_stance_invariance.json` | Per-feature original-mirror concordance on test posts |
| `q3_flip_fidelity.json` | Per-feature mismatch rates (orig on mirror off; mirror on orig off) |
| `q4_prediction.json` | Logistic models: original_only, mirror_only, paired, combined; `auc`, `log_loss` |
| `q5_disagreement.json` | Three-group prevalence on eligible test posts; N per group |
| `q6_party_interaction.json` | Moderator party x post stance x feature presence (remove trials) |
| `q7_incremental_auc.json` | Nested models: covariates only vs covariates + features; `delta_auc`, `log_loss` |
| `summary_tables.md` | Markdown tables for `write_results` |
| `ablations/` | Subdirs per ablation axis with parallel JSON summaries |

### Q1 to Q7 methods (test split only)

| Question | Method | Primary table in RESULTS.md |
|----------|--------|----------------------------|
| **Q1** | Feature prevalence by `modal_decision` on test posts (union labels by default); two-proportion or chi-square per feature; Benjamini-Hochberg across features. Map features to June themes via rank-1 `theme_map.csv` (cosine similarity reported; mapping provisional). For June theme replication, restrict to `in_june_catalog` test posts and use `participant_filter=september_only` modal labels (June themes were mined from June labels). Report which June themes replicate, which features are new, which June themes disappear. Discovery-half labels used only in a separate descriptive appendix table (not hypothesis tests). | `q1_feature_prevalence.csv`, `q1_june_replication.csv` |
| **Q2** | Per feature, concordance rate = share of test posts where original and mirror labels agree; classify stance-invariant (high concordance) vs stance-specific (low). BH correction across features. | `q2_stance_invariance.csv` |
| **Q3** | Per feature on test posts: `P(orig present AND mirror absent)` and reverse; report mismatch rates. | `q3_flip_fidelity.csv` |
| **Q4** | Logistic regression: `modal_decision` ~ feature vector per arm (original columns, mirror columns, paired, combined/diff). Report AUC and log loss on test split. | `q4_prediction_auc.csv` |
| **Q5** | Among test posts with non-null `three_group_label`, compare feature prevalence across unanimous_keep, split, unanimous_remove; BH correction. Report N per group. | `q5_disagreement.csv` |
| **Q6** | Trial-level: moderator party x post stance x feature presence for remove-labeled trials on test posts; BH correction on interaction contrasts. | `q6_party_interaction.csv` |
| **Q7** | Nested logistic: base = toxicity bucket + stance; full = base + features. Compare AUC and log loss; report delta AUC. | `q7_incremental_auc.csv` |

### Ablation axes (document in RESULTS.md)

| Axis | Values | Notes |
|------|--------|-------|
| Text arm | `original_only`, `mirror_only`, `paired` | Primary: `paired` for June theme replication |
| Batch design | `mixed`, `single_class` | Discovery-stage features; compare downstream if separate codebooks exist |
| Label definition | `modal`, `unanimous`, `three_group` | `three_group` only on eligible posts for Q5 |
| Label source | `union`, `september_only` | `union` | Q1 replication uses september_only on June catalog posts |
| Participant filter | `all`, `attention_pass`, `september_only` | `attention_pass` |
| Clustering | `hdbscan`, `kmeans`, `docfreq` | Compare baseline ladders from Steps 2 and 4 |
| Random seeds | `42`, `43`, `44` | Cluster stability sensitivity |

### `RESULTS.md` required sections

1. Summary (model, split sizes, codebook size, labeling cost).
2. Caveats: provisional LLM labels (no human validation); June collection `gpt-5.4-nano` vs September collection `gpt-6-luna`.
3. Self-consistency: features below 90% flagged, not dropped.
4. Q1 to Q7 tables (test set only).
5. Ablation summary.
6. June catalog overlap: replication / new / disappeared themes on June catalog posts with september_only labels (descriptive + test-set prevalence); provisional rank-1 theme mapping with cosine similarity scores.
7. What is not answerable (from plan.md).

## Human gates (if any)

This step has no human gates. June collection mapping picks the automatic rank-1 nearest theme by Titan cosine similarity. `RESULTS.md` states that the mapping is provisional and lists the similarity score for each match.

## Commit message template

`step7: analyze test set Q1-Q7 and write RESULTS.md`

## Handoff (experiment complete)

- `experiments/llm_feature_generation_study_2_2026_09_24/RESULTS.md` committed.
- All artifacts under `s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_study_2_2026_09_24/`.
- `uv run pytest experiments/llm_feature_generation_study_2_2026_09_24/tests -q` passes in CI.
