# Results

Date: 2026-09-24. Status: Pipeline complete. Human topic review is still pending.

BERTopic on 18,899 Study Phase 2 Part 3 stimulus posts, original text and mirrored text. Topics were fit on text only. Keep/remove decisions were joined afterwards. The fit drops duplicate originals and identical original-mirror pairs before clustering.

## Setup

| Setting | Value |
| --- | --- |
| Embedding | `amazon.titan-embed-text-v2:0`, 256-d, L2-normalized |
| UMAP | 15 neighbors, 5 components, min distance 0, cosine, seed 42 |
| HDBSCAN | min cluster size 15, euclidean, eom |
| Vectorizer | English stopwords, `min_df=2` |
| LLM labels | `gpt-5.4-nano` |
| Fit corpus | All deduplicated stimuli |
| Outcome corpus | Rated posts with `n_raters >= 3` |

Dedupe drops 173 duplicate originals, then 28 pairs whose mirror text equals the original (35 such pairs existed before the duplicate drop). The fit uses 18,698 posts.

## Production counts

| Role | Docs fitted | Topics (excl. noise) | Noise docs | Noise share |
| --- | ---: | ---: | ---: | ---: |
| original | 18,698 | 92 | 7,386 | 39.5% |
| mirror | 18,698 | 83 | 7,572 | 40.5% |
| joint | 37,396 | 143 | 17,123 | 45.8% |

Runs: `outputs/topics/original/20260924T053045Z`, `outputs/topics/mirror/20260924T053136Z`, `outputs/topics/joint/20260924T053302Z`.

## Topic labels

Largest original topics and largest joint topics are in the label files, with `topic_id`, document count, and the LLM label. Full tables:

- `outputs/labels/original/20260924T053520Z/topic_labels.parquet`
- `outputs/labels/joint/20260924T053831Z/topic_labels.parquet`

## Q1. Part 3 topics versus Part 2

8,899 Part 3 posts are in the Part 2 stimulus catalog. 7,689 of them already have a Part 2 topic in the committed Part 2 assignments. The other 1,210 get the nearest Part 2 topic centroid. The primary comparison uses the directly assigned posts that also remain after dedupe (8,700 paired posts).

| Comparison | ARI | NMI |
| --- | ---: | ---: |
| Direct Part 2 assignments only | 0.41 | 0.60 |
| Including centroid-filled posts | 0.38 | 0.58 |

Part 3 topic assignments overlap substantially with Part 2 assignments, and the topic shares also shift. Shares, the crosstab, and facet charts are in `outputs/analyses/part2_comparison/20260924T053524Z`.

## Q2. Do mirrors stay on the original's topic?

Mirrors were assigned with the fitted original model (`transform`, not a second fit).

| Metric | Rate |
| --- | ---: |
| Same topic, including the noise topic | 22.8% |
| Same topic, excluding pairs where either side is noise | 34.7% |

4,272 of 18,698 pairs match. Most mirrors do not land on their original's topic.

A separate mirror model, matched to the original model by Hungarian assignment on topic-centroid cosine similarity, has ARI 0.15 and NMI 0.33 on the 18,698 paired posts (83 topics matched).

## Q3. Is there a role skew in the joint model?

In the joint model, a pair is co-assigned 49.7% of the time. 70 of 144 topics (including noise) have an original-text share outside 35% to 65% after a false-discovery-rate correction. Some joint topics are mostly originals or mostly mirrors. That skew is an association. It does not by itself show that the mirror generator caused it.

## Q4. Vocabulary contrast

Within each non-noise joint topic, terms are ranked by Monroe log-odds with a Dirichlet prior of 0.01. Each topic keeps 15 terms favoring the original and 15 favoring the mirror, or fewer when the topic has fewer terms. Table: `outputs/analyses/cross_role/20260924T053941Z/q4_keyword_contrast.parquet` (143 topics).

## Q5. Which topics have the lowest keep rates?

Among posts with at least 3 raters, the keep rate is 69.4% (15,846 posts). The noise topic (6,443 posts) is close to that, at 68.9%. 37 non-noise topics differ from the overall rate after a Benjamini-Hochberg correction. Significance uses cluster bootstraps of 2,000 resamples by post. Interval columns are in the outcomes tables.

Democrat ratings keep 68.7% of the time. Republican ratings keep 70.0%. Those are rating-level cuts on the same pair decision.

