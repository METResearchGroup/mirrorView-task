# Previous experiments on Study Phase 2, Part 2 data

This is an inventory of experiments that used Study Phase 2, Part 2 data. It is meant to help decide what to rerun on the Part 3 collection (the `jspsych-mirror-view-2026-09-09` run, registered as `STUDY_PHASE_2_PART_3_*`).

How experiments were identified: a folder counts if its code loads a `STUDY_PHASE_2_PART_2_*` registry key or `shared/data/raw/study_phase_2_part_2/`, or if it consumes the outputs of an experiment that does. Folders containing several distinct experiments (arms, versions, or sub-analyses) are split into separate rows.

Part 2 registry keys referenced below:

- `KEEP_REMOVE_LABELS`: modal keep/remove label per post (about 8,791 posts).
- `KEEP_REMOVE_LABELS_UNANIMOUS_MIN3`: posts with at least 3 raters who all agreed.
- `RESULTS_FULL`: raw per-trial participant results.
- `USER_REFLECTION_FEEDBACK`: participants' free-text reflections and influence ratings.
- `STIMULI`: the original/mirror post pairs (`flips.csv`).

## 1. Experiments on Part 2 participant data (main rerun candidates)

These analyze participant behavior: labels, results, or reflections. Each should transfer to Part 3 once `STUDY_PHASE_2_PART_3_RESULTS_FULL` has the derived label tables.

### Descriptive analyses of keep/remove behavior

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Keep/remove rates by platform | Crosstab of modal keep/remove labels by source platform and toxicity (`KEEP_REMOVE_LABELS` + `STIMULI`). Reddit posts were removed most often (0.403 vs Bluesky 0.257, Twitter 0.230). High-toxicity removal was about 0.53–0.64 on every platform. | `experiments/compare_keep_remove_rates_across_integrations_2026_08_04/` |
| Unanimous vs majority keep/remove | Compares posts with unanimous vs split votes (n=3,718 posts with 3 or more raters; `RESULTS_FULL` + `STIMULI`). Share of high-toxicity posts rises steadily: 4.6% of unanimous-keep, 19.2% of majority-keep, 52.5% of majority-remove, 70.8% of unanimous-remove. Political stance does not separate keep from remove the way toxicity does. | `experiments/unanimous_vs_majority_labels_2026_08_08/` |
| BERTopic topics on original posts | BERTopic on Titan embeddings of about 8,790 original posts, joined to keep/remove labels. Found 53 topics (plus 3,030 noise documents). The largest topic is the U.S. gun debate (1,586 documents). | `experiments/bertopic_modeling_2026_08_05/` |

### LLM-derived features and themes

| Headline experiment | Description | Folder |
| --- | --- | --- |
| LLM feature → theme synthesis | Two-stage pipeline on a 50% subset of `KEEP_REMOVE_LABELS`: the LLM extracts features per batch, then combines them into themes (140 batches, 132 themes). Themes weighted toward removal include profanity/insults and dehumanizing language. | `experiments/llm_based_feature_generation_2026_07_31/` |
| LLM features + clusters: keep posts | 500 kept posts, 400 LLM features, 11 HDBSCAN clusters (266 noise). Example cluster: "Imperative policy or punishment demands." | `experiments/create_llm_features_2026_08_05/` (`--label-class keep`) |
| LLM features + clusters: remove posts | 500 removed posts, 400 LLM features, 13 HDBSCAN clusters (220 noise). Example cluster: "Profanity and sexual slur attacks." | `experiments/create_llm_features_2026_08_05/` (`--label-class remove`) |

