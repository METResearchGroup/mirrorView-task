# Results

Date: 2026-09-24. Status: Pipeline complete on the Part 2 + Part 3 union (20,000 stimuli). Human topic review is still pending.

BERTopic on the combined Phase 2 Part 2 and Part 3 stimulus catalog: original text, mirrored text, and a pooled original+mirror joint fit. Topics are fit on text only; keep/remove labels are joined afterward. Dedupe drops duplicate originals and identical original–mirror pairs before clustering.

## Setup

| Setting | Value |
| --- | --- |
| Embedding | `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized |
| UMAP | 15 neighbors, 5 components, min distance 0, cosine, seed 42 |
| HDBSCAN | min cluster size 15, euclidean, eom |
| Vectorizer | English stopwords, `min_df=2` |
| LLM labels | `gpt-5.4-nano` |
| Fit corpus | All deduplicated stimuli (19,763 posts; 39,526 joint rows) |
| Outcome corpus | Posts with `n_raters >= 3` (drops 0 posts on this union) |

| Dedupe step | Removed | Remaining |
| --- | ---: | ---: |
| Raw stimuli | — | 20,000 |
| Duplicate `original_text` (first `post_id` kept) | 205 | 19,795 |
| Identical original and mirror text | 32 | **19,763** |

Titan embeddings for all 20,000 stimuli: 18,899 reused from the earlier Part 3 cache, 1,101 from the identity cache, 0 new Bedrock calls (`outputs/embeddings/original/metadata.json` provenance).

## Production counts

| Role | Docs fitted | Topics (excl. noise) | Noise docs | Noise share |
| --- | ---: | ---: | ---: | ---: |
| original | 19,763 | 100 | 8,369 | 42.3% |
| mirror | 19,763 | 97 | 8,857 | 44.8% |
| joint | 39,526 | 154 | 21,398 | 54.1% |

| Artifact | Run ID |
| --- | --- |
| Topics original | `outputs/topics/original/20260924T135151Z` |
| Topics mirror | `outputs/topics/mirror/20260924T135244Z` |
| Topics joint | `outputs/topics/joint/20260924T135414Z` |
| Labels original / mirror / joint | `20260924T135628Z` / `20260924T135739Z` / `20260924T135924Z` |
| Mirror via original assignments | `outputs/assignments/mirror_via_original/20260924T135936Z` |
| Cross-role analyses (Q2–Q4) | `outputs/analyses/cross_role/20260924T135955Z` |
| Part 2 comparison (Q1) | `outputs/analyses/part2_comparison/20260924T135958Z` |
| Outcomes (Q5) | `outputs/analyses/outcomes/20260924T140052Z` |
| Figures | `outputs/figures/{original,mirror,joint}/20260924T140103Z` (and `140110Z`, `140117Z`) |
| Ablations | `outputs/ablations/*/20260924T140407Z`, summary `outputs/ablations/summary.csv` |
| Review samples | `outputs/reviews/20260924T140407Z/` |

## Largest topics (LLM labels)

Original model (`outputs/labels/original/20260924T135628Z/topic_labels.parquet`):

| Topic | Docs | Label |
| ---: | ---: | --- |
| 0 | 1,122 | Green New Deal climate and fossil fuel policy |
| 1 | 862 | Border security and immigration enforcement (deportations, due process, and legal status) |
| 2 | 851 | MAGA vs. U.S. political institutions and rule-of-law / authoritarianism advocacy |
| 3 | 690 | Abortion rights and access debate (Roe v. Wade, pro-choice vs pro-life) |
| 4 | 636 | Critiques of Trump’s media strategy, lying, and divisive behavior |

Joint model (`outputs/labels/joint/20260924T135924Z/topic_labels.parquet`):

| Topic | Docs | Label |
| ---: | ---: | --- |
| 0 | 3,424 | Second Amendment and gun control debate (rights vs laws) |
| 1 | 1,300 | Pro-choice reproductive rights and bodily autonomy |
| 2 | 644 | Voter suppression and election integrity (voting rights, ID laws, voter rolls, and election fraud concerns) |
| 3 | 623 | Anti–Joe Biden corruption and senility claims |
| 4 | 601 | MAGA conspiracy and electoral integrity debate |

## Q1. Union fit versus the Part 2 production run

All 10,000 Part 2 catalog posts are inside this fit. Q1 compares topic assignments from the union original model (`20260924T135151Z`) to the committed Part 2 original run `experiments/bertopic_modeling_2026_08_05/outputs/topics/original/20260805T135853Z` (`framing`: `union_fit_vs_part2_run`). Primary pairing uses posts with a direct Part 2 assignment that survive dedupe (8,579 posts). Centroid fill covers another 1,186 Part 2-catalog posts in the union.

| Comparison | ARI | NMI | n posts |
| --- | ---: | ---: | ---: |
| Direct Part 2 assignments only (primary) | 0.259 | 0.555 | 8,579 |
| Including centroid-filled catalog posts | 0.235 | 0.539 | 9,765 |

| Subset in union fit | Posts | Noise share (original model) |
| --- | ---: | ---: |
| Part 2 catalog (`n=9,765`) | 9,765 | 40.0% |
| Part 3-only posts (`n=9,998`) | 9,998 | 44.6% |

Shares, crosstab, and facet charts: `outputs/analyses/part2_comparison/20260924T135958Z`.

## Q2. Do mirrors stay on the original's topic?

Mirrors are assigned with the fitted original model (`transform` via `outputs/assignments/mirror_via_original/20260924T135936Z`).

| Metric | Rate | n pairs |
| --- | ---: | ---: |
| Same topic, including noise | 19.5% | 19,763 |
| Same topic, excluding pairs where either side is noise | 30.5% | — |

3,846 of 19,763 pairs match on raw topic id. A separately fitted mirror model, aligned to the original model by Hungarian matching on topic-centroid cosine similarity, yields ARI 0.094 and NMI 0.298 on the paired posts (97 topics matched). Details: `outputs/analyses/cross_role/20260924T135955Z/q2_ari_nmi.json`.

## Q3. Role skew in the joint model

| Metric | Value |
| --- | ---: |
| Pair co-assignment rate | 59.0% (11,653 / 19,763) |
| Role-dominated topics (FDR) | 75 of 155 (incl. noise) |

Co-assignment and role shares: `outputs/analyses/cross_role/20260924T135955Z/q3_coassignment.json`, `q3_role_shares.parquet`. Role dominance is an association; it does not by itself show that mirror generation caused the skew.

## Q4. Vocabulary contrast

Within each non-noise joint topic, terms are ranked by Monroe log-odds with Dirichlet prior 0.01. Each topic keeps up to 15 terms favoring the original and 15 favoring the mirror. Table: `outputs/analyses/cross_role/20260924T135955Z/q4_keyword_contrast.parquet` (154 topics).

## Q5. Topic-level keep rates

All 19,763 deduplicated posts have at least 3 raters (`n_posts_dropped_min_raters`: 0). Overall keep rate: **69.8%**. The noise topic (8,369 posts) is 69.8%. **50** non-noise topics differ from the overall rate after Benjamini–Hochberg correction (`fdr_alpha` 0.05). Significance uses cluster bootstraps of 2,000 resamples by post.

| Party (rating-level) | Keep rate |
| --- | ---: |
| Democrat | 69.4% |
| Republican | 70.0% |

Lowest keep rates among non-noise original topics (labels not human-reviewed):

| Topic | Posts | Keep rate | Label |
| ---: | ---: | ---: | --- |
| 19 | 144 | 31.7% | Anti-Trump Hate Speech and Harassment |
| 90 | 19 | 45.0% | Calling Trump a fascist and criticizing fascism in America |
| 38 | 56 | 46.9% | Accusations of Trump as a rapist, pedophile, and criminal |

Highest keep rates:

| Topic | Posts | Keep rate | Label |
| ---: | ---: | ---: | --- |
| 79 | 23 | 90.7% | National Gun Violence Awareness Month (Wear Orange) and Community Safety Action |
| 68 | 27 | 88.9% | Global Climate Action for Rainforests, Wetlands, and Reefs Conservation |
| 99 | 15 | 87.7% | Florida Property Tax & Homestead Tax Policy Debate (DeSantis) |

Facet cells are reported only when a topic has at least 30 posts in that facet value (70 stance, 78 toxicity, 74 platform cells). The keep/remove decision is one label per post pair. Tables: `outputs/analyses/outcomes/20260924T140052Z/`.

## Ablation sensitivity

Summary: `outputs/ablations/summary.csv` (union production run `20260924T140407Z`).

| Ablation | Result |
| --- | --- |
| A0 K-Means on Titan | Highest silhouette on a 2,000-row sample at k=5 (automatic; samples under `outputs/ablations/a0_naive/20260924T140407Z/`) |
| A1 UMAP seeds 42–46 | Seed 42 matches production (ARI 1.0). Mean pairwise ARI across seeds **0.558**; topic count ranges ~90–103 |
| A2 `min_cluster_size` 15 / 30 / 50 | **100 / 48 / 32** topics; noise share ~37–42% |
| A3 MiniLM vs Titan | 132 topics, **32.5%** noise; Spearman of per-topic keep rates vs production **0.749** (centroid matching) |
| A4 Fit design (no refit) | Separate original+mirror models: Q2 agreement **22.5%**, 5 role-dominated topics. Joint: **59.0%** co-assign, **75** role-dominated. Original assigns mirror: **19.5%**, 54 role-dominated |
| A5 `reduce_outliers` (`embeddings`) | Noise 42.3% → 0% on refit; Spearman keep-rate ranking vs production **0.950** |

## Human review export (pending)

Samples of 10 centroid neighbors and 10 random documents per topic, plus 30 noise documents:

- `outputs/reviews/20260924T140407Z/review_original.md`
- `outputs/reviews/20260924T140407Z/review_joint.md`
- `outputs/reviews/20260924T140407Z/samples.parquet`

`review_notes.md` is not in this run. A person still needs to read the markdown files and record whether the topics are acceptable.

## Changes from the Part 3-only run

The earlier same-day run fit only the 18,899-post Part 3 catalog (`outputs/topics/original/20260924T053045Z` and matching analysis timestamps). The union rerun adds all Part 2 catalog posts, pools Part 2 and Part 3 keep/remove ratings, and reframes Q1 as union-fit vs the Part 2 production run.

| Metric | Part 3-only run | Union run | Notes |
| --- | ---: | ---: | --- |
| Stimuli / fit posts | 18,698 | 19,763 | Union dedupe: 205 duplicate originals, 32 identical pairs |
| Topics original / mirror / joint | 92 / 83 / 143 | 100 / 97 / 154 | |
| Noise share original / mirror / joint | 39.5% / 40.5% / 45.8% | 42.3% / 44.8% / 54.1% | |
| Q1 ARI / NMI (primary n) | 0.41 / 0.60 (8,700) | 0.259 / 0.555 (8,579) | Q1 reframed to `union_fit_vs_part2_run`; Part 2 posts are in the fit |
| Q2 same-topic all / excl. noise | 22.8% / 34.7% | 19.5% / 30.5% | |
| Q2 Hungarian ARI (orig vs mirror fit) | 0.15 | 0.094 | |
| Q3 joint co-assign | 49.7% | 59.0% | |
| Q3 role-dominated topics | 70 | 75 | |
| Q5 posts analyzed | 15,846 | 19,763 | Min-3-raters filter kept but drops **0** posts on the union |
| Q5 overall keep rate | 69.4% | 69.8% | |
| Q5 BH-significant topics | 37 | 50 | |
| A1 mean pairwise UMAP ARI | 0.571 | 0.558 | |
| A3 MiniLM topics / noise / Q5 Spearman | 128 / 34.9% / 0.76 | 132 / 32.5% / 0.749 | |

Pooling Part 2 and Part 3 ratings changes the modal keep/remove decision on **1,161** of **8,866** overlap posts that Part 3 alone had rated (same post ids in both catalogs).

## Limitations

Topics are post-hoc. Keep/remove is one decision per pair with multiple raters per post. Titan vectors for posts missing from the Part 3 cache were satisfied from the identity cache (no new Bedrock calls). UMAP partitions move with the seed (A1). MiniLM shifts topic count and keep-rate ranking (A3). K-Means k in A0 was not chosen by a person.

## S3 storage

`s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/`

Large artifacts (embedding arrays, BERTopic `model/` directories, `umap_2d.npy`, HTML figures) are gitignored and stored under that prefix. Assignments, labels, analysis tables, review markdown, figure PNGs, and `outputs/ablations/summary.csv` are in git. Upload on 2026-09-24: **476** files, **710,666,913** bytes (`outputs/upload_manifest.json`).
