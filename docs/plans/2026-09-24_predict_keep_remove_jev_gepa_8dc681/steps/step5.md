# Step 5: Run Stage A (A1 to A4) on cohort A

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py` `main`
- **Task:** Score all 14,941 cohort A posts for ablations A1, A2, A3, and A4 with `jev_scorer.py` (batch 10, 1,000 requests per minute, resume). Build `shared/metrics.py`. Compute headline metrics on the test split and secondary metrics on the full cohort. Write `labels.parquet`, `requests.parquet`, and `results.json` under `jev_baseline/outputs/<ablation_id>/`. Log Wandb runs (`group=jev_baseline`, `job_type=score`). Upload outputs to S3. Write Stage A tables in `RESULTS.md`.
- **Out of scope:** GEPA (`jev_gepa/`), Stage B, error clustering, criteria mining, changing `cohort.py`, `splits.py`, `prompt.py`, or `jev_scorer.py` behavior beyond imports.

## Dependencies

Steps 1 to 4 must exist:

- `shared/cohort.py`, `shared/splits.py`, `shared/prompt.py`
- `shared/jev_scorer.py`, `shared/rate_limiter.py`, `shared/retries.py`, `shared/latency.py`, `shared/pricing.py`
- `shared/artifacts.py`, `shared/wandb_tracking.py`
- Frozen splits parquet on S3 and locally
- 100-post smoke per view passed in Step 4

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md` | Ablations A1 to A4, key questions, metric list |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Folder layout, label convention, metrics table, Wandb conventions, S3 prefix |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` | Stage A token and cost expectations |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/evaluate.py` | Positive class = remove (`keep_remove_label=1`), `compute_metrics` keys |
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/runner.py` | `_hard_label_metrics`, resume pattern, label encoding |
| `/workspace/experiments/simplified_predict_remove_2026_05_13/features.py` | `classification_metrics_summary` (ROC-AUC, PR-AUC, confusion matrix keys) |
| `/workspace/experiments/predict_keep_remove_2026_05_07/calibration/run_calibration.py` | `balanced_accuracy_score` usage |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/artifacts.py` | `upload_under_prefix` pattern |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/metrics.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/A1_pair_study_prompt/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/A2_original_only/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/A3_mirror_only/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/A4_pair_features_addendum/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_metrics.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/tests/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/tests/test_run_config.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` (append Stage A section only)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/.gitignore` (ignore `jev_baseline/outputs/**` if not already ignored)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/cohort.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/rate_limiter.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/retries.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/latency.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/pricing.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/artifacts.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/wandb_tracking.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/**`
- `/workspace/webapp/**`
- `/workspace/pyproject.toml`
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md`

## Ablation registry (exact)

| `ablation_id` | View | Prompt arm | Wandb run name |
|---------------|------|------------|----------------|
| `A1_pair_study_prompt` | `pair` | study instruction | `A1_pair_study_prompt` |
| `A2_original_only` | `original` | study instruction (single-post edit) | `A2_original_only` |
| `A3_mirror_only` | `mirror` | study instruction (single-post edit) | `A3_mirror_only` |
| `A4_pair_features_addendum` | `pair` | study instruction + `KEEP_REMOVE_FEATURES_ADDENDUM` | `A4_pair_features_addendum` |

Output root per ablation:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/outputs/<ablation_id>/
```

S3 mirror:

```text
s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/<ablation_id>/
```

## Contracts

Positive class is remove (`keep_remove_label=1`). Default threshold is `0.5`. Predicted label: `1` when `p_remove >= threshold`, else `0`.

### `shared/metrics.py`

```python
from dataclasses import dataclass
from typing import Any, Literal

SplitName = Literal["test", "dev", "gepa_pool", "full"]

@dataclass(frozen=True)
class ConfusionCounts:
    tn: int
    fp: int
    fn: int
    tp: int

@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    balanced_accuracy: float
    roc_auc: float
    pr_auc: float
    confusion: ConfusionCounts
    threshold: float
    n: int

@dataclass(frozen=True)
class TrivialBaselineMetrics:
    keep_all_f1: float
    remove_all_f1: float
    prevalence_random_f1_mean: float
    prevalence_random_f1_std: float

@dataclass(frozen=True)
class SubgroupMetrics:
    subgroup_name: str
    subgroup_value: str
    metrics: ClassificationMetrics

@dataclass(frozen=True)
class LatencyPercentiles:
    p50_ms: float
    p90_ms: float
    p99_ms: float

@dataclass(frozen=True)
class CostSummary:
    input_tokens: int
    output_tokens: int
    cost_usd: float

def hard_label_metrics(
    y_true: list[int],
    y_pred: list[int],
    *,
    threshold: float = 0.5,
) -> ClassificationMetrics:
    """F1, accuracy, precision, recall with positive class remove. Uses sklearn with zero_division=0."""

def probability_metrics(
    y_true: list[int],
    p_remove: list[float],
    *,
    threshold: float = 0.5,
) -> ClassificationMetrics:
    """Derive y_pred from p_remove and threshold; compute balanced_accuracy, ROC-AUC, PR-AUC, confusion matrix."""

def tune_threshold_for_f1(
    y_true: list[int],
    p_remove: list[float],
    *,
    grid: list[float] | None = None,
) -> tuple[float, float]:
    """Return (best_threshold, best_f1). Default grid: 0.05, 0.10, ..., 0.95."""

def trivial_baselines(
    y_true: list[int],
    *,
    prevalence_random_seed: int = 20260924,
    prevalence_random_draws: int = 100,
) -> TrivialBaselineMetrics:
    """keep-all, remove-all, prevalence-random (mean and std F1 over draws)."""

def subgroup_metrics(
    frame,  # pandas DataFrame with keep_remove_label, p_remove, sampled_stance, sample_toxicity_type, is_unanimous, remove_share
    *,
    threshold: float = 0.5,
) -> list[SubgroupMetrics]:
    """Emit metrics for stance, toxicity, unanimous vs non-unanimous, and rater agreement quartiles of remove_share."""

def spearman_remove_share(
    remove_share: list[float],
    p_remove: list[float],
) -> float:
    """Spearman correlation between human remove vote share and P(remove). Return nan when undefined."""

def latency_summary(request_latencies_ms: list[float], post_latencies_ms: list[float]) -> dict[str, LatencyPercentiles]:
    """Keys: request, post. Use latency.percentile_ms for p50, p90, p99."""

def build_results_payload(
    *,
    ablation_id: str,
    split_metrics: dict[SplitName, ClassificationMetrics],
    dev_tuned_test_metrics: ClassificationMetrics,
    dev_tuned_threshold: float,
    trivial: TrivialBaselineMetrics,
    subgroups: list[SubgroupMetrics],
    spearman: float,
    latency: dict[str, LatencyPercentiles],
    cost: CostSummary,
    wall_time_s: float,
) -> dict[str, Any]:
    """JSON-serializable dict written to results.json."""
```

`results.json` top-level keys:

| Key | Meaning |
|-----|---------|
| `ablation_id` | One of the four A ids |
| `headline_split` | Always `test` |
| `secondary_split` | Always `full` |
| `metrics_at_0_5` | `test` and `full` `ClassificationMetrics` at threshold 0.5 |
| `dev_tuned_threshold` | float chosen on dev only |
| `dev_tuned_test_metrics` | test metrics at dev-tuned threshold |
| `trivial_baselines` | on test split |
| `subgroups` | test split subgroup table |
| `spearman_remove_share` | on full cohort |
| `latency` | request and post percentiles |
| `cost` | token and dollar totals for the scoring pass |
| `wall_time_s` | end-to-end runner wall time |

`labels.parquet` columns (one row per post):

| Column | Type | Meaning |
|--------|------|---------|
| `post_id` | str | Post id |
| `split` | str | `test`, `dev`, or `gepa_pool` |
| `keep_remove_label` | int | 1 = remove, 0 = keep |
| `p_remove` | float | Jev P(remove) |
| `predicted_label` | int | At default threshold 0.5 |
| `sampled_stance` | str | `left` or `right` |
| `sample_toxicity_type` | str | `low`, `middle`, or `high` |
| `remove_share` | float | `n_remove / n_raters` from cohort parquet |
| `is_unanimous` | bool | True when all raters agree |
| `n_raters` | int | Rater count |

`requests.parquet` columns match Step 4 Contracts (`request_id`, `ablation_id`, `batch_index`, `post_ids`, `n_posts`, `attempt`, `status`, `error_type`, `started_at_utc`, `latency_ms`, `latency_per_post_ms`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `model`, `instruction_sha256`).

### `jev_baseline/run.py`

```python
ABLATION_IDS: tuple[str, ...] = (
    "A1_pair_study_prompt",
    "A2_original_only",
    "A3_mirror_only",
    "A4_pair_features_addendum",
)

def resolve_ablation(ablation_id: str) -> AblationConfig:
    """Map ablation_id to view, prompt arm, output dir, and Wandb run name."""

def build_post_tasks(
    cohort: pd.DataFrame,
    *,
    view: str,
    add_criteria: bool,
) -> list[PostTask]:
    """Shuffle post_ids with numpy RNG seed 20260924. Map cohort column label to PostTask.gold_label.
    Build state_text via prompt.render_state_text(view, original_text, mirror_text, post_1_role, add_criteria)."""

def score_ablation(
    ablation_id: str,
    *,
    cohort_path: Path,
    output_dir: Path,
    resume: bool = True,
) -> Path:
    """Load cohort_a_splits.parquet (default splits.COHORT_PARQUET). Call jev_scorer.run_scoring_pass
    with api_key=secrets.get_jev_api_key(), view from resolve_ablation,
    ablation_id=ablation_id, instruction=None (seed path),
    max_starts_per_minute=jev_scorer.MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT.
    Return output_dir."""

def finalize_ablation(output_dir: Path, cohort: pd.DataFrame) -> dict[str, Any]:
    """Join predictions.jsonl (probability_remove) to cohort rows.
    Materialize requests.parquet from requests.jsonl using the Step 4 schema
    (request_id, ablation_id, batch_index, post_ids, n_posts, attempt, status, error_type,
    started_at_utc, latency_ms, latency_per_post_ms, input_tokens, output_tokens,
    estimated_cost_usd, model, instruction_sha256).
    Write labels.parquet (rename label to keep_remove_label, probability_remove to p_remove)
    and results.json. Latency percentiles read latency_ms and latency_per_post_ms from requests.parquet.
    Cost totals sum input_tokens, output_tokens, and estimated_cost_usd from requests.parquet rows with status ok."""

def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id (required), --cohort-path, --all, --no-resume."""
```

Scoring settings (must match design.md):

| Setting | Value |
|---------|-------|
| Batch size | 10 |
| Rate limiter | `RequestStartLimiter`, 60 s window, 1,000 starts per minute |
| Model | `jev-1.13.0` |
| Resume | skip `post_id` already present in `predictions.jsonl` |
| Shuffle seed | 20260924 (same value as `jev_scorer.SMOKE_SEED`; same batch composition across ablations) |

Wandb: `wandb_tracking.init_run(WandbRunSpec(group='jev_baseline', name=<ablation_id>, job_type='score', config=...))`.
Config keys: `ablation_id`, `view`, `model`, `batch_size`, `rate_cap_per_min`, `split_hash`, `prompt_hash`.
Upload via `artifacts.upload_under_prefix`.

## Tests to write first

Tests live under `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/` and `jev_baseline/tests/`. No live Jev calls in unit tests.

### `shared/tests/test_metrics.py`

Class `TestHardLabelMetrics`, `TestProbabilityMetrics`, `TestTuneThresholdForF1`, `TestTrivialBaselines`, `TestSpearmanRemoveShare`, `TestLatencySummary`.

```text
given y_true [1,0,1,0] and y_pred [1,0,0,0]
when hard_label_metrics
then f1 equals sklearn f1 with pos_label=1 and precision and recall match evaluate.py convention

given y_true [1,0,1,0] and p_remove [0.9,0.1,0.4,0.2] at threshold 0.5
when probability_metrics
then predicted labels are [1,0,0,0]
and confusion tp=1 fp=0 fn=1 tn=2
and roc_auc and pr_auc are finite floats

given y_true with two removes and eight keeps and p_remove perfectly separable
when tune_threshold_for_f1 on dev labels
then returned f1 is 1.0 at some threshold in the grid

given y_true length 100 with 20 removes
when trivial_baselines
then keep_all_f1 is 0.0
and remove_all_f1 equals f1 of all-ones predictions
and prevalence_random_f1_std is non-negative

given remove_share [0.0,0.5,1.0] and p_remove [0.0,0.5,1.0]
when spearman_remove_share
then result is 1.0

given request latencies [100,200,300] and post latencies [50,150,250]
when latency_summary
then request p50_ms is 200.0
```

### `jev_baseline/tests/test_run_config.py`

Class `TestResolveAblation`.

```text
given ablation_id A2_original_only
when resolve_ablation
then view is original
and prompt arm does not include KEEP_REMOVE_FEATURES_ADDENDUM

given ablation_id A4_pair_features_addendum
when resolve_ablation
then view is pair
and prompt arm includes the addendum flag

given unknown ablation_id
when resolve_ablation
then raise ValueError
```

## Implementation order

One Git commit per unit. Full auto. Do not pause after locking contracts.

1. Scaffold `jev_baseline/run.py`, `shared/metrics.py`, ablation subfolders, and test files with `NotImplementedError` bodies.
2. Implement `hard_label_metrics` and `probability_metrics` until `test_metrics.py` classes for those pass.
3. Implement `tune_threshold_for_f1`, `trivial_baselines`, `spearman_remove_share`, and `latency_summary` until remaining `test_metrics.py` classes pass.
4. Implement `subgroup_metrics` and `build_results_payload` until subgroup and payload shape tests pass (add focused tests if needed in the same commit).
5. Implement `resolve_ablation` until `test_run_config.py` passes.
6. Wire `score_ablation` and `finalize_ablation` in `run.py` (imports only from shared modules; no scorer logic duplication).
7. Run live A1, then A2, A3, A4 (may be one commit per ablation after code is green, or one commit for runner plus one per ablation execution artifact).
8. Upload each ablation output dir to S3 and append Stage A section to `RESULTS.md`.

## Commands

Unit tests:

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_metrics.py -q
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/tests -q
```

Expected: exit 0 for both.

Stage A scoring (run each ablation; resume-safe):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

for AB in A1_pair_study_prompt A2_original_only A3_mirror_only A4_pair_features_addendum; do
  PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py \
    --ablation-id "$AB"
done
```

Expected per ablation:

- stdout ends with `ablation_id=<id> posts_scored=14941 deadletter=0`
- `jev_baseline/outputs/<id>/labels.parquet` has 14,941 rows
- `jev_baseline/outputs/<id>/results.json` has `headline_split=test` and `metrics_at_0_5.test.f1` as a float
- Wandb run exists in project `predict_keep_remove_jev_gepa_2026_09_23`, group `jev_baseline`, `job_type=score`

S3 upload (after each ablation or once at end):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import upload_under_prefix
prefix = 'experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/'
root = Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/outputs')
for ablation_dir in sorted(root.iterdir()):
    for path in ablation_dir.rglob('*'):
        if path.is_file():
            upload_under_prefix(path, prefix)
print('uploaded', len(list(root.rglob('results.json'))), 'ablations')
"
```

Expected: prints `uploaded 4 ablations`.

Full shared test suite (regression):

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q
```

Expected: exit 0.

## RESULTS.md Stage A template

Append this block to `experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md`. Fill numeric cells from `results.json` test split at threshold 0.5. Keep four decimal places for rates.

```markdown
## Stage A: Jev baselines (cohort A, n=14,941)

Headline metrics: **test split only**, threshold **0.5**, positive class **remove**.

| Ablation | View | Accuracy | Precision | Recall | F1 | Balanced acc | ROC-AUC | PR-AUC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1_pair_study_prompt | pair | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| A2_original_only | original | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| A3_mirror_only | mirror | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| A4_pair_features_addendum | pair + addendum | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Test split trivial baselines (A1): keep-all F1 **0.0000**, remove-all F1 **0.0000**, prevalence-random F1 **0.0000** (std **0.0000**).

Dev-tuned threshold (fit on dev, applied to test):

| Ablation | Dev threshold | Test F1 |
| --- | --- | --- |
| A1_pair_study_prompt | 0.0000 | 0.0000 |
| A2_original_only | 0.0000 | 0.0000 |
| A3_mirror_only | 0.0000 | 0.0000 |
| A4_pair_features_addendum | 0.0000 | 0.0000 |

Spearman(P(remove), remove_share) on full cohort:

| Ablation | rho |
| --- | --- |
| A1_pair_study_prompt | 0.0000 |
| A2_original_only | 0.0000 |
| A3_mirror_only | 0.0000 |
| A4_pair_features_addendum | 0.0000 |

Latency at batch size 10 (A1, full cohort):

| Level | p50 ms | p90 ms | p99 ms |
| --- | --- | --- | --- |
| per request | 0.0 | 0.0 | 0.0 |
| per post | 0.0 | 0.0 | 0.0 |

Stage A Jev cost (from results.json): **$0.00** total (estimates.md expected ~$0.93).
```

## Must pass

- `shared/metrics.py` positive class is remove (`1`).
- All four ablations score 14,941 posts with resume support.
- Headline metrics in `results.json` and `RESULTS.md` use the test split at threshold 0.5.
- Dev-tuned threshold is fit on dev only and reported on test.
- Trivial baselines, subgroup metrics, Spearman, latency percentiles, and cost are present in `results.json`.
- Wandb runs use group `jev_baseline` and `job_type=score`.
- S3 objects exist under `jev_baseline/<ablation_id>/` for all four ablations.
- Unit tests exit 0 without network calls.

## Must fail

- Scoring fewer than 14,941 posts without an explicit `--limit` smoke flag (not part of this step).
- Using `keep` as the positive class for F1 or recall.
- Tuning threshold on the test split.
- Starting Stage B or editing `jev_gepa/`.
- Uploading to any S3 prefix outside `experiments/predict_keep_remove_jev_gepa_2026_09_23/`.
- Rebuilding cohort or splits in this step.

## Commit messages

1. `feat(jev-gepa): scaffold Stage A runner and metrics module`
2. `feat(jev-gepa): add hard-label and probability metrics`
3. `feat(jev-gepa): add threshold tuning, trivial baselines, and latency helpers`
4. `feat(jev-gepa): add subgroup metrics and results.json builder`
5. `feat(jev-gepa): wire jev_baseline run.py ablation registry`
6. `feat(jev-gepa): run Stage A ablation A1_pair_study_prompt`
7. `feat(jev-gepa): run Stage A ablation A2_original_only`
8. `feat(jev-gepa): run Stage A ablation A3_mirror_only`
9. `feat(jev-gepa): run Stage A ablation A4_pair_features_addendum`
10. `docs(jev-gepa): add Stage A RESULTS.md tables and S3 uploads`

## Implement-from-spec notes

Phase 1 names `jev_baseline/run.py` `main` as the caller. Phase 2 scaffolds `metrics.py`, `run.py`, and test files. Phase 3 locks dataclasses and function signatures above. Phase 4 writes `test_metrics.py` and `test_run_config.py` from the given/when/then blocks. Phase 5 follows the implementation order list. Phase 6 is complete when all four ablations are scored, uploaded, `RESULTS.md` Stage A is filled, and pytest exits 0.
