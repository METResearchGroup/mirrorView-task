# Step 6: Build the GEPA adapter and optimize runner

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` `main`
- **Task:** Build `jev_gepa/adapter.py` (`JevGepaAdapter`, conforming to `gepa.core.adapter.GEPAAdapter`) and `jev_gepa/optimize.py` (`gepa.optimize` runner). Score minibatches in groups of 10 via `jev_scorer.score_batch` with `instruction=candidate["instruction"]` (single Jev call path: rate limiter, retries, latency, and token/cost logging all live in `jev_scorer.py` from Step 4). Default per-example score is P(gold label). B4 uses asymmetric reward (TP +1, FN -3, FP -1, TN +0.5). `make_reflective_dataset` emits post text(s), gold label, human vote split, P(remove), stance, toxicity, and threshold crossing. Connect reflection models, dev-F1 candidate selection over all accepted candidates, Wandb (`wandb_tracking.init_run`, `group=jev_gepa`, `job_type=optimize`, `wandb_attach_existing=True`), and per-process `RequestStartLimiter` at 200 requests per minute passed into `run_scoring_pass` / `score_batch`. Unit tests with fake scorer and fake reflection LM. Tiny-budget smoke for both `openai/gpt-6-luna` and `openai/gpt-5.6-terra`.
- **Out of scope:** Full Stage B production runs (Step 7), transfer evals, Stage A rescoring, analysis scripts.

## Dependencies

Steps 1 to 5 must exist:

- `shared/jev_scorer.py`, `shared/prompt.py`, `shared/splits.py`, `shared/metrics.py`, `shared/wandb_tracking.py`
- Stage A seed prompts under `jev_baseline/outputs/<ablation_id>/` (A1 to A3 seeds for B1 to B3; A1 for B1-T and B4)
- Frozen GEPA trainset (up to 2,000 balanced) and valset (300 balanced) from `splits.py`
- `gepa==0.1.4` in `pyproject.toml`

## Verified GEPA API (gepa 0.1.4)

Use these exact names in contracts and code:

| Symbol | Module | Notes |
|--------|--------|-------|
| `gepa.optimize` | `gepa` | Returns `GEPAResult` |
| `EvaluationBatch` | `gepa.core.adapter` | Fields: `outputs`, `scores`, `trajectories`, `objective_scores`, `num_metric_calls` |
| `GEPAAdapter` | `gepa.core.adapter` | Protocol methods: `evaluate`, `make_reflective_dataset` |
| `GEPAResult` | `gepa.core.result` | Fields: `candidates`, `parents`, `val_aggregate_scores`, `val_subscores`, `per_val_instance_best_candidates`, `discovery_eval_counts`, `total_metric_calls`, `num_full_val_evals`, `run_dir`, `seed`, `_str_candidate_key` |
| `GEPAResult.best_idx` | property | `argmax(val_aggregate_scores)` |
| `GEPAResult.best_candidate` | property | `candidates[best_idx]` (unwraps str seed when `_str_candidate_key` set) |

`gepa.optimize` keyword args used in this step:

| Parameter | B1, B2, B3, B4 | B1-T |
|-----------|----------------|------|
| `reflection_lm` | `openai/gpt-6-luna` | `openai/gpt-5.6-terra` |
| `max_reflection_cost` | `5.0` | `20.0` |
| `reflection_minibatch_size` | `10` | `10` |
| `candidate_selection_strategy` | `"pareto"` | `"pareto"` |
| `use_merge` | `True` | `True` |
| `max_metric_calls` | `9000` (smoke: `60`) | `9000` (smoke: `60`) |
| `seed` | `20260924` | `20260924` |
| `use_wandb` | `True` | `True` |
| `wandb_attach_existing` | `True` | `True` |

LiteLLM model ids `openai/gpt-6-luna` and `openai/gpt-5.6-terra` are the intended ids per design.md. Do not call the OpenAI API in unit tests. The tiny-budget smoke in Step 6 is the first live check that both ids resolve through GEPA.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | GEPA settings, B4 reward, adapter responsibilities, folder names |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` | Reflection and Jev cost per run |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` | Batch-10 scoring interface (from Step 4) |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py` | `STUDY_INSTRUCTION`, view renderers |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/metrics.py` | Dev-F1 candidate selection |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/outputs/A1_pair_study_prompt/` | B1 and B4 seed instruction text |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/adapter.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/B1_gepa_pair/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/B1T_gepa_pair_terra/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/B2_gepa_original/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/B3_gepa_mirror/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/B4_gepa_asymmetric_reward/.gitkeep` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/__init__.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/conftest.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_adapter.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/test_optimize.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests/fakes.py` (new)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` (import and call `score_batch` / `run_scoring_pass` only; instruction override is defined in Step 4)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` (Step 7 writes Stage B)
- `/workspace/pyproject.toml` (Step 1 added `gepa`)
- `/workspace/webapp/**`