Lowest keep rates are on topics whose automatic labels mention Trump hostility or conviction. Those labels are not human-reviewed:

| Topic | Posts | Keep rate | Label |
| --- | ---: | ---: | --- |
| 17 | 107 | 30.7% | Anti-Trump profanity and hostility |
| 42 | 35 | 40.7% | Accusations against Donald Trump and calls for conviction |
| 81 | 20 | 47.2% | Trump as a fascist |

Highest keep rates:

| Topic | Posts | Keep rate | Label |
| --- | ---: | ---: | --- |
| 84 | 12 | 91.4% | Reproductive freedom and abortion rights |
| 65 | 20 | 87.0% | Climate conservation campaigns |
| 66 | 24 | 85.9% | US reshoring of manufacturing jobs |

Facet cells are reported only when a topic has at least 30 posts in that facet value (60 stance cells, 64 toxicity cells, 60 platform cells). These are associations. The decision is one keep/remove for the pair, not a separate decision for each text. Output: `outputs/analyses/outcomes/20260924T053611Z`.

## Ablation sensitivity

Summary: `outputs/ablations/summary.csv` (run `20260924T055615Z`).

- A0. K-Means on Titan vectors. Among k in {5, 10, 15, 20, 25, 30}, silhouette on a 2,000-row sample is highest at k=5. That pick is automatic. Sample files are under `outputs/ablations/a0_naive/20260924T055615Z/` for a person to replace `k_chosen`.
- A1. UMAP seeds 42 to 46. Seed 42 matches the production fit (ARI 1.0). Mean pairwise ARI across seeds is 0.57, so the partition is only moderately stable. Topic count moves from 86 to 99.
- A2. Minimum cluster size 15, 30, and 50. Topic count falls from 92 to 42 to 30. Noise share stays near 36% to 40%.
- A3. MiniLM instead of Titan. 128 topics, noise share 34.9%. Spearman correlation of per-topic keep rates versus production, after centroid matching, is 0.76. The keep-rate ranking is related but not the same.
- A4. Fit design, no refit. Joint co-assignment is 49.7% with 70 role-dominated topics. Assigning mirrors with the original model agrees 22.8% of the time and flags 44 role-dominated topics. Separate original and mirror models agree on raw topic ids 22.4% of the time. Those ids are not aligned, so the separate-model role count (9) is not a signature of the mirror text.
- A5. `reduce_outliers` with strategy `embeddings` moves noise from 39.5% to 0% on a refit. Spearman of keep rates versus production is 0.93, so the keep-rate ranking mostly survives reassignment.

## Human review export (pending)

Samples of 10 centroid neighbors and 10 random documents per topic, plus 30 noise documents:

- `outputs/reviews/20260924T055615Z/review_original.md`
- `outputs/reviews/20260924T055615Z/review_joint.md`
- `outputs/reviews/20260924T055615Z/samples.parquet`

`review_notes.md` is not in this run. A person still needs to read the two markdown files and record whether the topics are acceptable.

## Limitations

Topics are post-hoc. The keep/remove label is one decision for the pair, and a post can have several raters. Titan vectors for posts missing from the identity cache were backfilled. UMAP still moves with the seed (A1). MiniLM changes the topic count and the keep-rate ranking (A3). The K-Means k was not chosen by a person.

## Artifact paths

- Topics: `outputs/topics/{original,mirror,joint}/20260924T053045Z` and the mirror and joint timestamps above
- Labels: `outputs/labels/{original,mirror,joint}/`
- Figures: `outputs/figures/{original,mirror,joint}/` and the analysis `figures/` directories
- Cross-role: `outputs/analyses/cross_role/20260924T053941Z`
- Outcomes: `outputs/analyses/outcomes/20260924T053611Z`
- Part 2 comparison: `outputs/analyses/part2_comparison/20260924T053524Z`
- Ablations: `outputs/ablations/summary.csv`
- Review samples (no `review_notes.md` yet): `outputs/reviews/20260924T055615Z`

## S3 storage

`s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_part3_2026_09_24/`

Embedding arrays, BERTopic `model/` directories, `umap_2d.npy`, `probabilities.npy`, and HTML figures are gitignored and stored under that prefix. Assignments, labels, analysis tables, review markdown, figure PNGs, and `outputs/ablations/summary.csv` are in git. Upload on 2026-09-24 wrote 275 output files (463,659,777 bytes) plus `outputs/upload_manifest.json`. S3 holds 276 objects under the prefix.
