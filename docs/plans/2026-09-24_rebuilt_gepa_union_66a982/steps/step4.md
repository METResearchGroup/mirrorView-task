# Step 4: Candidate selection, guards, and logging

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` `run_optimize` (post-`gepa.optimize`), `jev_gepa_rebuilt/selection.py`, `jev_gepa_rebuilt/guards.py`, `jev_gepa_rebuilt/reflection_logging.py`
- **Task:** Build a deterministic stratified dev-A/dev-B split (seed `GEPA_SEED`, sidecar `data/dev_ab_split.json`, S3 via `upload_rebuilt`). After optimization, preselect the **top 10 accepted** candidates by validation subsample score, filter by **VAL_DEV_GAP_MAX** balanced-accuracy gap (val subsample vs dev-A at 0.5), then tune the classification threshold on dev-A F1 and record dev-B F1 at that threshold. Persist `dev_selection.json` and `candidate_dev_scores.jsonl`. Enforce proposal guards (length cap and train-text quoting only). Log **per reflection call** token usage and USD, `acceptance_log.jsonl`, stop reason, and per-candidate dev metrics to Wandb.
- **Out of scope:** Production 30k ablation launches (Step 6), 100-post token smoke (Step 5), editing `plan.md` or `design.md`, changing Steps 1 to 3 contracts.

## Dependencies

Steps 1 to 3: `JevGepaRebuiltAdapter`, policies (`ValSubsampleOnAcceptPolicy`, `HardLabelMarginAcceptance`, `ErrorFocusedBatchSampler`), `load_gepa_union_splits()`, constants (`GEPA_SEED`, `VAL_SUBSAMPLE_SIZE`, `CANDIDATE_DEV_SCORES_FILENAME`, `DEV_SELECTION_FILENAME`).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md` | Guards table, dev top-10 selection, reflection logging destinations |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py` | `select_candidate_on_dev`, `_persist_run_outputs`, `_reflection_cost_usd` patterns |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/metrics.py` | `tune_threshold_for_f1`, `probability_metrics` |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py` | `COHORT_UNION_PARQUET`, dev rows |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/lm.py` | `LM` LiteLLM `usage` and `total_cost` / `total_tokens_in` / `total_tokens_out` |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/api.py` | `max_reflection_cost`, `LM` conversion, `MaxReflectionCostStopper` wiring |
| `/workspace/.venv/lib/python3.12/site-packages/gepa/utils/stop_condition.py` | `MaxReflectionCostStopper` reads `reflection_lm.total_cost` |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/pricing.py` (add reflection LM USD helpers only)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_pricing_reflection.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/data/dev_ab_split.json` (generated at runtime; commit only if repo policy requires fixture; tests use tmp paths)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/constants.py` (guard/selection constants)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/splits.py` (extend: dev load, dev-A/B)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/dev_ab.py` (new, build/write split sidecar)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/guards.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/selection.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/reflection_logging.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py` (wire guards, reflection LM wrapper, selection, artifacts)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/policies/hard_label_acceptance.py` (optional `reject_reason` hook for guard rejects)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_dev_ab_split.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_guards.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_selection_top10.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_reflection_logging.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_run_optimize_selection_artifacts.py` (new)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/steps/step1.md` through `step3.md`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/**`
- `/workspace/.venv/**`

## Contracts

### Constants (`constants.py` additions)

```python
DEV_AB_SPLIT_RELATIVE = Path("data/dev_ab_split.json")  # under EXPERIMENT_ROOT
TOP_ACCEPTED_CANDIDATES = 10
MAX_OPTIMIZED_COMPONENT_CHARS = 4000
TRAIN_QUOTE_MIN_SUBSTRING_LEN = 40
VAL_DEV_GAP_MAX = 0.15  # max(val_balanced_acc@0.5 - dev_a_balanced_acc@0.5) for top-10 filter
DEV_B_CONFIRM_MAX_F1_DROP = 0.02  # vs dev-A at same threshold (done check in Step 7)
ACCEPTANCE_LOG_FILENAME = "acceptance_log.jsonl"  # under gepa_run/
REFLECTION_USD_PER_MILLION = {
    "openai/gpt-6-luna": (0.10, 0.50),  # input, output per 1M tokens
    "openai/gpt-5.6-terra": (2.0, 12.0),
}
MAX_REFLECTION_COST_USD = {
    "openai/gpt-6-luna": 5.0,
    "openai/gpt-5.6-terra": 40.0,
}
HALF_BUDGET_MAX_REFLECTION_COST_USD = 2.50  # R5/R6
REFLECTION_USAGE_JSONL = "reflection_usage.jsonl"  # under gepa_run/
STOP_REASON_FILENAME = "stop_reason.json"
```

### `shared/pricing.py`

```python
def estimate_reflection_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """USD from pinned Luna/Terra per-1M rates in constants (fallback 0.0 if unknown)."""
```

### `dev_ab.py`

```python
def dev_ab_split_path() -> Path:
    """experiments/predict_keep_remove_jev_gepa_2026_09_23/data/dev_ab_split.json"""

def build_or_load_dev_ab_split(
    *,
    parquet_path: Path = COHORT_UNION_PARQUET,
    seed: int = GEPA_SEED,
    write: bool = True,
) -> dict[str, list[str]]:
    """Stratified 50/50 split of dev post_ids into dev_a_ids and dev_b_ids.

    Persist JSON: {seed, dev_a_ids, dev_b_ids, n_dev_a, n_dev_b}.
    Call upload_rebuilt(dev_ab_split_path()) after write.
    """
```

Use `sklearn.model_selection.train_test_split` on dev rows with `stratify=label`, `test_size=0.5`, `random_state=seed`.

### `splits.py` extensions

```python
def load_dev_instances(*, split: Literal["dev_a", "dev_b", "dev"]) -> list[JevDataInst]:
    """Map post_id via dev_ab_split.json; full dev if split=='dev'."""
```

### `guards.py`

```python
@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str | None

def check_candidate_guards(
    candidate: dict[str, str],
    *,
    train_post_texts: Sequence[str],
) -> GuardResult:
```

Rules (all optimized string values in `candidate`):

1. **Length:** any value length `> MAX_OPTIMIZED_COMPONENT_CHARS` -> reject `length_cap`.
2. **Memorization:** any contiguous substring of length `>= TRAIN_QUOTE_MIN_SUBSTRING_LEN` found in any train post text (original and mirror columns) -> reject `train_substring`.

Build a train substring index once per run from GEPA train parquet. A lazy 40-gram scan is fine for about 2k train rows. In tests, use a tiny corpus.

Run guards **before** you treat a proposal as accepted. After `HardLabelMarginAcceptance` passes, run `check_candidate_guards`. If guards fail, set `proposal_rejected` and log the reason to Wandb. Append each outcome to `gepa_run/acceptance_log.jsonl`.

### `reflection_logging.py`

GEPA 0.1.4 mechanism (verified):

- Pass `reflection_lm` as model string -> `gepa.optimize` builds `gepa.lm.LM` which reads LiteLLM `completion.usage` (`prompt_tokens`, `completion_tokens`) and `litellm.completion_cost` into `total_cost`, `total_tokens_in`, `total_tokens_out` (`gepa/lm.py` lines 121 to 129, 73 to 84).
- `max_reflection_cost` attaches `MaxReflectionCostStopper` to that same callable (`gepa/api.py` lines 268 to 281; stop when `total_cost >= budget`, `gepa/utils/stop_condition.py` lines 176 to 190).
- **Do not** pass a bare custom callable without `total_cost` for production runs: `TrackingLM` estimates tokens but `total_cost` stays 0 and the cost stopper never fires (`gepa/lm.py` TrackingLM docstring).

Per-call logging:

```python
def make_reflection_lm_with_usage_log(
    model: str,
    *,
    usage_jsonl_path: Path,
    wandb_run: Any | None,
) -> LM:
    """Subclass or wrap gepa.lm.LM: after each __call__, append one JSON line:

    {call_idx, model, input_tokens, output_tokens, usd, cumulative_usd}
    where usd uses estimate_reflection_cost_usd on the *delta* tokens since last call.
    Log wandb.log({reflection/call_usd, reflection/cumulative_usd, reflection/input_tokens, ...}).
    Return the LM instance passed to gepa.optimize as reflection_lm= (string path: use wrapper
    by passing the returned LM object, not the string, so GEPA does not double-wrap).
    """
```

### `selection.py`

```python
def list_accepted_candidate_indices(result: GEPAResult, acceptance_log: Sequence[dict]) -> list[int]:
    """Indices where proposal was accepted (exclude seed 0 if never accepted)."""

def preselect_top_by_val_score(
    result: GEPAResult,
    accepted_indices: list[int],
    *,
    k: int = TOP_ACCEPTED_CANDIDATES,
) -> list[int]:
    """Sort by result.val_aggregate_scores[idx] descending; tie-break lower idx."""

def filter_top10_val_dev_gap(
    adapter: JevGepaRebuiltAdapter,
    candidate_indices: list[int],
    candidates: list[dict[str, str]],
    dev_a: list[JevDataInst],
    *,
    val_subsample_ids_by_idx: Mapping[int, list[int]] | None,
    val_dev_gap_max: float = VAL_DEV_GAP_MAX,
) -> list[int]:
    """For each idx in candidate_indices (expected len <= 10), score dev-A and val subsample at 0.5.

    Val side: 100-post subsample ids for that candidate (from accept-only policy history), or full 300 val ids if fully scored.
    Reject idx when val_balanced_acc - dev_a_balanced_acc > val_dev_gap_max.
    """

def select_on_dev_ab(
    adapter: JevGepaRebuiltAdapter,
    candidates: list[dict[str, str]],
    candidate_indices: list[int],
    dev_a: list[JevDataInst],
    dev_b: list[JevDataInst],
) -> tuple[int, float, float, float, list[dict]]:
    """For each idx in candidate_indices, score dev_a and dev_b once (posts count toward adapter only here).

    Pick threshold on dev_a maximizing F1 (shared tune_threshold_for_f1 grid).
    Return (selected_idx, threshold, dev_a_f1, dev_b_f1, per_candidate_rows for jsonl).
    """
```

`per_candidate_rows` fields: `candidate_idx`, `val_score`, `dev_a_f1`, `dev_b_f1`, `threshold`, `study_instruction_chars`, `accepted`, `last_reject_reason`.

### `optimize.py` post-run artifacts

Under `jev_gepa_rebuilt/outputs/<ablation_id>/`:

| File | Content |
|------|---------|
| `gepa_run/gepa_result.json` | `GEPAResult.to_dict()` |
| `gepa_run/reflection_usage.jsonl` | per reflection call |
| `gepa_run/acceptance_log.jsonl` | per proposal (accept/reject, guard or margin reason) |
| `gepa_run/stop_reason.json` | `{stop_reason, total_metric_calls, reflection_cost_usd, max_reflection_cost_usd}` |
| `dev_selection.json` | selected idx, threshold, dev_a_f1, dev_b_f1, top10 indices, reflection totals |
| `candidate_dev_scores.jsonl` | one row per top-10 candidate |

`stop_reason` enum strings: `max_metric_calls`, `max_reflection_cost`, `gepa.stop` (file stopper), `composite`, `unknown`. Detect via final `reflection_lm.total_cost`, `result.total_metric_calls`, and presence of `gepa_run/gepa.stop`.

Call `upload_rebuilt` on `outputs/<ablation_id>/` tree and `data/dev_ab_split.json` after write.

Wandb group remains `jev_gepa_rebuilt`; log `selection/dev_a_f1`, `selection/dev_b_f1`, `selection/threshold`, `reflection/total_usd`.

## Tests to write first

### `shared/tests/test_pricing_reflection.py`

Class `TestReflectionPricing`.

```text
given 1_000_000 input tokens on gpt-6-luna
when estimate_reflection_cost_usd
then usd == 0.10

given 1_000_000 output tokens on gpt-5.6-terra
when estimate_reflection_cost_usd
then usd == 12.0
```

### `tests/test_dev_ab_split.py`

Class `TestDevAbSplit`.

```text
given union dev rows in memory fixture with known labels
when build_or_load_dev_ab_split with seed GEPA_SEED and tmp path
then len(dev_a_ids) + len(dev_b_ids) == n_dev
and both splits preserve remove rate within 0.02
and re-running with same seed yields identical ids
```

### `tests/test_guards.py`

Class `TestGuards`.

```text
given candidate study_instruction length 4001
when check_candidate_guards
then ok is False and reason == length_cap

given train text containing UNIQUE40CHARSUBSTRINGXXXXXXXXXXXX
when candidate contains that substring
then reason == train_substring

```

### `tests/test_selection_top10.py`

Class `TestPreselectTop10`.

```text
given 15 accepted indices and monotonic val_aggregate_scores
when preselect_top_by_val_score k=10
then returns 10 indices with highest val scores
```

Class `TestFilterValDevGap`.

```text
given two candidates with val_balanced_acc 0.85 and 0.70 and dev_a_balanced_acc 0.60 and 0.65
when filter_top10_val_dev_gap with VAL_DEV_GAP_MAX 0.15
then first idx dropped (0.85 - 0.60 > 0.15) and second kept (0.70 - 0.65 <= 0.15)
```

Class `TestSelectOnDevAb`.

```text
given fake adapter returning fixed probabilities per candidate idx
when select_on_dev_ab with two candidates
then threshold is from dev_a only
and dev_b_f1 computed at that threshold
```

### `tests/test_reflection_logging.py`

Class `TestReflectionLmWrapper`.

```text
given LM.__call__ patched to increment total_tokens_in/out on fake completion
when make_reflection_lm_with_usage_log completes one call
then usage jsonl has one line with input_tokens > 0
and cumulative_usd >= 0
```

### `tests/test_run_optimize_selection_artifacts.py`

Class `TestOptimizeWritesSelectionArtifacts`.

```text
given run_optimize with gepa.optimize patched to return fixture GEPAResult and acceptance log
when smoke completes
then dev_selection.json exists under outputs/<ablation_id>/
and candidate_dev_scores.jsonl has at most 10 data lines
and stop_reason.json contains stop_reason key
```

## Implementation order

1. Pricing helpers and tests
2. `dev_ab.py` + split loader tests
3. `guards.py` + tests
4. `reflection_logging.py` + tests (use fake LM, no network)
5. `selection.py` + tests
6. Wire `run_optimize`: build dev split at start, reflection LM wrapper, guard composition, post-run `preselect_top_by_val_score` then `filter_top10_val_dev_gap` then `select_on_dev_ab`, and uploads

## Commands

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_pricing_reflection.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_dev_ab_split.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_guards.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_selection_top10.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_reflection_logging.py experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_run_optimize_selection_artifacts.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python -c "
from pathlib import Path
from gepa.lm import LM
import inspect
src = inspect.getsourcefile(LM)
assert src.endswith('gepa/lm.py')
print('gepa_lm_ok')
"
```

Expected stdout: `gepa_lm_ok`

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/ -q
```

Expected: exit 0 (Steps 1 to 3 plus Step 4).

## Must pass

- `data/dev_ab_split.json` written with seed `20260924` and uploaded under `rebuilt_s3_prefix()`.
- Top 10 selection by val score only among **accepted** candidates.
- Threshold tuned on dev-A; dev-B F1 recorded at same threshold.
- Guards enforce 4,000 char cap and 40+ char train substrings.
- Top-10 val-dev gap filter uses balanced accuracy at 0.5 and **VAL_DEV_GAP_MAX** (0.15).
- Reflection per-call log and cumulative USD; `max_reflection_cost` uses real `LM.total_cost`.
- Artifacts at `jev_gepa_rebuilt/outputs/<ablation_id>/` paths from Step 1.

## Must fail

- Scoring all accepted candidates on full 1,927-post dev during optimize (budget blowup).
- Using `TrackingLM`-only wrapper for production `max_reflection_cost` without USD accumulation.
- Selecting candidate by full-dev F1 at 0.5 only (Stage B regression).

## Commit message

`add dev ab split top10 selection guards and reflection usage logging`

## Done check

- All pytest commands above exit 0.
- A patched smoke `run_optimize` writes `dev_selection.json`, `candidate_dev_scores.jsonl`, `reflection_usage.jsonl`, `acceptance_log.jsonl`, and `stop_reason.json`.
- `upload_rebuilt` keys include `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/` and `data/dev_ab_split.json`.