## Ablation registry (exact)

| `ablation_id` | Seed from Stage A | View | Score mode | Reflection LM | `max_reflection_cost` |
|---------------|-------------------|------|------------|---------------|----------------------|
| `B1_gepa_pair` | A1 instruction | `pair` | `probability` | `openai/gpt-6-luna` | `5.0` |
| `B1T_gepa_pair_terra` | A1 instruction | `pair` | `probability` | `openai/gpt-5.6-terra` | `20.0` |
| `B2_gepa_original` | A2 instruction | `original` | `probability` | `openai/gpt-6-luna` | `5.0` |
| `B3_gepa_mirror` | A3 instruction | `mirror` | `probability` | `openai/gpt-6-luna` | `5.0` |
| `B4_gepa_asymmetric_reward` | A1 instruction | `pair` | `asymmetric` | `openai/gpt-6-luna` | `5.0` |

GEPA component key (single optimizable text field): `instruction`.

`seed_candidate` passed to `gepa.optimize`:

```python
{"instruction": "<seed instruction text from Stage A results or prompt.py render>"}
```

Run directory per ablation:

```text
experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/<ablation_id>/gepa_run/
```

## Contracts

### `jev_gepa/adapter.py`

```python
from dataclasses import dataclass
from typing import Any, Literal

ScoreMode = Literal["probability", "asymmetric"]
ViewName = Literal["pair", "original", "mirror"]

@dataclass(frozen=True)
class JevDataInst:
    post_id: str
    original_text: str
    mirror_text: str
    post_1_role: str  # original or mirror; required for pair view state_text
    post_2_role: str
    label: int  # cohort parquet column; 1 = remove
    n_keep: int
    n_remove: int
    n_raters: int
    sampled_stance: str
    sample_toxicity_type: str

@dataclass(frozen=True)
class JevTrajectory:
    post_id: str
    view: ViewName
    instruction: str
    p_remove: float
    label: int
    n_keep: int
    n_remove: int
    sampled_stance: str
    sample_toxicity_type: str
    threshold_crossed: bool
    error: str | None = None

@dataclass(frozen=True)
class JevRolloutOutput:
    post_id: str
    p_remove: float

class JevGepaAdapter:
    def __init__(
        self,
        *,
        view: ViewName,
        score_mode: ScoreMode = "probability",
        scorer: Any | None = None,  # optional injectable fake matching jev_scorer.score_batch signature
        client: TypeSafeClient | None = None,  # default: jev_scorer.build_client(secrets.get_jev_api_key())
        rate_limiter: RequestStartLimiter | None = None,
        threshold: float = 0.5,
        batch_size: int = 10,
    ) -> None: ...

    def evaluate(
        self,
        batch: list[JevDataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[JevTrajectory, JevRolloutOutput]:
        """
        Score batch in groups of batch_size via jev_scorer.score_batch(
            client, state_texts, view, instruction=candidate["instruction"]
        ) behind the shared rate limiter and retries.run_with_retries (same path as Stage A).
        Do not call client.system_one directly in the adapter.
        Default score (probability mode): P(remove) if gold is remove else 1 - P(remove).
        Asymmetric mode (B4): TP +1, FN -3, FP -1, TN +0.5 using threshold 0.5 hard labels.
        On per-example failure return score 0.0 and populate trajectory.error (do not raise).
        Set EvaluationBatch.num_metric_calls to number of Jev API requests made.
        """

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[JevTrajectory, JevRolloutOutput],
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Return {"instruction": [records...]}.
        Each record schema:
          {
            "Inputs": {"post_text": str} or {"original_text": str, "mirror_text": str},
            "Generated Outputs": {"p_remove": str, "predicted_label": str},
            "Feedback": str,  # includes gold label, vote split, stance, toxicity, threshold crossed
          }
        """
```

Asymmetric reward (B4 only, threshold 0.5):

| Outcome | Score |
|---------|-------|
| TP (gold remove, pred remove) | +1.0 |
| FN (gold remove, pred keep) | -3.0 |
| FP (gold keep, pred remove) | -1.0 |
| TN (gold keep, pred keep) | +0.5 |

### `jev_gepa/optimize.py`

