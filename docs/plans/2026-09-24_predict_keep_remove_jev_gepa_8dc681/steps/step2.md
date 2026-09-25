# Step 2: Build labels and frozen splits from Phase 2 Part 3 export

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py` `main`
- **Task:** Load `STUDY_PHASE_2_PART_3_RESULTS_FULL` via `shared.data.dataloader.load_dataset`. Filter scored moderation trials. Dedupe to one rating per `(prolific_id, post_id)`, keeping the first row by `(time_elapsed, trial_index)`. Aggregate per-post counts and majority labels with at least three raters, with ties dropped. Build cohort A (primary) and a unanimous flag. Attach `sampled_stance`, `sample_toxicity_type`, stable texts, and deterministic pair order (`PAIR_ORDER_SEED=0`, same hash pattern as reasoning-during-moderation). Stratify splits test 20% / dev 10% / GEPA pool 70% by label x stance x toxicity with seed `20260924`. Sample balanced GEPA valset 300 (150 keep / 150 remove) and GEPA trainset up to 2,000 balanced from the pool. Write parquet and split hash, upload to S3 `data/` subprefix, and log a Wandb artifact.
- **Out of scope:** Prompt rendering, Jev scoring, GEPA, `jev_baseline/`, editing registry, editing raw CSVs, Stage A runs.

## Dependencies

Step 1 must provide `artifacts.py`, `wandb_tracking.py`, and `secrets.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Cohort rules, split percentages, expected counts, label convention |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/steps/step1.md` | S3 prefix, Wandb helpers |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_3_RESULTS_FULL` path |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform.py` | Slim trial filter and per-post aggregation pattern |
| `/workspace/shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py` | Unanimous min-3 aggregation |
| `/workspace/experiments/study_progress_dashboard_2026_09_11/analyze.py` | `select_real_trials` gate: `trial_type=moderation-trial`, non-empty `post_id`, decision keep or remove |
| `/workspace/experiments/simplified_predict_remove_2026_05_13/splits.py` | `train_test_split` stratify pattern |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` | `PAIR_ORDER_SEED`, hash pair-order constants |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py` | `dedupe_worker_post` sort key pattern |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Label convention: 1 = remove, 0 = keep |
| `/tmp/jev_probe/run_probe.py` | `filter_scored_trials`, `aggregate_labels`, `label_counts` acceptance targets |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/SETUP.md` (add cohort build command and expected counts only)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/cohort.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/conftest.py` (extend)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_filter_scored_trials.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_dedupe_participant_post.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_build_cohort_a.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_build_splits.py` (new)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/README.md`
- `/workspace/webapp/**`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/data/raw/study_phase_2_part_3/**`
- `/workspace/pyproject.toml`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md`

## Contracts

Label convention: `label` 1 = remove (positive), 0 = keep. String `majority_decision` is `keep` or `remove`.

Pinned values in `cohort.py` / `splits.py`:

- `MIN_RATERS = 3`
- `SPLIT_SEED = 20260924`
- `PAIR_ORDER_SEED = 0` (import hash helpers from `experiments.reasoning_during_moderation_2026_09_15.shared.constants` or duplicate the same constants)
- `TEST_FRACTION = 0.20`
- `DEV_FRACTION = 0.10`
- `GEPA_VAL_SIZE = 300`
- `GEPA_VAL_PER_CLASS = 150`
- `GEPA_TRAIN_MAX = 2000`
- `GEPA_TRAIN_PER_CLASS_CAP = 1000`
- `COHORT_PARQUET = experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet`
- `SPLIT_HASH_JSON = experiments/predict_keep_remove_jev_gepa_2026_09_23/data/split_hash.json`
- `S3_DATA_KEY = experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet`

### `cohort.py`

```python
def filter_scored_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep moderation-trial rows with non-empty post_id and decision keep or remove.
    Normalize decision to lowercase stripped strings. Raise KeyError on missing columns."""

def dedupe_participant_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Sort by post_id, prolific_id, time_elapsed, trial_index (mergesort) and keep first per pair."""

def assert_stable_pair_text(trials: pd.DataFrame) -> None:
    """Raise ValueError when a post_id has multiple original_text or mirror_text values."""

def aggregate_post_labels(trials: pd.DataFrame) -> pd.DataFrame:
    """Return one row per post_id with n_raters, n_keep, n_remove, remove_share, majority_decision,
    is_unanimous, original_text, mirror_text, sampled_stance, sample_toxicity_type."""

def build_cohort_a(agg: pd.DataFrame) -> pd.DataFrame:
    """Keep posts with n_raters >= 3 and n_keep != n_remove. Set label from majority_decision."""

def pair_order_for_post(post_id: str, seed: int = PAIR_ORDER_SEED) -> tuple[str, str]:
    """SHA-256 seed hash; return (original, mirror) or (mirror, original). Same algorithm as reasoning experiment."""

def attach_pair_order(cohort: pd.DataFrame) -> pd.DataFrame:
    """Add post_1_role and post_2_role columns."""
```

### `splits.py`

```python
@dataclass(frozen=True)
class CohortCounts:
    n_posts: int
    n_keep: int
    n_remove: int
    n_unanimous: int

@dataclass(frozen=True)
class SplitCounts:
    test: int
    dev: int
    gepa_pool: int
    gepa_val: int
    gepa_train: int

def stratify_key(row) -> str:
    """Return f\"{label}:{sampled_stance}:{sample_toxicity_type}\"."""

def assign_splits(cohort: pd.DataFrame, seed: int = SPLIT_SEED) -> pd.DataFrame:
    """Add split column test|dev|gepa_pool using iterative stratified holdout: test 20%, then dev 10% of remainder."""

def sample_gepa_subsets(pool: pd.DataFrame, seed: int = SPLIT_SEED) -> pd.DataFrame:
    """From gepa_pool rows add gepa_subset column none|val|train.
    val: exactly 150 label 0 and 150 label 1 when available.
    train: up to 1000 per class (2000 total cap). Remaining pool rows stay gepa_subset=none."""

def compute_split_hash(frame: pd.DataFrame) -> str:
    """SHA-256 hex of sorted post_id, split, gepa_subset tuples plus SPLIT_SEED."""

def write_outputs(frame: pd.DataFrame, split_hash: str, experiment_dir: Path) -> tuple[Path, Path]:
    """Write parquet and split_hash.json with counts and built_at timestamp."""

def upload_data(path: Path) -> str:
    """Call artifacts.upload_under_prefix; return s3 uri."""

def log_splits_artifact(run, path: Path) -> None:
    """Log parquet as Wandb artifact name cohort_a_splits type dataset."""

def main() -> CohortCounts:
    """Load, build cohort A, assign splits, write, upload, log artifact, print counts."""
```

### Output parquet columns (exact order)

| Column | Type | Meaning |
|--------|------|---------|
| `post_id` | str | Post id |
| `original_text` | str | Stable original |
| `mirror_text` | str | Stable mirror |
| `label` | int | 0 keep, 1 remove |
| `majority_decision` | str | keep or remove |
| `n_raters` | int | >= 3 |
| `n_keep` | int | |
| `n_remove` | int | |
| `remove_share` | float | n_remove / n_raters |
| `is_unanimous` | bool | all raters agree |
| `sampled_stance` | str | left or right |
| `sample_toxicity_type` | str | low, middle, or high |
| `post_1_role` | str | original or mirror |
| `post_2_role` | str | the other role |
| `split` | str | test, dev, or gepa_pool |
| `gepa_subset` | str | none, val, or train |

`split_hash.json` keys: `split_seed`, `pair_order_seed`, `split_hash`, `cohort_counts`, `split_counts`, `gepa_subset_counts`, `built_at`.

### Acceptance counts (frozen 2026-09-24)

After `main` on the registered CSV:

| Check | Expected |
|-------|----------|
| Cohort A posts | 14,941 |
| Cohort A keep | 11,772 |
| Cohort A remove | 3,169 |
| Unanimous posts | 4,889 |
| Test split | 2,988 |
| Dev split | 1,494 |
| GEPA pool | 10,459 |
| GEPA val | 300 (150/150) |
| GEPA train | 2,000 (1000/1000) |

**Stop rule:** If dedupe or filtering changes cohort A away from 14,941, record the actual counts in `split_hash.json`, print them, and stop. Do not change filters to force the old number.

## Tests to write first

### `tests/conftest.py`

Factory `trial_row(...)` with columns from Part 3 CSV: `trial_type`, `trial_index`, `time_elapsed`, `post_id`, `prolific_id`, `decision`, `original_text`, `mirror_text`, `sampled_stance`, `sample_toxicity_type`, `evaluation_mode`.

Fixture `mixed_trials` with:

- post `P1`: 4 keep (majority keep, unanimous)
- post `P2`: 3 remove, 1 keep (majority remove)
- post `P3`: 2 keep, 2 remove (tie, dropped)
- post `P4`: 2 keep (too few raters)
- post `P5`: duplicate prolific on same post (keep later row with higher trial_index)
- one `moderation-practice` row
- one empty `post_id` row

### `tests/test_filter_scored_trials.py`

Class `TestFilterScoredTrials`.

```text
given mixed_trials
when filter_scored_trials
then practice and empty post_id rows are gone
and only keep or remove decisions remain
```

### `tests/test_dedupe_participant_post.py`

Class `TestDedupeParticipantPost`.

```text
given two rows for prolific W and post P5 with same decision and trial_index 1 then 5
when dedupe_participant_post
then one row remains with trial_index 1
```

### `tests/test_build_cohort_a.py`

Class `TestAggregatePostLabels` and class `TestBuildCohortA`.

```text
given mixed_trials after filter and dedupe
when aggregate_post_labels then build_cohort_a
then P1 and P2 are present with correct n_raters and label
and P3 and P4 are absent
and P1 is_unanimous is True
and P2 is_unanimous is False

given P2 with n_remove=1 n_keep=3
when build_cohort_a
then label is 0 and remove_share is 0.25
```

### `tests/test_build_splits.py`

Class `TestAssignSplits` and class `TestSampleGepaSubsets`.

```text
given a synthetic cohort of 100 rows with balanced labels and full stance/toxicity grid
when assign_splits with seed 20260924
then test fraction is 0.20 plus or minus 1 row per stratum rounding
and dev fraction of remainder is 0.10 plus or minus 1 row

given a gepa_pool of 400 rows with 200 label 0 and 200 label 1
when sample_gepa_subsets
then gepa_subset val has 150 per class
and gepa_subset train has 1000 per class cap
and val and train post_ids are disjoint

given the same cohort frame twice
when compute_split_hash
then both hashes are equal
```

## Implementation order

Follow `/implement-from-spec`. Full auto. One commit per unit of work.

1. `cohort.py` and `splits.py` scaffold with stubs and `main` wiring
2. pytest files (failing)
3. `filter_scored_trials` until `test_filter_scored_trials.py` is green
4. `dedupe_participant_post` and `assert_stable_pair_text` until `test_dedupe_participant_post.py` is green
5. `aggregate_post_labels`, `build_cohort_a`, `pair_order_for_post`, `attach_pair_order` until `test_build_cohort_a.py` is green
6. `assign_splits`, `sample_gepa_subsets`, `compute_split_hash` until `test_build_splits.py` is green
7. `write_outputs`, `upload_data`, `log_splits_artifact`, `main` integration
8. `SETUP.md` cohort command and expected counts

## Commands

Pytest (includes Step 1 tests):

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q
```

Expected: exit 0.

Live cohort build:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts
```

Expected stdout includes:

```text
cohort_a_posts=14941
cohort_a_keep=11772
cohort_a_remove=3169
unanimous_posts=4889
test=2988
dev=1494
gepa_pool=10459
gepa_val=300
gepa_train=2000
split_hash=<64-char hex>
```

Expected local files:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet
experiments/predict_keep_remove_jev_gepa_2026_09_23/data/split_hash.json
```

Expected S3 object:

```text
s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet
```

Wandb artifact `cohort_a_splits` appears on a run with `group=jev_baseline`, `job_type=score`, `name=build_splits`.

## Must pass

- `filter_scored_trials` matches `select_real_trials` gate (moderation-trial, non-empty post_id, keep or remove).
- Dedupe keeps earliest `(time_elapsed, trial_index)` per `(prolific_id, post_id)`.
- Cohort A excludes ties and posts with fewer than three raters.
- `label` 1 means remove.
- Stratified splits use seed `20260924`.
- GEPA val is balanced 150/150; GEPA train is balanced up to 2,000.
- `split_hash` is deterministic.
- Parquet uploads under `data/` subprefix.
- Live counts match the acceptance table, or the stop rule fires with actuals recorded.

## Must fail

- Loading Part 2 registry data.
- Keeping `moderation-practice` rows.
- Keeping tied posts (equal keep and remove counts).
- Assigning labels with 1 = keep.
- Shuffling pair order with a nondeterministic RNG.
- Writing splits without `gepa_subset` on pool rows.
- Upload outside `experiments/predict_keep_remove_jev_gepa_2026_09_23/`.

## Commit messages

1. `add cohort label aggregation for predict_keep_remove_jev_gepa`
2. `add stratified splits and GEPA subset sampling`
3. `add cohort and split unit tests`
4. `wire splits main upload and wandb artifact logging`

## Implement-from-spec notes

Phase 1 names `splits.py` `main` as the caller. Phase 6 completes when pytest exits 0 and the live command prints expected counts or stops with recorded actuals per the stop rule.