### Predicting keep/remove

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Embedding classifiers + ablations | Logistic regression and XGBoost on Titan embeddings (`KEEP_REMOVE_LABELS`, n=8,791). Concatenating original and mirror embeddings performs about the same as original-only (LR test ROC-AUC ≈ 0.71). The original post drives predictability; mirror text adds little. | `experiments/predict_keep_remove_2026_07_01/models/{logistic_regression,xgboost}` |
| ModernBERT head-only fine-tune | Frozen ModernBERT encoder with a trained head, original text only. Test accuracy 0.694, F1 0.555, ROC-AUC 0.742, comparable to the embedding LR. | `experiments/predict_keep_remove_2026_07_01/models/modernbert` |
| LLM prompting baselines | One-shot and few-shot keep/remove prompts, including the Qwen3-Next-80B run used by the error analyses below. The results table has some placeholder rows. | `experiments/predict_keep_remove_2026_07_01/models/{llm_api,llm_finetuning}` |
| Prompt engineering (gpt-5.4-nano) | Control prompt vs a feature-informed prompt on 500 posts. Control F1 0.601 vs tuned 0.576; the 0.70 goal was not met. | `experiments/llm_prompt_engineering_2026_08_05/` |
| Prompt engineering v2 (Qwen 3.6 Plus) | Same design on 1,000 class-balanced posts. Control F1 0.628 vs tuned 0.700; the gain comes mostly from recall (0.574 → 0.818). | `experiments/llm_prompt_engineering_v2_2026_08_05/` |
| LoRA teachability: unanimous labels | Qwen3-4B LoRA on the balanced `KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` set (n=308). Test remove-F1 rose from 0.741 to 0.969. The test set is tiny. | `experiments/finetune_qwen_model_2026_08_08/` |
| LoRA teachability: modal labels | Same recipe on about 5,626 balanced modal labels. Remove-F1 fell from 0.721 to 0.696, but accuracy rose from 0.639 to 0.702: the baseline over-predicted "remove" (recall 0.93). | `experiments/larger_finetune_qwen_model_2026_08_08/` |

### Error analysis of LLM moderation

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Where Qwen errors live in embedding space | Uses the Qwen3-Next-80B predictions from `predict_keep_remove_2026_07_01`. Qwen was wrong on about 36% of 8,791 posts. A probe predicting which posts it gets wrong reaches only ROC-AUC ≈ 0.60, and clustering finds no stable high-error regions (best lift ≈ 1.12). The errors are spread out rather than concentrated. | `experiments/model_errors_analysis_2026_07_15/` |
| LLM features of Qwen errors | V1 pilot extracting linguistic features for true/false positives and negatives (≤320 posts). False removals skew toward high-arousal, conspiracy, and victimhood language. Missed removals read cooler and more policy-argumentative. V2 was not run. | `experiments/followup_model_error_analysis_2026_07_15/` |

### Participant reflections (free response)

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Influence-rating histogram | Distribution of the 1–7 pair-influence Likert rating (`USER_REFLECTION_FEEDBACK`): 1,177 users, 255 low and 922 high. | `experiments/mine_free_response_for_features_2026_08_03/part_1_histogram` |
| Mine free responses into feature clusters | LLM features from reflection text, embedded with Titan, clustered with HDBSCAN (compared against KMeans), split by low vs high influence. Of 916 embedded features, 699 were noise. Low-influence users produced 2 labeled clusters (e.g. harm/toxicity thresholds); high-influence users produced 3 (e.g. remove for threats/toxicity). | `experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses` |

## 2. Experiments that used only the Part 2 stimuli

