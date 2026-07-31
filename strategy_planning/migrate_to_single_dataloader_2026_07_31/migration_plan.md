# Migrate experiments onto the shared dataset loader

Follow-up to [PR #35](https://github.com/METResearchGroup/mirrorView-task/pull/35): callers still pin local / `scripts/` CSVs. This plan migrates them onto `shared.data.dataloader.load_dataset` + registry names.

**Registry names (raw only):**

| Name | Path |
|---|---|
| `STUDY_PHASE_2_PART_1_RESULTS_PILOT` | `shared/data/raw/study_phase_2_part_1/results/pilot.csv` |
| `STUDY_PHASE_2_PART_1_RESULTS_FULL` | `shared/data/raw/study_phase_2_part_1/results/full.csv` |
| `STUDY_PHASE_2_PART_1_STIMULI` | `shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv` |
| `STUDY_PHASE_2_PART_2_RESULTS_FULL` | `shared/data/raw/study_phase_2_part_2/results/full.csv` |
| `STUDY_PHASE_2_PART_2_STIMULI` | `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` |

Verified equivalences before planning:

- Part 2 stimuli (`flips.csv`) matches `experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv` (same columns, same 10k `post_primary_key` set).
- `keep_remove_results_2026_06_23.csv` is a slim subset of Part 2 results: linked-fate keep/remove rows with non-null `post_id`, columns renamed (`post_id` → `message_id`), five columns only. Exact row match after that filter: 23,560.

---

## Phase 1 — Obvious drop-ins

Swap a hardcoded CSV path for `load_dataset(<registry name>)`. No reshape. Local filtering that already runs *after* `read_csv` can stay as-is.

| File | Change |
|---|---|
| `experiments/free_response_analysis_2026_04_28/main.py` | Replace `SOURCE_CSV` (`scripts/mirrorview_pilot_data_2026_04_28-16:31:47.csv`) with `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`. Keep `generate_filtered_dataframe` filtering. |
| `experiments/mirrors_content_analysis_2026_04_24/dataloader.py` | In `get_latest_mirrorview_run_data`, replace `pd.read_csv(PINNED_EXPORT_PATH)` with `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`. Drop `PINNED_EXPORT_*` path constants (or leave unused). Keep `transform_latest_mirrorview_run_data` unchanged. |
| `experiments/basic_summary_stats_2026_04_27/summary_stats.py` | Remove `find_latest_export_csv` / `copy_latest_export_csv` / `scripts/` discovery. Load via `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)` (pilot-era stats). |
| `experiments/basic_summary_stats_2026_04_27/toxicity_remove_breakdown.py` | Stop calling `find_latest_export_csv`; load `STUDY_PHASE_2_PART_1_RESULTS_PILOT` the same way as `summary_stats.py`. |
| `experiments/predict_keep_remove_2026_05_07/generate_dataset_metrics.py` | In `_choose_latest_valid_export_csv` fallback path, replace `scripts/mirrorview_pilot_data_*.csv` discovery + `pd.read_csv` with `load_dataset(STUDY_PHASE_2_PART_1_RESULTS_PILOT)`. Preferred path already goes through `Dataloader` (inherits Phase 1 mirrors swap). |
| `experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py` | Replace `INPUT_CSV` pointing at `combined_flips/flips.csv` with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`. |
| `experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths_v2.py` | Stop reading `INPUT_CSV` from disk; use the shared Part 2 stimuli load (import helper from `run_match_lengths.py` or call `load_dataset` directly). |
| `experiments/match_lengths_original_mirrors_2026_06_19/run_ablations.py` | Same as v2: load Part 2 stimuli via shared loader instead of `INPUT_CSV`. |
| `experiments/truncate_posts_2026_06_19/truncate_flips.py` | Replace default `INPUT_CSV` (`combined_flips/flips.csv`) with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`. |
| `experiments/truncate_posts_2026_06_19/truncate_flips_v2.py` | Same default-input swap to `STUDY_PHASE_2_PART_2_STIMULI`. |
| `experiments/truncate_posts_2026_06_19/truncate_flips_v3.py` | Same default-input swap to `STUDY_PHASE_2_PART_2_STIMULI`. |
| `experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py` | Replace `DEFAULT_INPUT_CSV` (`combined_flips/flips.csv`) with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`. |
| `experiments/scaled_mirrors_generation_2026_06_02/validate_mirrors_equal_lengths.py` | Replace `FLIPS_CSV` (`combined_flips/flips.csv`) with `load_dataset(STUDY_PHASE_2_PART_2_STIMULI)`. |

---

## Phase 2 — Needs transformation

Source should become a registry dataset, but the frame callers expect is derived (filters, renames, aggregation, joins). Keep transforms local; only the raw ingress moves to `load_dataset`.

| File | Change |
|---|---|
| `experiments/predict_keep_remove_2026_07_01/data/dataloader.py` | Stop reading `keep_remove_results_2026_06_23.csv`. Load `STUDY_PHASE_2_PART_2_RESULTS_FULL`, then rebuild the slim trial frame: `evaluation_mode == linked_fate`, `decision in {keep,remove}`, drop null `post_id`, set `message_id = post_id`, keep columns `prolific_id, message_id, original_text, mirror_text, decision`. Keep existing modal training aggregation in `load_training_dataframe`. |
| `experiments/predict_keep_remove_2026_05_07/dataloader.py` | After Phase 1 mirrors swap works, optionally load `STUDY_PHASE_2_PART_1_RESULTS_PILOT` directly (skip `MirrorViewPilotDataloader` for ingress), then apply: mirrors trial transform (moderation-trial, phase > 0), linked-fate + keep/remove filter, analysis-label CSV joins. Label joins stay local (not registry data). |
| `experiments/simplified_predict_remove_2026_05_13/dataloader.py` | No new raw path; keep majority aggregation on top of the Phase 2 `05_07` training frame. Confirm it still works after parent ingress changes. |
| `experiments/predict_keep_remove_2026_07_01/models/modernbert/dataloader.py` | No direct CSV path; confirm `load_classifier_dataframe` still matches after `07_01` rebuilds trials from Part 2 full. |
| `experiments/predict_keep_remove_2026_07_01/models/llm_api/dataset.py` | Indirect only: still calls `Dataloader().load_training_dataframe()`; verify after Phase 2 `07_01` change. |
| `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/dataset.py` | Same indirect verify as `llm_api/dataset.py`. |
| `experiments/model_errors_analysis_2026_07_15/collect/build_long_csv.py` | Gold texts come from `07_01` `Dataloader().load_training_dataframe()`; re-run / smoke after Phase 2 `07_01` so `message_id` join still holds. |

---

## Phase 3 — All else (your call)

Not a clean swap and not a single obvious transform. Decide case-by-case (or leave alone).

| File | Why it's here / decision needed |
|---|---|
| `experiments/basic_summary_stats_2026_04_27/total_attrition.py` | Needs export *filename timestamp* for DynamoDB grace-window logic; shared registry files have no export timestamp in the name. |
| `scripts/export_study_results.py` | Producer of ad-hoc `scripts/mirrorview_pilot_data_*.csv` exports, not a consumer of the registry. |
| `experiments/scaled_mirrors_generation_2026_06_02/**` (except `validate_mirrors_equal_lengths.py`) | Producer lineage for Part 2 stimuli; rewriting producers onto the registry is optional / historical. |
| `experiments/llm_based_feature_generation_2026_07_31/**` | Experiment source largely removed; wire-up to Part 2 results when/if rebuilt. |
| `experiments/followup_model_error_analysis_2026_07_15/**` | Reads intermediate analysis CSVs, not study raw tables. |
| `experiments/fetch_reddit_pushshift_dump_2026_06_15/**` | Unrelated corpus pipeline. |
| `experiments/mirrors_content_analysis_2026_04_24/run_analysis.py` | CLI `--data-path` is caller-supplied; only docstring examples mention `scripts/` paths. |
| `STUDY_PHASE_2_PART_1_STIMULI` | No current experiment consumer found. |
| `experiments/basic_summary_stats_2026_04_27/*` PILOT vs FULL | Phase 1 pins pilot for historical continuity; switching summary scripts to `STUDY_PHASE_2_PART_1_RESULTS_FULL` is a product choice. |
| Delete `experiments/predict_keep_remove_2026_07_01/keep_remove_results_2026_06_23.csv` | Only after Phase 2 `07_01` dataloader is proven equivalent. |
| Docs / READMEs / WRITEUPs that still cite `scripts/mirrorview_pilot_data_*.csv` or `combined_flips/flips.csv` | Update when convenient; not required for runtime migration. |

---

## Suggested order

1. Phase 1 Part 1 results consumers (free response, mirrors, summary stats, metrics fallback).
2. Phase 1 Part 2 stimuli consumers (match_lengths, truncate_posts, validate lengths).
3. Phase 2 `07_01` slim-frame rebuild (unblocks modernbert / llm_api / model_errors).
4. Phase 2 `05_07` / simplified direct or inherited ingress.
5. Phase 3 items you pick.
