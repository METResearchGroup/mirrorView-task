# Step 1: Build post-level cohort and discovery and held-out split

Step 1 creates the experiment scaffold at `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/`, builds one post-level cohort row per stimuli catalog post (18,899), computes modal keep/remove and three-group labels, runs a stratified 50/50 discovery versus test split, commits the post-ID lists, and uploads cohort and split artifacts to S3.

## Scope

- **Caller / entrypoint:** `experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort`, `split`, and `s3_sync` CLIs (`if __name__ == "__main__"`).
- **In scope:** Experiment README/SETUP, `paths.py`, `constants.py`, `cohort.py`, `split.py`, `s3_sync.py`, Step 1 tests, cohort parquet under each text arm, committed `data/post_split/*`, S3 upload of split and cohort outputs.
- **Out of scope:** `baselines.py`, LLM modules, `RESULTS.md` content (stub file may exist empty), any edits under `shared/` or other `experiments/*`, `llm_client.py`.

## Files to inspect (read-only)

- `shared/data/dataloader.py`: `load_dataset(name)` for registry CSVs.
- `shared/data/registry.py`: dataset keys (`STUDY_PHASE_2_PART_3_RESULTS_FULL`, `STUDY_PHASE_2_PART_3_STIMULI`, `STUDY_PHASE_2_PART_2_STIMULI`, `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`).
- `shared/data/raw/study_phase_2_part_3/results/full.csv`: moderation trials; columns include `phase`, `trial_type`, `evaluation_mode`, `decision`, `post_id`, `prolific_id`, `attention_check_passed`.
- `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv`: 18,899-post catalog; join key `post_primary_key`; columns `sampled_stance`, `sample_toxicity_type`, `original_text`, `mirrored_text`.
- `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`: Part 2 June catalog (10,000 posts); use `post_primary_key` to detect the 8,899-post overlap with Part 3.
- `shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv`: Part 2 labeled subset (`message_id`); secondary overlap reference only.
- `experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py`: copy the three-group logic into this experiment (do not import across experiments): `drop_conflicting_worker_posts`, `dedupe_worker_post`, `assign_group`, vote counting.
- `experiments/reasoning_during_moderation_2026_09_15/shared/constants.py`: copy constants: `MIN_RATERS=4`, `SPLIT_VOTE_PATTERNS={(2,2),(3,2),(2,3)}`, group string values.
- `experiments/create_llm_features_2026_08_05/src/paths.py`: pattern for `EXPERIMENT_ROOT`, `latest_timestamp_subdir`.
- `lib/aws/s3.py`: `S3` class (`upload_file`, `upload_bytes`, `object_exists`).
- `docs/runbooks/HISTORY_OF_STUDY.md`: Part 3 collection context.
- [HOW_TO_MINE_TEXT_FOR_FEATURES.md](https://github.com/METResearchGroup/lab_wiki/blob/main/docs/manuals/methods/HOW_TO_MINE_TEXT_FOR_FEATURES.md): baseline preprocessing notes (referenced by Step 2; no import).

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/README.md`: 1 to 2 lines plus redirect to SETUP.md and RESULTS.md per `AGENTS.md`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/SETUP.md`: data required (registry CSVs, AWS for S3 upload, expected counts); out of scope: environment setup.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/__init__.py`: empty.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/__init__.py`: empty.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/paths.py`: `EXPERIMENT_ROOT`, arm/stage path helpers, `latest_timestamp_subdir`.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/constants.py`: all standard constants listed below plus cohort-specific literals.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/cohort.py`: cohort builder CLI.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/split.py`: stratified split CLI.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/s3_sync.py`: S3 upload wrapper.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/__init__.py`: empty.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_paths.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_constants.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cohort.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_split.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_s3_sync.py`
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/discovery_post_ids.csv`: written by split CLI; commit to git.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/test_post_ids.csv`: written by split CLI; commit to git.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/split_metadata.json`: written by split CLI; commit to git.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/<arm>/cohort/<run_timestamp>/`: gitignored run outputs.

## Files forbidden to change

- `shared/` (read only)
- Other `experiments/*` (no cross-experiment imports)
- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md` and sibling step files (`step2.md` through `step7.md`)
- `lib/` (read only)
- Any module assigned to Steps 2 through 7 in the contract

## Implementation phases (TDD: mandatory order)

Complete phases in order. Make one git commit per phase (or per unit of work in Phase 5), and do not skip phases.

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Name callers, file tree, out-of-scope | Three CLIs plus tree listed |
| 2: Scaffold | Create modules and imports; stub bodies only | Imports resolve; `raise NotImplementedError` |
| 3: Contracts | Types, signatures, schemas; no business logic | Matches cohort and split artifact contracts below; stubs only |
| 4: Test design | Pseudocode to failing tests (happy plus key failures) | Tests fail for the right reason |
| 5: Implement | One function or path per commit until green | Targeted tests pass |
| 6: Done | Full Step 1 pytest plus CLI smoke | All pass/fail criteria met |

### Phase 4: Named test cases (write before implementation)

**`test_paths.py`**

| Test | Asserts |
|------|---------|
| `test_experiment_root_is_package_parent` | `paths.EXPERIMENT_ROOT.name == "llm_feature_generation_phase_2_part_3_2026_09_24"`. |
| `test_cohort_dir_for_each_arm` | `paths.cohort_dir("original_only")` ends with `outputs/original_only/cohort`. |
| `test_latest_timestamp_subdir_picks_max_name` | Given temp dirs `2026-09-24T10-00-00` and `2026-09-24T11-00-00`, returns the latter. |
| `test_latest_timestamp_subdir_empty_raises` | Empty parent raises `FileNotFoundError`. |

**`test_constants.py`**

| Test | Asserts |
|------|---------|
| `test_split_seed_is_42` | `constants.SPLIT_SEED == 42`. |
| `test_text_arms_match_contract` | `constants.TEXT_ARMS == ("original_only", "mirror_only", "paired")`. |
| `test_s3_prefix_matches_experiment_folder` | `constants.S3_PREFIX == "experiments/llm_feature_generation_phase_2_part_3_2026_09_24/"`. |
| `test_min_raters_is_4` | `constants.MIN_RATERS == 4`. |

**`test_cohort.py`**

| Test | Asserts |
|------|---------|
| `test_slim_trials_filters_phase_one_moderation` | Fixture with phase 1 and phase 2 rows keeps only phase==1 linked-fate moderation trials with keep/remove decisions. |
| `test_drop_conflicting_worker_posts` | Worker with both keep and remove on same post is removed entirely. |
| `test_dedupe_worker_post_keeps_earliest` | Two rows same worker/post keeps lower `time_elapsed`. |
| `test_assign_group_split_patterns` | `(2,2)`, `(3,2)`, `(2,3)` map to `"split"`. |
| `test_assign_group_unanimous_requires_min_raters` | `(4,0)` to `"unanimous_keep"`; `(3,0)` to `None`. |
| `test_modal_decision_is_majority_vote` | 3 keep, 1 remove yields `"keep"`. |
| `test_modal_decision_tie_raises` | 2 keep, 2 remove raises `ValueError`. |
| `test_three_group_null_when_fewer_than_four_raters` | 3 raters yields `three_group_label is None`. |
| `test_in_part2_catalog_uses_part2_stimuli` | Post in Part 2 stimuli set has `in_part2_catalog=True`; post only in Part 3 has `False`. |
| `test_attention_pass_filter_excludes_failed_participants` | Trials from prolific_ids with `attention_check_passed==0` dropped when `--participant-filter attention_pass`. |
| `test_build_cohort_row_count` | On real data (mark `@pytest.mark.integration` or use cached fixture), cohort has exactly 18,899 rows. |
| `test_label_count_distribution` | On real data, posts-by-label-count: 1,145 with 1 label; 1,755 with 2; 15,966 with 3 or more; 18,866 posts with at least one phase-1 moderation label. |
| `test_in_part2_catalog_count` | On real data, exactly 8,899 rows have `in_part2_catalog==True` when overlap is computed against `STUDY_PHASE_2_PART_2_STIMULI.post_primary_key`. |

**`test_split.py`**

| Test | Asserts |
|------|---------|
| `test_stratified_split_sizes` | 18,899 posts split into 9,449 discovery and 9,450 test. |
| `test_split_is_disjoint_and_complete` | Union of discovery and test IDs equals full cohort ID set; intersection empty. |
| `test_split_reproducible_with_seed_42` | Two runs with seed 42 produce identical ID lists. |
| `test_stratify_preserves_modal_decision_margin` | For each modal_decision stratum, discovery/test ratio within 5 percentage points of 50/50 (guard against broken stratification). |
| `test_split_metadata_schema` | Written JSON contains required keys and `split_seed==42`. |
| `test_unlabeled_posts_assigned_to_split` | Posts with null `modal_decision` still receive `discovery` or `test`. |

**`test_s3_sync.py`**

| Test | Asserts |
|------|---------|
| `test_s3_key_for_local_prepends_prefix` | Local path under experiment root maps to `S3_PREFIX + relative_posix_path`. |
| `test_upload_paths_calls_s3_upload_file` | Mock `S3.upload_file`; CLI uploads each file under given directories. |
| `test_upload_skips_missing_paths` | Missing path prints warning and continues (or raises clearly; pick one behavior and test it). |

## Pass / fail criteria

### Must pass

- Experiment folder exists with README, SETUP, `src/`, `tests/`, `data/post_split/`.
- `cohort.py --participant-filter all --write` writes identical 18,899-row parquet copies under `outputs/original_only/cohort/<ts>/`, `outputs/mirror_only/cohort/<ts>/`, and `outputs/paired/cohort/<ts>/`.
- `cohort.py --participant-filter attention_pass --write` writes sensitivity cohorts with fewer moderation trials, because participants who failed the attention check are removed.
- `split.py --seed 42 --write` writes committed CSVs and metadata, and fills the `split` column in cohort parquet (`discovery` or `test`).
- `s3_sync.py --paths data/post_split outputs/original_only/cohort outputs/mirror_only/cohort outputs/paired/cohort` uploads to `s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/`.
- Label-count and overlap sanity checks match plan numbers (see Artifact contract).
- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_paths.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_constants.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cohort.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_split.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_s3_sync.py -q` exits 0.

### Must fail (until implemented)

- Running any Step 1 CLI before Phase 5 completes raises `NotImplementedError` or argparse error on missing `--write`.
- `test_modal_decision_tie_raises` fails if ties silently pick a label.
- Stratified split test fails when IDs are assigned randomly without stratification.

## Commands (exact)

```bash
cd /workspace

# Build cohort (all participants, primary)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort \
  --participant-filter all \
  --write

# Attention-check ablation cohort (sensitivity)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort \
  --participant-filter attention_pass \
  --write

# Stratified 50/50 split (uses SPLIT_SEED=42)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.split \
  --seed 42 \
  --write

# Upload committed split + cohort artifacts
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \
  --paths data/post_split outputs/original_only/cohort outputs/mirror_only/cohort outputs/paired/cohort

# Tests
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_paths.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_constants.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_cohort.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_split.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_s3_sync.py -q
```

### Expected output (representative lines)

```
participant_filter=all n_posts=18899 n_labeled=18866 n_part2_overlap=8899
label_counts: n1=1145 n2=1755 n3plus=15966
wrote outputs/original_only/cohort/2026-09-24T12-34-56/cohort.parquet
n_posts=18899 n_discovery=9449 n_test=9450
wrote data/post_split/discovery_post_ids.csv
wrote data/post_split/test_post_ids.csv
wrote data/post_split/split_metadata.json
s3_uploaded_prefix=s3://mirrorview-experimental-artifacts/experiments/llm_feature_generation_phase_2_part_3_2026_09_24/
```

## Artifact contract (this step's outputs)

### Run timestamp format

Use local `datetime.now().strftime("%Y-%m-%dT%H-%M-%S")` for cohort output folders (orchestrator override; do not use `lib.timestamp_utils.get_current_timestamp` here).

### Cohort table (`outputs/<arm>/cohort/<ts>/cohort.parquet`)

One row per post (18,899). Same rows in all three arm folders (copy for traceability).

| Column | Type | Notes |
|--------|------|-------|
| `post_id` | str | Primary key; equals `post_primary_key` in stimuli |
| `original_text` | str | From stimuli |
| `mirror_text` | str | From stimuli `mirrored_text` |
| `modal_decision` | str or null | `"keep"` or `"remove"` (majority over phase==1 moderation trials); null when zero labels |
| `keep_count` | int | Keep votes after dedupe and conflict drop |
| `remove_count` | int | Remove votes after dedupe and conflict drop |
| `n_raters` | int | `keep_count + remove_count` |
| `three_group_label` | str or null | `"unanimous_keep"`, `"split"`, `"unanimous_remove"`, or null |
| `sampled_stance` | str | `"left"` or `"right"` from stimuli |
| `sample_toxicity_type` | str | `"low"`, `"middle"`, or `"high"` mapped from `sample_low_toxicity`, `sample_middle_toxicity`, `sample_high_toxicity` |
| `in_part2_catalog` | bool | `post_id` in Part 2 June catalog (`STUDY_PHASE_2_PART_2_STIMULI.post_primary_key`); expect 8,899 True |
| `split` | str or null | `"discovery"` or `"test"` after split step; null before split |
| `participant_filter` | str | `"all"` or `"attention_pass"` |

**Cohort build logic (copy from reasoning reference; do not import across experiments):**

1. Start from all 18,899 rows in `STUDY_PHASE_2_PART_3_STIMULI`.
2. Slim moderation trials from `STUDY_PHASE_2_PART_3_RESULTS_FULL`:
   - `trial_type == "moderation-trial"`
   - `evaluation_mode == "linked_fate"` (lowercase strip)
   - `decision` in `{keep, remove}` (lowercase strip)
   - `phase == 1`
   - non-empty `prolific_id` and `post_id` (reject literal `"nan"`)
3. Participant filter:
   - `all`: keep all slim trials.
   - `attention_pass`: keep trials only from prolific_ids whose first non-null `attention_check_passed` equals `1`.
4. `drop_conflicting_worker_posts`: drop worker-post pairs with both keep and remove.
5. `dedupe_worker_post`: keep earliest row per `(post_id, prolific_id)` sorted by `time_elapsed`, then `trial_index`.
6. Aggregate per `post_id`: `keep_count`, `remove_count`, `n_raters`.
7. `modal_decision`: majority label; raise if `keep_count == remove_count` and `n_raters > 0`.
8. `three_group_label`: apply `assign_group(keep_count, remove_count)` only when `n_raters >= MIN_RATERS` (4); patterns per reasoning reference.
9. Join stance and toxicity from stimuli; map toxicity prefix `sample_` and suffix `_toxicity` to short bucket names.
10. `in_part2_catalog`: membership in set of `STUDY_PHASE_2_PART_2_STIMULI.post_primary_key`.

Also write `outputs/<arm>/cohort/<ts>/metadata.json`:

```json
{
  "participant_filter": "all",
  "built_at": "<ISO8601>",
  "n_posts": 18899,
  "n_labeled": 18866,
  "label_count_histogram": {"1": 1145, "2": 1755, "3_plus": 15966},
  "n_part2_overlap": 8899,
  "run_timestamp": "2026-09-24T12-34-56"
}
```

### Split files (`data/post_split/`)

**`discovery_post_ids.csv` / `test_post_ids.csv`**

| Column | Type |
|--------|------|
| `post_id` | str |

**`split_metadata.json`**

```json
{
  "split_seed": 42,
  "n_discovery": 9449,
  "n_test": 9450,
  "stratify_columns": ["modal_decision", "sampled_stance", "sample_toxicity_type", "in_part2_catalog"],
  "participant_filter": "all",
  "built_at": "<ISO8601>"
}
```

**Split logic:**

- Input: latest cohort parquet built with `--participant-filter all`.
- Split all 18,899 posts (including 33 with null `modal_decision`).
- Use `sklearn.model_selection.train_test_split` with `test_size=0.5`, `random_state=SPLIT_SEED` (42), `stratify` on concatenated stratify key built from the four columns; represent null `modal_decision` as the string `"unlabeled"` for stratification only.
- Write ID lists and set the `split` column on cohort parquet in place, or rewrite parquet under a new cohort timestamp. Pick one approach and document it in SETUP.md.

### `src/constants.py` (define in Step 1; import everywhere)

| Constant | Value |
|----------|-------|
| `LLM_MODEL_ID` | `gpt-6-luna` |
| `LLM_LITELLM_MODEL_ID` | `openai/gpt-6-luna` |
| `LLM_REASONING_EFFORT` | `none` |
| `SPLIT_SEED` | `42` |
| `CLUSTER_SEEDS` | `(42, 43, 44)` |
| `DEFAULT_SEED` | `42` |
| `TEXT_ARMS` | `("original_only", "mirror_only", "paired")` |
| `BATCH_DESIGN_MIXED` | `mixed` |
| `BATCH_DESIGN_SINGLE_CLASS` | `single_class` |
| `MAX_KEEP_FEATURES_PER_BATCH` | `8` |
| `MAX_REMOVE_FEATURES_PER_BATCH` | `8` |
| `EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` |
| `EMBEDDING_DIM` | `256` |
| `EMBEDDING_NORMALIZE` | `True` |
| `SPEND_CAP_USD` | `25.00` |
| `LLM_INPUT_PRICE_PER_1M` | `0.10` |
| `LLM_CACHED_INPUT_PRICE_PER_1M` | `0.01` |
| `LLM_OUTPUT_PRICE_PER_1M` | `0.50` |
| `SELF_CONSISTENCY_SAMPLE` | `200` |
| `SELF_CONSISTENCY_THRESHOLD` | `0.90` |
| `S3_BUCKET` | `mirrorview-experimental-artifacts` |
| `S3_PREFIX` | `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/` |
| `RUN_TIMESTAMP_FORMAT` | `%Y-%m-%dT%H-%M-%S` |
| `COST_LOG_PATH` | `outputs/shared/cost_log.jsonl` |
| `PART2_STAGE2_OUTPUT_DIR` | `experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981/` |
| `MIN_RATERS` | `4` |
| `SPLIT_VOTE_PATTERNS` | `frozenset({(2, 2), (3, 2), (2, 3)})` |
| `GROUP_SPLIT` | `"split"` |
| `GROUP_UNANIMOUS_KEEP` | `"unanimous_keep"` |
| `GROUP_UNANIMOUS_REMOVE` | `"unanimous_remove"` |

### `src/paths.py` helpers

| Function | Returns |
|----------|---------|
| `EXPERIMENT_ROOT` | Path to experiment folder |
| `cohort_dir(arm: str)` | `outputs/<arm>/cohort` |
| `baselines_dir(arm: str)` | `outputs/<arm>/baselines` (Step 2) |
| `discovery_run_dir(arm: str)` | `outputs/<arm>/discovery/outputs` |
| `normalize_run_dir(arm: str)` | `outputs/<arm>/normalize` |
| `operationalize_dir(arm: str)` | `outputs/<arm>/operationalize` (Step 5 exports) |
| `shared_label_dir()` | `outputs/shared/label` |
| `codebook_dir()` | `outputs/shared/codebook` |
| `self_consistency_dir()` | `outputs/shared/self_consistency` |
| `cost_log_path()` | `outputs/shared/cost_log.jsonl` |
| `post_split_dir()` | `data/post_split` |
| `make_run_timestamp()` | `RUN_TIMESTAMP_FORMAT` string |
| `latest_timestamp_subdir(parent: Path)` | Newest child directory by name sort |

### `src/s3_sync.py`

| Function | Behavior |
|----------|----------|
| `s3_key_for_local(local_path: Path) -> str` | `S3_PREFIX + relative path from EXPERIMENT_ROOT` |
| CLI `--paths` | Each argument is a file or directory under experiment root; upload files recursively |

## Human gates (if any)

None for Step 1.

## Commit message template

`step1: {short description}`

Suggested commits (Phase 5 granularity):

- `step1: scaffold experiment package and paths`
- `step1: add constants and cohort contracts`
- `step1: implement cohort builder with tests`
- `step1: implement stratified split and commit post IDs`
- `step1: add s3_sync and upload cohort artifacts`

## Handoff to Step 2

Step 2 (`baselines.py`) depends on the following:

- `data/post_split/discovery_post_ids.csv` committed with 9,449 IDs.
- Cohort parquet with `split=="discovery"`, `modal_decision`, text columns, and the metadata fields above.
- `paths.baselines_dir(arm)` and `constants.TEXT_ARMS` ready.
- Do not edit `s3_sync.py` after Step 1. Step 2 only calls it.
