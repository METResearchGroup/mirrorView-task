# Step 6: Production runs and test evaluation

## Scope

- **Caller:** `jev_gepa_rebuilt/optimize.py` production config, `jev_gepa_rebuilt/evaluate.py` `main`
- **Task:** Launch ablations per the plan table with shared Jev rate limit **200 request starts/min per job** (max **1,000**/min across parallel jobs). After Step 5 smokes pass, run **R1**, **R2**, **R3**, and **R7** in parallel. Run **R4** only after the R4 round-robin smoke passes. Run **R5** and **R6** at `HALF_BUDGET_MAX_METRIC_CALLS` (15,000 posts) only if R1's confirmed dev-B F1 is strictly greater than **0.538**. After each optimize run finishes, run **one** test evaluation via `evaluate.py`. On Jev API failure after retries, stop the job and report. Do not retry in a loop. Upload outputs and log Wandb group `jev_gepa_rebuilt`.
- **Out of scope:** RESULTS.md prose (Step 7), error clustering (Step 7 optional), editing plan.md/design.md.

## Dependencies

Steps 1 to 5: policies, selection, guards, reflection logging, smokes green, dev_ab_split on S3.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py` | Metrics payload, subgroup, latency, Wandb |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | `ABLATION_REGISTRY`, rate limiter |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/metrics.py` | `build_results_payload`, ROC/PR AUC |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` | Stage A union A1 test F1 **0.538** baseline |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` (`ABLATION_REGISTRY`, production `run_optimize`, Jev failure handling)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py` (full implementation)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/run_ablations.py` (new, optional launcher shell-out)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_ablation_registry.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_evaluate_rebuilt.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_jev_failure_stops.py` (new)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/evaluate.py`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md`

## Contracts

### `ABLATION_REGISTRY` (production)

| `ablation_id` | view | score_mode | reflection_lm | max_metric_calls | max_reflection_cost_usd |
|---------------|------|------------|---------------|------------------|-------------------------|
| `R1_gepa_pair` | pair | `label_certainty` | `openai/gpt-6-luna` | `DEFAULT_MAX_METRIC_CALLS` (30000) | 5.0 |
| `R2_majority_weighted` | pair | `majority_weighted` | `openai/gpt-6-luna` | 30000 | 5.0 |
| `R3_gepa_pair_terra` | pair | `label_certainty` | `openai/gpt-5.6-terra` | 30000 | 40.0 |
| `R4_gepa_multi_component` | pair | `label_certainty` | `openai/gpt-6-luna` | 30000 | 5.0 |
| `R5_gepa_original` | original | `label_certainty` | `openai/gpt-6-luna` | `HALF_BUDGET_MAX_METRIC_CALLS` | 2.50 |
| `R6_gepa_mirror` | mirror | `label_certainty` | `openai/gpt-6-luna` | 15000 | 2.50 |
| `R7_plain_majority` | pair | `plain_majority` | `openai/gpt-6-luna` | 30000 | 5.0 |

R7 is approved. Enable it in the registry with no extra flag.

R4: multi-key `seed_candidate` per Step 5; `module_selector="round_robin"`. All other ablations: single `study_instruction` key; **omit** `module_selector` (GEPA default).

### Rate limiting

Each optimize process:

```python
RequestStartLimiter(200)  # DEFAULT_RATE_CAP_PER_MIN per job
```

Parallel jobs: run at most **5** full-budget jobs at once so combined traffic stays at or under **1,000** req/min (5 x 200). Wave 1: R1, R2, R3, R7. Wave 2: R4. Wave 3: R5 and R6 if the dev-B gate passes.

### R5/R6 gate

After R1 finishes dev selection, read `outputs/R1_gepa_pair/dev_selection.json`. Run R5 and R6 only if R1's confirmed dev-B F1 is strictly greater than Stage A union A1 test F1 **0.538**. If not, skip R5/R6 and write `outputs/_smoke/r5_r6_skipped.json` with the measured dev-B F1 and the 0.538 bar. The earlier $12 Jev-cost gate is retired.

### Jev API failure

In adapter or scorer wrapper: on exhausted retries from Jev client, raise `JevScoringFailed` (new exception in `jev_gepa_rebuilt/errors.py`). `run_optimize` catches, writes `gepa_run/jev_failure.json` `{message, post_id, batch_idx}`, logs Wandb `run.summary["status"]="jev_failed"`, re-raises exit code 2. Do not continue GEPA loop.

### `evaluate.py`

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py \
  --ablation-id R1_gepa_pair --split test
```

Behavior:

