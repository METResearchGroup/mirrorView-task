# Step 5: Smoke and cost re-estimate

## Scope

- **Caller:** `jev_gepa_rebuilt/optimize.py` smoke path, new `jev_gepa_rebuilt/measure_tokens.py` (or `scripts/measure_union_pair_tokens.py` under experiment root only if mirror Stage A pattern)
- **Task:** (1) **100-post** live Jev measurement on union cohort **pair** layout after the study-instruction flip (input tokens per post, latency). (2) **GEPA smoke** with `--smoke --max-metric-calls 120` (120 **posts**) that leaves at least one **rejected** proposal (guard or `HardLabelMarginAcceptance`) and **non-zero** reflection USD in artifacts. (3) **R4 multi-component** smoke with `module_selector="round_robin"` pass criterion. (4) Record measured numbers so the human operator can paste them into `plan.md` and `design.md` estimates tables. The implementer updates those files in the same PR as Step 5 results. This step file does not edit plan or design.
- **Out of scope:** Full R1 30k run, RESULTS.md (Step 7), and edits to forbidden plan assets unless the implementer records measurements and updates plan or design by hand.

## Dependencies

Steps 1 to 4 complete: live `run_optimize`, guards, reflection logging, dev split sidecar.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md` | Estimates table rows to update after smoke |
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` | Cost model section |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | Smoke val subset size 20 |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` | Batch scoring, usage fields |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/measure_tokens.py` (new CLI)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/smoke_checks.py` (new, parse smoke outputs)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` (smoke config: val subsample 20, R4 seed keys, smoke report JSON)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/constants.py` (`SMOKE_JEV_POSTS = 100`, `SMOKE_METRIC_CALLS = 120`, R4 component keys)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_measure_tokens.py` (new, fake client)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_smoke_checks.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_r4_round_robin_smoke.py` (new)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md` (implementer updates manually with smoke numbers)
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` (same)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/**`

## Contracts

### `measure_tokens.py`

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/measure_tokens.py \
  --view pair \
  --n-posts 100 \
  --output experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/_smoke/token_measurement.json
```

Writes JSON:

```json
{
  "n_posts": 100,
  "view": "pair",
  "mean_input_tokens_per_post": <float>,
  "p50_input_tokens_per_post": <float>,
  "p90_input_tokens_per_post": <float>,
  "jev_optimize_usd_per_30k_posts": <float using shared.pricing.estimate_jev_cost_usd>,
  "cohort_parquet": "cohort_union_splits.parquet"
}
```

Sample 100 post ids from GEPA train or dev with `numpy.random.default_rng(GEPA_SEED)`. Score them via `JevGepaRebuiltAdapter` or `score_batch_with_study_instruction` with the seed study instruction.

### GEPA smoke R1 (`R1_gepa_pair`)

- CLI: `--ablation-id R1_gepa_pair --smoke --max-metric-calls 120`
- Smoke overrides: `VAL_SUBSAMPLE_SIZE=20` (Step 3), `rate_cap_per_min=200`
- Requires `OPENAI_API_KEY` for reflection (live call(s) expected within 120 post budget)

Smoke artifacts under `outputs/_smoke/` include `token_measurement.json`, `r1_smoke_report.json`, `r4_smoke_passed.json`, and optional `r5_r6_skipped.json` / `cost_reestimate_notes.txt` (see design.md folder layout).

Pass criteria (`smoke_checks.py`):

```python
def assert_r1_smoke_pass(smoke_dir: Path) -> dict:
    """Raises AssertionError if any check fails.

    Checks:
    - gepa_run/gepa_result.json exists
    - total_metric_calls <= 120
    - at least one reject: acceptance log or gepa_result parents length implies >1 candidates with
      iteration where proposal_accepted false OR stop_reason.json lists guard_reject count >= 1
    - reflection_usage.jsonl exists and sum(usd) > 0 OR dev_selection reflection_cost_usd > 0
    - stop_reason.json present
    """
```

Write `outputs/_smoke/r1_smoke_report.json` with booleans and measured `posts_per_iteration_estimate`.

### R4 multi-component smoke (`R4_gepa_multi_component`)

Seed candidate keys (all strings):

```python
R4_SEED_CANDIDATE = {
    "study_instruction": <default_study_instruction_seed("pair")>,
    "remove_criteria": "- ...",
    "keep_criteria": "- ...",
    "mirror_note": "Mirror post is opposite stance.",
}
```

Run:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py \
  --ablation-id R4_gepa_multi_component --smoke --max-metric-calls 120
```

**Round-robin pass criterion (concrete):** persist `gepa_run/component_update_log.jsonl` each iteration with `{iteration, module_selected, keys_snapshot_hash}`. After run, with `module_selector="round_robin"` and 4 keys, over the first `min(8, num_iterations)` iterations:

