# Proposal: Break down high-toxicity posts that are kept versus removed

Scope: the observation in `docs/study_updates/STUDY_2_WRITEUP.md` that high-toxicity posts are kept at 49.8% (4,983 posts), and the request to break that set down by stored topics and stored features. There is no GitHub issue. This proposal covers one new experiment that only reads the stored topic assignments and the stored feature labels.

## Overview

High-toxicity posts are kept at 49.8% across 4,983 posts. That 49.8% is the average of each post's own keep rate, from `experiments/bertopic_original_mirror_study_2_2026_09_24/RESULTS.md`. The existing topic chart shows the keep rate inside each topic at each toxicity level. This experiment starts from the high-toxicity posts alone and separates the posts whose modal label is keep from the posts whose modal label is remove.

The join uses the stored topic assignments from the fit on the original posts and the stored feature labels. It keeps the 4,983 posts and writes two tables, one for topics and one for the 30 named features. Each row has the modal counts and the average keep rate, so the margin of the tables is the published 49.8%.

## Cross-cutting concerns

### Population

The population is the high-toxicity posts in the topic fit on the original posts, which is 4,983 posts (measured). The fit itself is 19,763 posts after `dedupe_stimuli` in `experiments/bertopic_original_mirror_study_2_2026_09_24/src/dedupe.py` drops duplicate originals and identical original-mirror pairs. Of the grouped posts, 2,892 are high toxicity (measured), so 4,983 minus 2,892 leaves 2,091 high-toxicity posts in the ungrouped topic (derived). The topic table includes that ungrouped row, plus one rollup row for grouped topics with fewer than 30 high-toxicity posts, so the post counts sum to 4,983.

The feature labels cover all 20,000 stimulus pairs, including 5,000 high-toxicity pairs (measured in `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` as `EXPECTED_TOXICITY_COUNTS`). The join keeps the 4,983 fit posts, so a high-toxicity post dropped by dedupe is out. If any of the 4,983 posts has no feature row, the run stops.

### Outcome

Keep versus remove is the `decision` column on `STUDY_2_KEEP_REMOVE_LABELS`. `shared/data/transformed/study_2/transform.py` sets `decision` to keep when keep votes strictly outnumber remove votes, and it sets every tie to remove. This experiment reads that column.

`keep_rate` on the same table is `n_keep / n_raters`. The published 49.8% is the mean of `keep_rate` over the 4,983 posts. The share of those posts with `decision` keep is a separate count, and it is not measured yet. Every output row reports the modal counts and the mean `keep_rate`.

### What is reused

| Input | Path | Symbol or file |
| --- | --- | --- |
| Modal label, keep rate, toxicity, text | `shared/data/dataloader.py` | `load_dataset(STUDY_2_KEEP_REMOVE_LABELS)` |
| Topic id per post | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/topics/original/20260924T135151Z/assignments.parquet` | columns `post_id`, `topic`, `text_role` |
| Topic name | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/labels/original/20260924T135628Z/topic_labels.parquet` | `topic_id`, `llm_label` |
| Topic display name | same rule as `display_label` in `experiments/bertopic_original_mirror_study_2_2026_09_24/src/export_map_data.py` | text of `llm_label` before the first ` (` |
| Feature 0/1 labels | `s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/step6_label_posts_with_features/post_feature_labels.parquet` | `post_id` plus one column per feature |
| Feature names | `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py` | `LABEL_TO_DETAIL` |
| Present cutoff already applied | `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` | `FEATURE_PRESENT_THRESHOLD` is 0.7 |
| Check against the existing topic-by-toxicity keep rates | `s3://mirrorview-experimental-artifacts/experiments/bertopic_original_mirror_study_2_2026_09_24/outputs/analyses/outcomes/20260924T140052Z/outcomes_by_topic_facet.csv` | facet `sample_toxicity_type` |

Downloads use `lib.aws.s3.S3`. The two source experiments stay unchanged. No new package is added. Plotting uses `matplotlib`, which is already a main dependency, so the run does not need the `bertopic` extra.

### Out of this experiment

Stance and rater party stay out. The writeup already reports both, and this question is about topics and features inside high toxicity. No bootstrap intervals. The writeup gets one section at the bottom, written from these tables.

## File structure

### Repository

```text
experiments/high_toxicity_kept_vs_removed_2026_10_07/
  README.md       title, then links to SETUP.md and RESULTS.md
  SETUP.md        which stored files the script reads
  RESULTS.md      the two tables, the two figures, and the excerpts
  src/analyze.py  join, topic table, feature table, figures, RESULTS.md
```

`experiments/bertopic_original_mirror_study_2_2026_09_24/` and `experiments/study_2_llm_based_feature_extraction_2026_09_29/` stay unchanged.

### S3

```text
s3://mirrorview-experimental-artifacts/experiments/high_toxicity_kept_vs_removed_2026_10_07/
  tables/topics.csv
  tables/features.csv
  figures/topic_composition.png
  figures/feature_presence_gap.png
```

