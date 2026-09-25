# Step 3: GEPA policies (val subsample, acceptance, batch sampler)

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` `run_optimize`
- **Task:** Implement GEPA 0.1.4 hooks under `jev_gepa_rebuilt/policies/`: **100-post** validation subsample on accept only, **hard-label** acceptance with **+2** correct margin on **25-post** reflection minibatches, and **error-focused** train `BatchSampler`. Connect them in `gepa.optimize` with `reflection_minibatch_size=25`, post-based `max_metric_calls`, `use_merge=False`, and explain post budget accounting in module docstrings. The stub run must call `gepa.optimize` with custom policy instances (mock adapter in tests, optional dry-run with a tiny budget in an integration test).
- **Out of scope:** dev-A/dev-B top-10 selection, guards, reflection cost JSONL, production 30k runs (Steps 4 to 6), editing `jev_gepa/optimize.py`.

## Dependencies

Steps 1 and 2 must provide `JevGepaRebuiltAdapter`, constants (`VAL_SUBSAMPLE_SIZE`, `ACCEPTANCE_MARGIN_CORRECT`, `REFLECTION_MINIBATCH_SIZE`), and union split loader.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/.venv/lib/python3.12/site-packages/gepa/api.py` | `optimize` kwargs resolution |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/strategies/eval_policy.py` | `EvaluationPolicy` protocol |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/strategies/acceptance.py` | `AcceptanceCriterion` protocol |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/strategies/batch_sampler.py` | `BatchSampler` protocol |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | Wandb init, `run_dir`, smoke pattern |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/policies/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/policies/val_subsample_on_accept.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/policies/hard_label_acceptance.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/policies/error_focused_sampler.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/splits.py` (new, `load_gepa_union_splits`)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` (replace stub with `run_optimize`)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_val_subsample_policy.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_hard_label_acceptance.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_error_focused_sampler.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_run_optimize_wiring.py` (new)

## Files forbidden to change

- `/workspace/.venv/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py`
- `/workspace/webapp/**`

## Contracts

### `policies/val_subsample_on_accept.py`

```python
class ValSubsampleOnAcceptPolicy:
    """EvaluationPolicy that returns an empty eval batch on reject and 100 val ids on accept.

    On accept, sample VAL_SUBSAMPLE_SIZE ids with rng seeded by (GEPA_SEED, state.i).
    Implement get_eval_batch, get_best_program, get_valset_score consistent with
    FullEvaluationPolicy averaging over stored subsample scores only.
    """
```

GEPA calls the val policy after acceptance. When the proposal is rejected, return `[]` so the runner does not score the full 300-post val set. Unit-test `get_eval_batch` before and after a synthetic accept flag.

### `policies/hard_label_acceptance.py`

```python
class HardLabelMarginAcceptance:
    """AcceptanceCriterion: compare hard labels at 0.5 on reflection minibatch.

    should_accept when correct_after >= correct_before + ACCEPTANCE_MARGIN_CORRECT (2).
    Use proposal.eval_before / eval_after trajectories or outputs; do not sum soft adapter scores.
    Optional reject_reason(proposal, state) -> str for logging.
    """
```

Parent and child are both scored on the same 25-post minibatch by GEPA before `should_accept` runs (50 posts total per proposal).

### `policies/error_focused_sampler.py`

```python
class ErrorFocusedBatchSampler:
    """BatchSampler preferring misclassified train ids, confident errors, close vote splits.

    Maintain epoch_shuffled fallback. Accept optional indexes: misclassified set,
    confident_error set, contrastive partner map (may be empty until Step 4 builds index).
    next_minibatch_ids returns REFLECTION_MINIBATCH_SIZE ids.
    """
```

Priority order (document in docstring): misclassification from last eval, confident errors, `abs(n_keep - n_remove) <= 1`, contrastive opposites, then epoch shuffle.

### `jev_gepa_rebuilt/splits.py`

```python
def load_gepa_union_splits() -> tuple[list[JevDataInst], list[JevDataInst]]:
    """Load train and val from COHORT_UNION_PARQUET gepa_subset train|val; map remove_share."""
```

### `optimize.py` `run_optimize`

Call `gepa.optimize` with at minimum:

```python
gepa.optimize(
    seed_candidate={STUDY_COMPONENT_KEY: default_study_instruction_seed(view)},
    trainset=trainset,
    valset=valset,
    adapter=adapter,
    reflection_lm=...,
    max_metric_calls=config.max_metric_calls,
    max_reflection_cost=...,
    reflection_minibatch_size=REFLECTION_MINIBATCH_SIZE,
    batch_sampler=ErrorFocusedBatchSampler(...),
    val_evaluation_policy=ValSubsampleOnAcceptPolicy(...),
    acceptance_criterion=HardLabelMarginAcceptance(...),
    # module_selector: omit (GEPA default) for single-key R1 to R3 and R5 to R7; Step 5/6 set round_robin only for R4
    use_merge=False,
    candidate_selection_strategy="pareto",
    seed=GEPA_SEED,
    run_dir=str(config.run_dir),
    use_wandb=True,
    wandb_attach_existing=True,
)
```

`init_run` must use `WandbRunSpec(group=WANDB_GROUP, job_type="optimize", ...)`.

Log `posts_scored` in wandb config: explain that `max_metric_calls` and `result.total_metric_calls` are in **posts** because adapter reports post counts.

Smoke CLI: `--smoke --max-metric-calls 120` uses `VAL_SUBSAMPLE_SIZE` override 20 in smoke config only (design smoke note).

## Tests to write first

### `tests/test_hard_label_acceptance.py`

Class `TestHardLabelMarginAcceptance`.

```text
given parent correct=10 child correct=11 on 25 examples
when should_accept
then False

given parent correct=10 child correct=12
when should_accept
then True

given equal correct counts
when should_accept
then False
```

Build minimal `CandidateProposal` mocks with trajectory lists and threshold 0.5 labels.

### `tests/test_val_subsample_policy.py`

Class `TestValSubsampleOnAcceptPolicy`.

```text
given policy configured for 100 ids and state flag proposal_rejected
when get_eval_batch
then returns []

given proposal accepted at iteration 3
when get_eval_batch
then returns exactly 100 ids deterministic for seed GEPA_SEED and i=3
```

### `tests/test_error_focused_sampler.py`

Class `TestErrorFocusedBatchSampler`.

```text
given train loader of 50 ids and misclassified set containing id A
when next_minibatch_ids called 10 times
then A appears in more minibatches than a random id not in misclassified set
and each minibatch length is 25
```

### `tests/test_run_optimize_wiring.py`

Class `TestRunOptimizeWiring`.

```text
given run_optimize with gepa.optimize patched to capture kwargs
when smoke config R1_gepa_pair
then kwargs include acceptance_criterion instance of HardLabelMarginAcceptance
and val_evaluation_policy instance of ValSubsampleOnAcceptPolicy
and batch_sampler instance of ErrorFocusedBatchSampler
and reflection_minibatch_size == 25
and use_merge is False
and module_selector is not passed for R1_gepa_pair smoke config
```

Patch `gepa.optimize` to return minimal `GEPAResult` without network.

## Implementation order

1. Policy modules with protocols satisfied
2. Unit tests for each policy
3. `load_gepa_union_splits`
4. `run_optimize` wiring test
5. `optimize.py` implementation

## Commands

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_val_subsample_policy.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_hard_label_acceptance.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_error_focused_sampler.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_run_optimize_wiring.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/ -q
```

Expected: exit 0 (includes Step 1 and 2 tests).

Optional import check:

```bash
PYTHONPATH=. uv run python -c "
from gepa.strategies.acceptance import AcceptanceCriterion
from gepa.strategies.eval_policy import EvaluationPolicy
from gepa.strategies.batch_sampler import BatchSampler
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.hard_label_acceptance import HardLabelMarginAcceptance
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.val_subsample_on_accept import ValSubsampleOnAcceptPolicy
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.error_focused_sampler import ErrorFocusedBatchSampler
assert isinstance(HardLabelMarginAcceptance(), AcceptanceCriterion)
print('gepa_hooks_ok')
"
```

Expected stdout: `gepa_hooks_ok`

## Must pass

- Custom policies plug into `gepa.optimize` without string presets for sampled val.
- Acceptance uses +2 hard-label margin, not `strict_improvement` soft sums.
- Reflection minibatch size 25.
- Post budget semantics documented and unchanged from Step 2 adapter.

## Must fail

- `acceptance_criterion="strict_improvement"` in rebuilt runner.
- `val_evaluation_policy="full_eval"` for production config.
- `use_merge=True` (rebuild disables merge until val overlap is guaranteed).
- `reflection_minibatch_size=10` in rebuilt runner.

## Commit message

`add gepa rebuilt val subsample acceptance and error-focused sampler policies`

## Done check

- All pytest commands above exit 0.
- `test_run_optimize_wiring` proves custom hooks are passed to `gepa.optimize`.