1. Load selected candidate from `outputs/<ablation_id>/dev_selection.json` + `gepa_run/gepa_result.json` candidates list (`study_instruction` key).
2. Load union parquet via `COHORT_UNION_PARQUET`; split `test` (and optional `--split dev` for debugging).
3. Score with `score_batch_with_study_instruction` (post-only state), batch 10, same rate limiter 200/min.
4. Metrics **identical to Stage A union** (`build_results_payload`): F1, accuracy, precision, recall at **dev-A tuned threshold** from `dev_selection.json` and at **0.5**; ROC-AUC, PR-AUC; `subgroup_metrics`; `latency_summary` per request and per post (p50/p90/p99); token and Jev USD totals via `estimate_jev_cost_usd`.
5. Write `outputs/<ablation_id>/test_results.json` (and `labels.parquet`, `requests.parquet` if matching baseline layout).
6. `upload_rebuilt` on ablation output dir; Wandb `job_type="evaluate"`, group `jev_gepa_rebuilt`.

**Single test read per ablation:** if `test_results.json` exists and `--force` not set, exit 0 with message `test_already_scored`.

### Production optimize command template

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py \
  --ablation-id R1_gepa_pair --max-metric-calls 30000
```

Outputs:

- `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/<ablation_id>/gepa_run/gepa_result.json`
- `.../dev_selection.json`
- `.../candidate_dev_scores.jsonl`
- `.../gepa_run/reflection_usage.jsonl`, `acceptance_log.jsonl`, `stop_reason.json`
- R4: `.../gepa_run/component_update_log.jsonl`

S3: `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/<ablation_id>/...`

## Tests to write first

### `tests/test_ablation_registry.py`

Class `TestAblationRegistry`.

```text
when resolving R1_gepa_pair
then score_mode == label_certainty and max_metric_calls == 30000

when resolving R5_gepa_original
then max_metric_calls == 15000 and max_reflection_cost == 2.5

when resolving R7_plain_majority
then score_mode == plain_majority and max_metric_calls == 30000 and the ablation is enabled
```

### `tests/test_evaluate_rebuilt.py`

Class `TestEvaluateRebuilt`.

```text
given tmp ablation dir with dev_selection threshold 0.35 and fake scorer
when evaluate main --split test with parquet fixture
then test_results.json metrics_at_dev_threshold.f1 is computed at 0.35
and metrics_at_0_5.f1 uses 0.5
and payload includes roc_auc and latency p50 keys
```

### `tests/test_jev_failure_stops.py`

Class `TestJevFailureStops`.

```text
given adapter.evaluate raises JevScoringFailed on batch 2
when run_optimize with patched gepa.optimize progressing one iteration
then jev_failure.json written and process exits non-zero
```

## Implementation order

1. Registry + gate helpers + tests
2. `evaluate.py` port from Stage B with union parquet and dev-A threshold
3. Jev failure path + test
4. `run_ablations.py` documenting parallel waves (subprocess, no orchestration framework required)
5. Execute production runs (operator); evaluate after each optimize

## Commands

Tests:

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_ablation_registry.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_evaluate_rebuilt.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_jev_failure_stops.py -q
```

Expected: exit 0.

Production example (R1, long running):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --max-metric-calls 30000
```

Expected: exit 0; `result.total_metric_calls` near 30000; `stop_reason.json` `stop_reason` is `max_metric_calls` or `max_reflection_cost`; Wandb run in group `jev_gepa_rebuilt`.

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/evaluate.py --ablation-id R1_gepa_pair --split test
```

Expected stdout contains `test_results.json`; test F1 fields present.

Parallel launch (operator, four terminals or `run_ablations.py`):

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/run_ablations.py --wave parallel_r1_r2_r3_r7
```

Expected: subprocess PIDs for each ablation; combined rate under 1000 req/min documented in launcher log.

## Must pass

- R1 completes with 350+ iterations **or** documented stop reason and `total_metric_calls` up to budget.
- Each completed ablation has exactly one `test_results.json` unless `--force`.
- Metrics match Stage A union schema (F1 at dev-A threshold and 0.5, AUC, subgroups, latency percentiles, cost).
- Uploads under `jev_gepa_rebuilt/` S3 prefix.

## Must fail

- Starting R4 before R4 smoke pass file is true.
- Starting R5/R6 when R1 confirmed dev-B F1 is not strictly greater than 0.538.
- Running test evaluate twice without `--force` counting as new Jev spend (second call should no-op).

## Commit message

`wire rebuilt ablation registry evaluate test read and jev failure stop`

## Done check

- Registry and evaluate tests green.
- At minimum R1 optimize + test evaluate completed in operator environment with artifacts on S3.
- `dev_selection.json` dev-B F1 within 0.02 of dev-A for selected candidate (plan done criterion; log if not).