1. `module_selected` cycles `study_instruction`, `remove_criteria`, `keep_criteria`, `mirror_note` in that order (allow wrap).
2. At least **3 distinct** keys have `keys_snapshot_hash` different from iteration 0 (mutation occurred).

`test_r4_round_robin_smoke.py` uses synthetic log fixture; live smoke must write the log from a GEPA callback `on_iteration_end` reading `event["module_selected"]` or equivalent from proposal metadata (if not exposed, record hash of `candidate[key]` for the key chosen by `(iteration % 4)` expectation).

Set `outputs/_smoke/r4_smoke_passed.json` `{"passed": true}` only when checks pass.

### Cost re-estimate handoff (implementer edit)

After both smokes and token measurement, the implementer updates:

- `docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md` **Estimates** table (tokens per post, iterations, USD rows)
- `docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` **Cost model** section

Use formulas:

- `iterations_estimate = floor(max_metric_calls / mean_posts_per_iteration)`
- `mean_posts_per_iteration = 50 + VAL_SUBSAMPLE_SIZE * accept_rate` (use observed accept rate from R1 smoke if available, else 0.25)
- `jev_optimize_usd = estimate_jev_cost_usd(30_000 * mean_input_tokens_per_post, 0)`

Record before/after in commit message body or `outputs/_smoke/cost_reestimate_notes.txt` (not committed to plan folder by CI).

## Tests to write first

### `tests/test_measure_tokens.py`

Class `TestMeasureTokens`.

```text
given fake Jev client returning usage input_tokens=500 per post
when measure_union_pair_tokens n_posts=10
then mean_input_tokens_per_post == 500
and jev_optimize_usd_per_30k_posts > 0
```

### `tests/test_smoke_checks.py`

Class `TestSmokeChecks`.

```text
given fixture gepa_result and reflection_usage with one reject and usd 0.01
when assert_r1_smoke_pass
then returns dict with passed true

given reflection_usage empty and no rejects
when assert_r1_smoke_pass
then raises AssertionError
```

### `tests/test_r4_round_robin_smoke.py`

Class `TestR4RoundRobinLog`.

```text
given component_update_log with 8 iterations cycling 4 keys and 3 hash changes
when evaluate_r4_round_robin_smoke
then passed is True

given log where only study_instruction ever changes
when evaluate_r4_round_robin_smoke
then passed is False
```

## Implementation order

1. `measure_tokens.py` + unit test (fake client)
2. `smoke_checks.py` + tests
3. R4 logging hook in `optimize.py` smoke branch
4. Run live commands on the operator machine, and save reports under `outputs/_smoke/`
5. Implementer edits plan.md and design.md estimates

## Commands

Unit tests (CI):

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_measure_tokens.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_smoke_checks.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_r4_round_robin_smoke.py -q
```

Expected: exit 0.

Live smoke (requires API keys; skip in CI without secrets):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/measure_tokens.py --view pair --n-posts 100 \
  --output experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/_smoke/token_measurement.json
```

Expected stdout ends with path written; JSON `mean_input_tokens_per_post` between 400 and 1300 (sanity band; adjust test doc if out of band).

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --smoke --max-metric-calls 120
```

Expected: exit 0; `outputs/R1_gepa_pair/gepa_run/gepa_result.json` exists.

```bash
PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.smoke_checks import assert_r1_smoke_pass
report = assert_r1_smoke_pass(Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/R1_gepa_pair'))
print('r1_smoke_passed', report['passed'])
"
```

Expected stdout contains `r1_smoke_passed True`.

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R4_gepa_multi_component --smoke --max-metric-calls 120
PYTHONPATH=. uv run python -c "
from pathlib import Path
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.smoke_checks import evaluate_r4_round_robin_smoke
p = evaluate_r4_round_robin_smoke(Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs/R4_gepa_multi_component'))
assert p['passed']
print('r4_smoke_ok')
"
```

Expected stdout: `r4_smoke_ok`

## Must pass

- 100-post token JSON on disk with per-post token stats.
- R1 smoke: `total_metric_calls <= 120`, >=1 reject, reflection USD > 0.
- R4 smoke: round-robin criterion satisfied before Step 6 launches R4 production.
- Implementer updates plan/design estimates after live smokes (tracked in PR description).

## Must fail

- Declaring R4 production ready when `r4_smoke_passed.json` is false.
- Using `--max-metric-calls` as HTTP batch count (must remain posts).

## Commit message

`add union token measurement and gepa smoke checks for r1 and r4`

## Done check

- Unit pytest block exits 0.
- Live smokes produce `_smoke/` and ablation output dirs with reflection_usage and reject evidence.
- `cost_reestimate_notes.txt` or PR text lists new tokens/post and revised iteration/USD estimates for plan.md and design.md.
