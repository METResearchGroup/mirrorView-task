# Step 1: Build the five-label cohort and the mining batches

Step 1 builds the scaffold of the experiment, the pairs that step 2 mines, and the 320 batches that step 2 sends to GPT-5.6 Terra. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step1_setup/run.py`. Step 1 calls no language model.

Out of scope are prompts, OpenAI calls, embeddings, and any edit under `shared/` at the repository root.

## Decisions

A pair is one `post_id`. The cohort is the set of pairs with exactly five labelers after each person counts once per pair. Reuse `build_five_labeler_counts` from `experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`, because it already runs on the same Study 2 table. It keeps only moderation trials with a keep or remove decision, and it counts each person once per pair. On the 2026-09-29 data it returns 15,113 pairs.

The modal label is `remove` when `n_remove` is 3 or more, and it is `keep` otherwise. Five labels cannot tie. On the 2026-09-29 data there are 11,910 keep pairs and 3,203 remove pairs.

The pair text, stance, and toxicity come from `STUDY_2_STIMULI`. Join `post_id` in the cohort to `post_primary_key` in the stimuli, after converting `post_primary_key` to a string. Rename `mirrored_text` to `mirror_text`. `sampled_stance` is the lean of the original post, and it is `left` or `right`. `sample_toxicity_type` is `sample_low_toxicity`, `sample_middle_toxicity`, or `sample_high_toxicity`.

For the batches, sort the keep ids and the remove ids by `post_id`. Then shuffle each list with one `numpy.random.default_rng(1)`, shuffling the keep list first. The batch count is the smaller of the keep count divided by 10 and the remove count divided by 10, rounded down, which is 320. Batch `i` takes keep ids `10*i` to `10*i+9` and remove ids `10*i` to `10*i+9`. No id appears in two batches. The 3 remove pairs and 8,710 keep pairs that are left over do not appear in any batch.

Local outputs go under `experiments/study_2_llm_based_feature_extraction_2026_09_29/outputs/`. The experiment's `.gitignore` holds the single line `outputs/`, so no data file is committed. Every output file is uploaded to the same relative key under the S3 prefix.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py` | `build_five_labeler_counts`, which you reuse |
| `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/jev_labels.py` | `use_lab_credentials`, which you reuse |
| `/workspace/shared/data/dataloader.py` | `load_dataset`, which downloads a registered CSV from S3. Do not call it in tests. |
| `/workspace/shared/data/registry.py` | `STUDY_2_RESULTS_FULL` and `STUDY_2_STIMULI` |
| `/workspace/shared/data/raw/study_2/README.md` | Table sizes |
| `/workspace/lib/aws/s3.py` | `S3.upload_file` and `S3.get_bytes` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/CODING_RULES.md` | Short functions, named constants, numpy-style docstrings |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function, arrange, act, and assert |

## Files allowed to change

All paths are under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Create `README.md`, `SETUP.md`, `RESULTS.md`, and `.gitignore`
- Create `__init__.py`, `shared/__init__.py`, `src/__init__.py`, `src/step1_setup/__init__.py`, and `tests/__init__.py`
- Create `shared/constants.py` and `shared/storage.py`
- Create `src/step1_setup/build_cohort.py`, `src/step1_setup/build_batches.py`, and `src/step1_setup/run.py`
- Create `tests/test_build_cohort.py`, `tests/test_build_batches.py`, and `tests/test_storage.py`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/data_platform/**`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/**`
- `/workspace/pyproject.toml` and `/workspace/uv.lock`

## Contracts

`README.md` is two lines. The first line is the title `# Study 2 LLM-based feature extraction`. The second line says to read `SETUP.md` for the data and `RESULTS.md` for the results.

`SETUP.md` lists the data the experiment needs, which is `STUDY_2_RESULTS_FULL` at `s3://mirrorview-experimental-artifacts/shared/data/raw/study_2/results/full.csv` and `STUDY_2_STIMULI` at `s3://mirrorview-experimental-artifacts/shared/data/raw/study_2/stimuli/flips.csv`, both downloaded with `shared.data.dataloader.load_dataset`. It gives the S3 prefix for outputs and one command per step, and each later step adds its own command. It does not cover environment setup.

`RESULTS.md` starts with one heading per step, from `## Step 1: cohort and batches` to `## Step 7: analyses`. Step 1 fills in only its own section.

`shared/constants.py` holds these values:

```text
EXPERIMENT_NAME = "study_2_llm_based_feature_extraction_2026_09_29"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_NAME   # REPO_ROOT from lib.constants
LOCAL_OUTPUT_DIR = EXPERIMENT_DIR / "outputs"
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = f"experiments/{EXPERIMENT_NAME}/"
SEED = 1
REQUIRED_LABELERS = 5
MODAL_REMOVE_MIN_VOTES = 3
MODAL_LABEL_KEEP = "keep"
MODAL_LABEL_REMOVE = "remove"
KEEP_PAIRS_PER_BATCH = 10
REMOVE_PAIRS_PER_BATCH = 10
BATCH_ID_PREFIX = "batch_"
BATCH_ID_WIDTH = 3
COHORT_COLUMNS = ("post_id", "original_text", "mirror_text", "sampled_stance",
                  "sample_toxicity_type", "n_remove", "modal_label")
EXPECTED_FIVE_LABEL_PAIRS = 15113
EXPECTED_MODAL_KEEP = 11910
EXPECTED_MODAL_REMOVE = 3203
EXPECTED_BATCHES = 320
EXPECTED_STIMULUS_PAIRS = 20000
SMOKE_QUERY_COUNT = 5
ESTIMATE_BAND = 0.20
COHORT_KEY = "step1_setup/cohort.parquet"
BATCHES_KEY = "step1_setup/batches.jsonl"
```

`shared/storage.py` has these functions, in this order:

```text
local_path(relative_key: str) -> Path
  Return LOCAL_OUTPUT_DIR / relative_key.

upload_artifact(relative_key: str) -> str
  Call use_lab_credentials, upload local_path(relative_key) to S3_PREFIX + relative_key
  in S3_BUCKET, and return the s3:// URI. Raise FileNotFoundError when the local file is missing.

download_artifact(relative_key: str) -> Path
  Return local_path(relative_key) when it exists. Otherwise call use_lab_credentials,
  download S3_PREFIX + relative_key, write it to local_path(relative_key), and return that path.
```

`src/step1_setup/build_cohort.py` has these functions, in this order:

```text
assign_modal_label(counts: pd.DataFrame) -> pd.DataFrame
  Add modal_label: MODAL_LABEL_REMOVE when n_remove >= MODAL_REMOVE_MIN_VOTES, else MODAL_LABEL_KEEP.
  Raise ValueError when any n_raters is not REQUIRED_LABELERS.

attach_pair_text(labeled: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame
  Inner-join on post_id == post_primary_key.astype(str), rename mirrored_text to mirror_text,
  and return COHORT_COLUMNS sorted by post_id.
  Raise ValueError when a labeled post_id has no stimulus row.

build_cohort(results: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame
  build_five_labeler_counts, then assign_modal_label, then attach_pair_text.
```

`src/step1_setup/build_batches.py` has these functions, in this order:

```text
shuffled_post_ids(cohort: pd.DataFrame, modal_label: str, rng: np.random.Generator) -> list[str]
  Sort the post_ids with that modal_label, then return rng.permutation of that list.

format_batch_id(index: int) -> str
  Return f"{BATCH_ID_PREFIX}{index:0{BATCH_ID_WIDTH}d}", for example "batch_007".

build_batches(cohort: pd.DataFrame, seed: int) -> list[dict]
  Make one rng from seed. Shuffle the keep ids, then the remove ids.
  Return one dict per batch with keys batch_id, keep_post_ids, and remove_post_ids.
```

`src/step1_setup/run.py` has `main()`. It downloads both datasets with `load_dataset("STUDY_2_RESULTS_FULL", low_memory=False)` and `load_dataset("STUDY_2_STIMULI")`, builds the cohort and the batches with `SEED`, and raises `ValueError` when a count differs from `EXPECTED_FIVE_LABEL_PAIRS`, `EXPECTED_MODAL_KEEP`, `EXPECTED_MODAL_REMOVE`, or `EXPECTED_BATCHES`. It writes `COHORT_KEY` as parquet and `BATCHES_KEY` as one JSON object per line, uploads both files, and prints one `uploaded=` line per file and then one count line.

Do not give these functions default arguments.

## Tests

`tests/test_build_cohort.py`:

- `TestAssignModalLabel.test_three_removes_is_remove`: rows with `n_remove` 2 and 3 get `keep` and `remove`.
- `TestAssignModalLabel.test_rejects_wrong_rater_count`: a row with `n_raters` 4 raises `ValueError`.
- `TestAttachPairText.test_renames_mirror_and_keeps_columns`: the result columns equal `COHORT_COLUMNS`.
- `TestAttachPairText.test_missing_stimulus_raises`: a labeled post with no stimulus row raises `ValueError`.
- `TestBuildCohort.test_keeps_only_five_label_pairs`: a raw frame where post `a` has five people and post `b` has two people returns only `a`.

`tests/test_build_batches.py`:

- `TestBuildBatches.test_batch_count_is_limited_by_smaller_label`: 35 keep pairs and 21 remove pairs give 2 batches.
- `TestBuildBatches.test_each_batch_has_ten_and_ten`: every batch has 10 keep ids and 10 remove ids.
- `TestBuildBatches.test_no_id_repeats`: no id appears in two batches.
- `TestBuildBatches.test_same_seed_same_batches`: two calls with seed 1 return equal lists, and seed 2 returns a different list.
- `TestFormatBatchId.test_zero_pads`: index 7 gives `batch_007`.

`tests/test_storage.py`:

- `TestLocalPath.test_joins_under_outputs`: `local_path("step1_setup/cohort.parquet")` ends with `outputs/step1_setup/cohort.parquet`.
- `TestUploadArtifact.test_missing_file_raises`: a key with no local file raises `FileNotFoundError`, and the test does not reach S3.

No test reads S3 or calls a model.

## Commands

```bash
PYTHONPATH=. uv run pytest experiments/study_2_llm_based_feature_extraction_2026_09_29/tests -q
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step1_setup/run.py
```

The second command prints these lines:

```text
uploaded=s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/step1_setup/cohort.parquet
uploaded=s3://mirrorview-experimental-artifacts/experiments/study_2_llm_based_feature_extraction_2026_09_29/step1_setup/batches.jsonl
cohort_pairs=15113 modal_keep=11910 modal_remove=3203 batches=320
```

After the run, write the four counts and the 3 remove and 8,710 keep pairs left out of the batches under `## Step 1: cohort and batches` in `RESULTS.md`.

## Pass

The pytest command exits 0, and the run prints the three lines in the Commands section.

## Fail

The step fails when a test fails, when a test reads S3, when any count differs from the pinned count, or when `git status` shows a file under `outputs/`.