The repo copy is `README.md`, `SETUP.md`, `RESULTS.md`, and `src/analyze.py`. The CSVs and PNGs are uploaded and are not committed.

## Schema and key interfaces

| Model | Lives in | Role |
| --- | --- | --- |
| Keep/remove row | `STUDY_2_KEEP_REMOVE_LABELS` (reused) | One post. Fields used: `post_id`, `decision`, `keep_rate`, `n_raters`, `sample_toxicity_type`, `original_text`. |
| Assignment row | original `assignments.parquet` (reused) | `post_id`, `topic`, `text_role`. The join keeps `text_role == "original"`. |
| Topic label row | `topic_labels.parquet` (reused) | `topic_id`, `llm_label`. Topic `-1` has a null `llm_label` and is named Ungrouped. |
| Feature label row | `post_feature_labels.parquet` (reused) | `post_id` and 30 integer columns, already 1 when the Jev probability is at least 0.7. |
| Joined post | memory only, inside `analyze.py` | One row per high-toxicity fit post. Not written. |
| Topic table | `tables/topics.csv` (new) | One row per topic with at least 30 high-toxicity posts, plus Ungrouped, plus Other grouped topics. |
| Feature table | `tables/features.csv` (new) | One row per feature in `LABEL_TO_DETAIL`. |

Topic table fields: `topic_id`, `topic_name`, `n_posts`, `n_modal_keep`, `n_modal_remove`, `share_of_modal_keep`, `share_of_modal_remove`, `mean_keep_rate`.

Feature table fields: `feature_key`, `name`, `n_present`, `presence_rate_modal_keep`, `presence_rate_modal_remove`, `presence_gap`, `mean_keep_rate_present`, `mean_keep_rate_absent`. `presence_gap` is the keep presence rate minus the remove presence rate.

`original_text` is used only to print excerpts. It is not stored in the CSVs.

## Steps

### Step 1: Join the high-toxicity posts

Read the keep/remove labels, the assignments from the fit on the original posts, the topic names, and the feature labels. Keep posts whose `sample_toxicity_type` is `sample_high_toxicity` and whose `post_id` is in those assignments. Assert the row count is 4,983. Assert every remaining post has a feature row and a topic id.

### Step 2: Write the topic table

Group the joined posts by topic. For each topic, count modal keep and modal remove, the share of each group, and the mean `keep_rate`. Keep topics with at least 30 posts, matching `FACET_MIN_POSTS` in `experiments/bertopic_original_mirror_study_2_2026_09_24/src/analyze_outcomes.py`. Roll the smaller grouped topics into one row. Keep Ungrouped as its own row. For every topic that also appears in `outcomes_by_topic_facet.csv` for `sample_high_toxicity`, `n_posts` and `mean_keep_rate` must match that file.

### Step 3: Write the feature table

For each of the 30 features, compute the presence rate among modal keep posts and among modal remove posts, and the mean `keep_rate` when the feature is present and when it is absent. Sort by the absolute presence gap. Step 7 of the feature experiment reports feature rates by toxicity for all 20,000 pairs, and feature rates by remove-vote count for the 15,113 pairs with five labels. This table reports feature rates for the 4,983 high-toxicity posts, split by modal keep and modal remove.

### Step 4: Write figures, excerpts, and RESULTS.md

Write two matplotlib figures. One shows each topic's share of the modal keep posts and its share of the modal remove posts. The other shows the presence gap for every feature. For the three topics with the largest absolute difference between those two shares, and the three features with the largest absolute presence gap, copy two modal keep excerpts and two modal remove excerpts from `original_text`, each truncated to 280 characters. Write the tables, figures, and excerpts into `RESULTS.md`, and upload the CSVs and PNGs.

## Expected results

A successful run reports the modal keep count and the modal remove count on the same 4,983 posts, and the mean `keep_rate` on those posts equals 49.8% (measured target). The ungrouped row has 2,091 posts (derived). The topic rows that overlap `outcomes_by_topic_facet.csv` match that file on `n_posts` and `mean_keep_rate`. The feature table has 30 rows.

Runtime is estimated at under 5 minutes, almost all of it downloading the three parquet files. Cost is $0, because the script makes no model calls. The tables are descriptive. They do not estimate an effect of topic or feature on the vote.

## Decisions

Confirmed on 2026-10-07.

1. **Ties stay in the remove group.** Confirmed. The analysis uses the stored `decision` label, so a tie is remove.
2. **Features stay at the stored 0.7 cutoff.** Confirmed. The analysis reads `post_feature_labels.parquet` only.
3. **No bootstrap intervals.** Confirmed. The tables print counts and rates only.
4. **RESULTS.md includes short excerpts.** Confirmed. Two kept and two removed excerpts for the three topics and three features with the largest gaps, truncated to 280 characters.
5. **The writeup gets a section at the bottom.** Changed from the recommendation to leave the writeup unchanged. The section is at the end of `docs/study_updates/STUDY_2_WRITEUP.md`.