```python
@dataclass(frozen=True)
class OptimizeConfig:
    ablation_id: str
    view: ViewName
    score_mode: ScoreMode
    reflection_lm: str
    max_reflection_cost: float
    max_metric_calls: int
    seed: int
    run_dir: Path
    rate_cap_per_min: int = 200

def load_gepa_splits() -> tuple[list[JevDataInst], list[JevDataInst], list[JevDataInst]]:
    """Read splits.COHORT_PARQUET. trainset: gepa_subset=='train'. valset: gepa_subset=='val'.
    devset: split=='dev'. Map parquet columns label, n_keep, n_remove, sample_toxicity_type, post_1_role, post_2_role."""

def load_seed_instruction(ablation_id: str) -> str:
    """Default: prompt.build_noul_instruction(0, view) for the ablation view. Optional: read cached seed from Stage A outputs."""

def select_candidate_on_dev(
    result: GEPAResult,
    *,
    devset: list[JevDataInst],
    adapter: JevGepaAdapter,
) -> tuple[int, dict[str, str], float]:
    """
    Evaluate every candidate in result.candidates on dev via adapter.evaluate
    (which calls score_batch with instruction=candidate["instruction"]).
    Return (candidate_idx, candidate_dict, dev_f1 at threshold 0.5).
    Do not use result.best_idx alone; dev-F1 is the selection rule.
    """

def run_optimize(config: OptimizeConfig, *, smoke: bool = False) -> GEPAResult:
    """
    Open Wandb run via wandb_tracking (group jev_gepa, job_type optimize).
    Call gepa.optimize with wandb_attach_existing=True inside that run.
    Apply per-process RequestStartLimiter at config.rate_cap_per_min.
    Persist GEPAResult.to_dict(), selected candidate, and dev selection metadata under run_dir.
    """

def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id, --smoke, --max-metric-calls override for smoke."""
```

`dev_selection.json` written beside `gepa_run/`:

| Key | Meaning |
|-----|---------|
| `selected_candidate_idx` | int index into `result.candidates` |
| `selected_dev_f1` | float at threshold 0.5 |
| `gepa_best_idx` | int from `result.best_idx` (logged for comparison) |
| `reflection_lm` | str model id |
| `reflection_cost_usd` | float from Wandb or GEPA logger if available |
| `total_metric_calls` | int |

## Tests to write first

### `jev_gepa/tests/fakes.py`

- `FakeJevBatchScorer`: callable matching `jev_scorer.score_batch(client, state_texts, view, instruction=...)`; records `instruction` and returns deterministic `BatchResult` probabilities per post order without network.
- `FakeReflectionLM`: records calls, returns fixed instruction mutation.

### `jev_gepa/tests/test_adapter.py`

Class `TestJevGepaAdapterEvaluate`, `TestJevGepaAdapterReflectiveDataset`, `TestAsymmetricReward`.

```text
given a batch of 12 JevDataInst and FakeJevBatchScorer
when evaluate with capture_traces=False and candidate instruction CAND
then len(outputs)==12 and len(scores)==12
and num_metric_calls==2 (two batch-10 requests, last partial batch)
and FakeJevBatchScorer received instruction=CAND on every score_batch call
and no exception is raised

given gold remove with p_remove 0.9 and gold keep with p_remove 0.1 in probability mode
when evaluate
then scores are approximately 0.9 and 0.9

given gold remove predicted keep (p_remove 0.4) in asymmetric mode
when evaluate at threshold 0.5
then score is -3.0

given gold keep predicted keep (p_remove 0.1) in asymmetric mode
when evaluate
then score is +0.5

given eval_batch with one wrong prediction and capture_traces=True
when make_reflective_dataset for component instruction
then one record Feedback mentions gold label, vote split, stance, toxicity, and threshold crossed

given scorer raises on one post_id
when evaluate
then that example score is 0.0
and trajectory.error is populated
and the batch does not raise
```

### `jev_gepa/tests/test_optimize.py`

Class `TestSelectCandidateOnDev`, `TestRunOptimizeSmoke`.

```text
given two fake candidates where candidate 1 has higher dev F1
when select_candidate_on_dev
then returned idx is 1
and dev_f1 matches metrics.probability_metrics on dev

given smoke config with max_metric_calls=60 and FakeReflectionLM patched
when run_optimize for B1_gepa_pair
then result.total_metric_calls <= 60
and dev_selection.json exists
and selected_candidate_idx is an int

given the same smoke harness with reflection_lm openai/gpt-6-luna mocked
when run_optimize
then optimize kwargs reflection_lm equals openai/gpt-6-luna

given smoke harness with reflection_lm openai/gpt-5.6-terra mocked for B1T_gepa_pair_terra
when run_optimize
then max_reflection_cost is 20.0
```

## Implementation order