These use `STIMULI` (the post pairs) but no participant responses. Rerun only if the Part 3 stimuli need the same treatment.

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Length matching v1: prompt-only | Regenerate mirrors with an explicit length instruction. The ≥10% character-difference failure rate fell from 86.9% to 76% (n=50). | `experiments/match_lengths_original_mirrors_2026_06_19/` (`run_match_lengths.py`) |
| Length matching v2: token budget | Cap output tokens based on the original's length. Character failure 70%, token failure 46% (n=50). | `experiments/match_lengths_original_mirrors_2026_06_19/` (`run_match_lengths_v2.py`) |
| Length matching ablation sweep | 15 prompt variants on 25 posts. Putting character bounds in the prompt cut failure to 28%. The best variant (D2) reached 20% but over-shortens. | `experiments/match_lengths_original_mirrors_2026_06_19/` (`run_ablations.py`) |
| Truncation v1: last period | Cut each post at its last period within 300 characters. 75.6% of pairs still differ in length by ≥10%. | `experiments/truncate_posts_2026_06_19/` (`truncate_flips.py`) |
| Truncation v2: boundary cascade | Try several cut points in turn and match the mirror to the original's length. Only 4.0% of pairs differ by ≥10%. | `experiments/truncate_posts_2026_06_19/` (`truncate_flips_v2.py`) |
| Truncation v3: sentence-first | Keep the longest complete sentence within the cap. 92.3% of mirrors are complete sentences, but 77.6% of pairs differ by ≥10%: grammar is traded for length parity. | `experiments/truncate_posts_2026_06_19/` (`truncate_flips_v3.py`) |
| Truncation v4/v5: topic-aligned regeneration | A topic-aligned mirror prompt, piloted on 125 rows (v4) and then applied to the full stimuli set (v5). No outcome table. | `experiments/truncate_posts_2026_06_19/truncation_v4`, `.../truncation_v5` |
| Bedrock Nova Micro throughput | Labeling throughput on the Part 2 stimuli, first by batch size, then by process count. Peaked at 98.9 posts/s with 4 processes; a size sweep costs about $0.11 vs about $0.84 on the OpenAI Batch API. | `experiments/bedrock_batch_parallelization_2026_09_06/` |
| OpenAI Batch throughput | Same workload with gpt-5.4-nano across 2–8 processes. Throughput reached about 53.6 posts/s at 8 processes. | `experiments/openai_batch_parallelization_2026_09_05/` |

## 3. Planned but never run (Part 2 intended)

| Headline experiment | Description | Folder |
| --- | --- | --- |
| Keep/remove criteria clustering | Cluster the stage-1 features from `llm_based_feature_generation` into keep and remove criteria lists. Planned only; the folders are empty stubs. | `experiments/create_llm_feature_clusters_2026_08_02/{keep,remove}` |
| Study prompt vs feature-checklist prompt | 500-post comparison of the study prompt vs the prompt plus the clustered criteria. Planned only. | `experiments/prompt_engineering_llm_feature_clusters_2026_08_02/` |
| Participant decision rules | Per-participant profiles comparing stated moderation criteria with actual keep/remove behavior. README only. | `experiments/participant_decision_rules_2026_08_05/` |
| Explanations vs behavior | Compare participants' stated removal reasons with how they actually moderated. README only. | `experiments/participant_explanation_behavior_2026_08_06/` |
| High- vs low-agreement posts | Look at posts with unanimous vs disputed votes by toxicity, topic, and language. README only. | `experiments/rater_agreement_2026_08_06/` |

## Not included

- **Already run on Part 3 data.** `ai_simulation_responses_2026_09_11` (experiments 1–6), `reasoning_during_moderation_2026_09_15` (experiments 1–4), and `study_progress_dashboard_2026_09_11` load Prolific exports from `jspsych-mirror-view-2026-09-09`, not Part 2. `ai_simulation_responses` used a snapshot of about 998 users, so it may be worth rerunning on the final cohort.
- **Part 1 (pilot) only:** `basic_summary_stats_2026_04_27`, `free_response_analysis_2026_04_28`, `mirrors_content_analysis_2026_04_24`, `predict_keep_remove_2026_05_07`, `simplified_predict_remove_2026_05_13`.
- **Part 3 stimulus and assignment preparation.** These touch Part 2 stimuli only to exclude posts that were already used: `combine_data_into_stimulus_set_2026_09_08`, `filter_posts_used_for_stimulus_dataset_2026_09_08`, `upsample_*`, `reddit_curated_perspective_v2_2026_09_08`, `generate_flips*`, `curate_study_2_phase_3_stimuli`, `calculate*_required_label_count_*`, `generate_study_user_assignments_2026_09_08`, `load_study_assignments_2026_09_09`, `qa_latest_dataset_2026_09_09`, `test_separability_original_mirror_posts_2026_09_09`.
- **Part 2 stimulus generation (produced the Part 2 stimuli, not an analysis):** `scaled_mirrors_generation_2026_06_02`.
- **Unrelated to study data:** `fetch_reddit_pushshift_dump_2026_06_15`, `data_ingestion_smoke_2026_08_28`, `create_feature_generation_training_sets_2026_09_04`, `llm_based_toxicity_classifier_2026_09_05`.