One Git commit per unit. Full auto.

1. Scaffold `adapter.py`, `optimize.py`, `fakes.py`, and test files.
2. Implement `JevDataInst`, `JevGepaAdapter.evaluate` (probability mode) until batching and scoring tests pass.
3. Implement asymmetric reward branch until `TestAsymmetricReward` passes.
4. Implement `make_reflective_dataset` until reflective dataset tests pass.
5. Implement `load_gepa_splits`, `load_seed_instruction`, and `select_candidate_on_dev` until selection tests pass.
6. Implement `run_optimize` and `main` with Wandb attach and rate limiter wiring until mocked smoke tests pass.
7. Run tiny-budget live smoke for `B1_gepa_pair` (`max_metric_calls=60`, valset subgroup of 20 posts).
8. Run tiny-budget live smoke for `B1T_gepa_pair_terra` with the same caps.

## Commands

Unit tests (no network):

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/tests -q
```

Expected: exit 0.

Tiny-budget smoke (live Jev + live reflection; requires API keys):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py \
  --ablation-id B1_gepa_pair \
  --smoke \
  --max-metric-calls 60

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py \
  --ablation-id B1T_gepa_pair_terra \
  --smoke \
  --max-metric-calls 60
```

Expected per smoke run:

- stdout contains `ablation_id=... total_metric_calls<=60 selected_dev_f1=`
- `jev_gepa/outputs/<ablation_id>/gepa_run/` exists
- `jev_gepa/outputs/<ablation_id>/dev_selection.json` exists
- Wandb run in group `jev_gepa` with `job_type=optimize`
- No `FileNotFoundError` for reflection model id (confirms LiteLLM id strings are accepted)

Verify GEPAResult fields after smoke:

```bash
PYTHONPATH=. uv run python -c "
import json
from pathlib import Path
p = Path('experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/outputs/B1_gepa_pair/gepa_run/gepa_result.json')
d = json.loads(p.read_text())
for k in ('candidates','val_aggregate_scores','per_val_instance_best_candidates','best_idx'):
    assert k in d or k=='best_idx'
print('GEPAResult keys OK', len(d['candidates']), 'candidates')
"
```

Expected: prints candidate count >= 1.

## Must pass

- `JevGepaAdapter` implements `evaluate` and `make_reflective_dataset` with exact GEPA signatures.
- All Jev scoring goes through `jev_scorer.score_batch` with `instruction=candidate["instruction"]`; no direct `system_one` calls in the adapter.
- Batch size 10 enforced; `num_metric_calls` reported per `EvaluationBatch`.
- Default score is P(gold label); B4 uses asymmetric table.
- `select_candidate_on_dev` uses dev F1 at 0.5, not `GEPAResult.best_idx` alone.
- `gepa.optimize` called with `candidate_selection_strategy='pareto'`, `use_merge=True`, `reflection_minibatch_size=10`, `seed=20260924`.
- Per-process rate cap is 200 requests per minute during optimize.
- Unit tests pass without network.
- Tiny-budget smoke completes for both Luna and Terra ablations.

## Must fail

- Using `result.best_idx` as the final selected candidate without dev-F1 evaluation.
- Raising from `evaluate` on a single example failure (GEPA contract violation).
- Direct `client.system_one` calls in `adapter.py` (bypasses shared rate limiter, retries, and request logging).
- Full `max_metric_calls=9000` production run in this step (Step 7).
- Transfer evals in this step.
- Reflection cap above $5 on Luna runs or above $20 on B1-T.

## Commit messages

1. `feat(jev-gepa): scaffold GEPA adapter and optimize runner`
2. `feat(jev-gepa): implement JevGepaAdapter probability scoring`
3. `feat(jev-gepa): add B4 asymmetric reward scoring`
4. `feat(jev-gepa): implement make_reflective_dataset feedback fields`
5. `feat(jev-gepa): add dev-F1 candidate selection helper`
6. `feat(jev-gepa): wire gepa.optimize with Wandb and rate limiter`
7. `test(jev-gepa): tiny-budget GEPA smoke B1_gepa_pair (Luna)`
8. `test(jev-gepa): tiny-budget GEPA smoke B1T_gepa_pair_terra (Terra)`

## Implement-from-spec notes

Phase 1 names `jev_gepa/optimize.py` `main` as the caller. Phase 2 scaffolds adapter, optimize, fakes, and tests. Phase 3 locks dataclasses and method signatures above (GEPA names verified against gepa 0.1.4). Phase 4 writes tests from given/when/then blocks. Phase 5 follows implementation order. Phase 6 is complete when unit tests pass and both tiny-budget smokes finish without model id errors.
