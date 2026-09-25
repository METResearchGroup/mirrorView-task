# Step 4: Port batched Jev scorer and run 100-post smoke per view

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` `main` with `--smoke --limit 100 --view {pair,original,mirror}` and `--add-criteria` for the A4 pair arm
- **Task:** Copy batching, rate limiting, retries, deadletter, resume, latency, and pricing from PR #23 (`experiments/speedup_jev_2026_09_23/`) into the design.md module names. Connect `typesafe-sdk` 0.7.1 client `system_one` calls per `/tmp/jev_probe/run_probe.py`. Unit-test with a fake client (no network). Run 100-post smoke per view (pair, original, mirror, plus pair with A4 addendum). Refresh token, latency, and cost rows in `estimates.md` from smoke outputs.
- **Out of scope:** Full Stage A on cohort A (Step 5), GEPA adapter (Step 6), `metrics.py`, `jev_baseline/run.py` production runner, editing `webapp/`.

## Dependencies

Steps 1 to 3 must provide `secrets.py`, `prompt.py`, `artifacts.py`, `wandb_tracking.py`, and frozen `cohort_a_splits.parquet` from Step 2 (smoke may sample from parquet when present; otherwise fail with a clear message to run Step 2).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Jev settings, outputs, pricing, concurrency |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` | Tables to refresh after smoke |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/steps/step3.md` | `render_state_text`, `build_questions`, Noul pattern |
| `METResearchGroup/mind_technology_lab_experiments` PR #23 @ `bae88e2d50550d0803578e53a049b54fc68b591b` | `models/batched_jev.py`, `shared/batch_runner.py`, `shared/rate_limiter.py`, `shared/timer.py`, `shared/pricing.py`, `shared/records.py` |
| `/tmp/jev_probe/run_probe.py` | Working `TypeSafeClient` call, `RetryPolicy(max_retries=0)`, secret `jev-typesafe-api-key`, model `jev-1.13.0` |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/secrets.py` | `get_jev_api_key` from Step 1 |

PR #23 path mapping for this experiment:

| PR #23 module | This experiment module |
|---------------|------------------------|
| `shared/timer.py` `timed` | `shared/latency.py` `timed` |
| `shared/rate_limiter.py` | `shared/rate_limiter.py` (same name) |
| `shared/pricing.py` | `shared/pricing.py` (same constants) |
| `models/batched_jev.py` + `shared/batch_runner.py` retry loop | `shared/jev_scorer.py` + `shared/retries.py` |
| `shared/records.py` models | pydantic models inside `jev_scorer.py` |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/rate_limiter.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/retries.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/latency.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/pricing.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_rate_limiter.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_retries.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_pricing.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_jev_scorer.py` (new)
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` (refresh per-view probe table and Stage A notes from smoke)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/README.md`
- `/workspace/webapp/**`
- `/workspace/shared/data/registry.py`
- `/workspace/pyproject.toml` (deps added in Step 1)
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/plan.md`
- `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md`

## Contracts

Pinned scorer settings (module-level in `jev_scorer.py` unless noted):

- `JEV_MODEL_ID = "jev-1.13.0"`
- `BATCH_SIZE = 10`
- `WORKER_THREADS = 8`
- `MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT = 1000`
- `MAX_EXTRA_ATTEMPTS = 3`
- `BACKOFF_SECONDS = (1.0, 2.0, 4.0)`
- `REQUEST_TIMEOUT_SECONDS = 120.0`
- `SMOKE_SEED = 20260924`
- `SMOKE_LIMIT_DEFAULT = 100`
- Output filenames: `predictions.jsonl`, `requests.jsonl`, `deadletter.jsonl`, `smoke_summary.json`

### `rate_limiter.py`

Port `RequestStartLimiter` from PR #23 unchanged:

```python
WINDOW_SECONDS = 60.0

class RequestStartLimiter:
    def __init__(self, max_starts_per_minute: int) -> None: ...
    def wait(self) -> None: ...
```

### `latency.py`

Port `timed` decorator from PR #23 `shared/timer.py`:

```python
def timed(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """Return (result, latency_ms). Re-raise exceptions unchanged."""
```

Also export:

```python
def percentile_ms(latencies: list[float], q: float) -> float:
    """Return q in [0,1] percentile with linear interpolation. Empty list returns 0.0."""
```

### `pricing.py`

Port from PR #23:

```python
JEV_USD_PER_MILLION_INPUT_TOKENS = 0.042
JEV_USD_PER_MILLION_OUTPUT_TOKENS = 0.0

def estimate_jev_cost_usd(input_tokens: int, output_tokens: int) -> float: ...
```

### `retries.py`

```python
AUTH_ERROR_TYPES = (TypeSafeAuthenticationError, TypeSafePermissionDeniedError)

def run_with_retries(
    fn: Callable[[], T],
    *,
    max_extra_attempts: int = MAX_EXTRA_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = BACKOFF_SECONDS,
) -> T:
    """Call fn up to 1 + max_extra_attempts times. Auth errors propagate immediately. Other exceptions sleep 1/2/4 s."""
```

### `jev_scorer.py`

Pydantic models:

```python
class PostTask(BaseModel):
    post_id: str
    state_text: str
    gold_label: int

class BatchResult(BaseModel):
    probabilities: list[float]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model_version: str

class PostPrediction(BaseModel):
    post_id: str
    view: str
    gold_label: int
    probability_remove: float
    batch_size: int
    request_index: int
    position_in_request: int
    n_posts_in_request: int
    request_latency_ms: float
    per_post_latency_ms: float  # request_latency_ms / n_posts_in_request
    request_input_tokens: int
    request_output_tokens: int
    per_post_input_tokens: float
    per_post_output_tokens: float
    estimated_cost_usd: float
    model_version: str
    attempts: int

class SmokeSummary(BaseModel):
    view: str
    add_criteria: bool
    n_posts: int
    n_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    latency_ms_p50: float
    latency_ms_p90: float
    latency_ms_p99: float
    per_post_latency_ms_p50: float
    per_post_latency_ms_p90: float
    per_post_latency_ms_p99: float
```

Core functions:

```python
def build_client(api_key: str) -> TypeSafeClient:
    """RetryPolicy(max_retries=0), timeout REQUEST_TIMEOUT_SECONDS, model JEV_MODEL_ID."""

def score_batch(
    client: TypeSafeClient,
    state_texts: list[str],
    view: str,
    *,
    instruction: str | None = None,
) -> BatchResult:
    """state={posts: state_texts}.
    When instruction is None, questions=prompt.build_questions(len(state_texts), view) (seed path).
    When instruction is set, each post_i Noul uses the same per-index prefix as build_noul_instruction
    (Consider `posts[i]`. ...) followed by instruction as the task text for every post in the batch.
    Use latency.timed around client.system_one. Read answer.noul as P(remove)."""

def make_batches(tasks: list[PostTask], batch_size: int = BATCH_SIZE) -> list[list[PostTask]]: ...

def seen_post_ids(predictions_path: Path) -> set[str]:
    """Resume: read post_id from predictions.jsonl."""

def run_scoring_pass(
    tasks: list[PostTask],
    output_dir: Path,
    *,
    view: str,
    api_key: str,
    max_starts_per_minute: int = MAX_REQUEST_STARTS_PER_MINUTE_DEFAULT,
    instruction: str | None = None,
    ablation_id: str = "",
) -> SmokeSummary:
    """ThreadPoolExecutor max_workers=WORKER_THREADS, per-thread clients, RequestStartLimiter,
    run_with_retries per batch, skip tasks whose post_id is already in predictions.jsonl,
    pass instruction through to score_batch for every batch,
    write predictions.jsonl and requests.jsonl in request_index order,
    write deadletter.jsonl on exhausted retries, return SmokeSummary."""
```

CLI:

```python
def main(argv: list[str] | None = None) -> None:
    """Args: --smoke --limit 100 --view pair|original|mirror [--add-criteria] [--rate-cap 1000] [--output-dir PATH].
    Sample post_ids with numpy RNG seed SMOKE_SEED from cohort_a_splits.parquet.
    Build state_text via render_state_text. On smoke completion write smoke_summary.json and print summary line."""
```

Auth fail-fast: `TypeSafeAuthenticationError` and `TypeSafePermissionDeniedError` cancel pending futures and re-raise (same as PR #23 `batch_runner.py`).

Per-post latency: `per_post_latency_ms = request_latency_ms / n_posts_in_request` for every post in the batch.

Per-post tokens: `request_input_tokens / n_posts_in_request` (and same for output).

### `requests.jsonl` record schema

One JSON object per line, written in `request_index` order. Field names match `requests.parquet` columns below.

| Field | Type | Meaning |
|-------|------|---------|
| `request_id` | str | Stable id `{ablation_id or view}:{batch_index}:{attempt}` |
| `ablation_id` | str | Stage A ablation id when set; empty string for smoke |
| `batch_index` | int | 0-based request index in the pass |
| `post_ids` | list[str] | Post ids in this batch |
| `n_posts` | int | `len(post_ids)` |
| `attempt` | int | 1 on first try; increments on retry |
| `status` | str | `ok` or `error` |
| `error_type` | str or null | Exception class name on error; null on success |
| `started_at_utc` | str | ISO 8601 UTC timestamp at request start |
| `latency_ms` | float | Wall time for the attempt |
| `latency_per_post_ms` | float | `latency_ms / n_posts` |
| `input_tokens` | int | From SDK usage |
| `output_tokens` | int | From SDK usage |
| `estimated_cost_usd` | float | `pricing.estimate_jev_cost_usd(input_tokens, output_tokens)` |
| `model` | str | `JEV_MODEL_ID` |
| `instruction_sha256` | str | SHA-256 hex of the effective task instruction text passed to `score_batch` (seed or override) |

### `requests.parquet` schema

Finalized table of `requests.jsonl` with the same columns:

| Column | Type | Meaning |
|--------|------|---------|
| `request_id` | str | Stable request id |
| `ablation_id` | str | Ablation id or empty for smoke |
| `batch_index` | int | 0-based request index |
| `post_ids` | list[str] | Post ids in batch |
| `n_posts` | int | Batch size for this request |
| `attempt` | int | Attempt number |
| `status` | str | `ok` or `error` |
| `error_type` | str or null | Error class name or null |
| `started_at_utc` | str | ISO 8601 UTC |
| `latency_ms` | float | Request latency |
| `latency_per_post_ms` | float | `latency_ms / n_posts` |
| `input_tokens` | int | Input tokens |
| `output_tokens` | int | Output tokens |
| `estimated_cost_usd` | float | Estimated USD |
| `model` | str | Model id |
| `instruction_sha256` | str | SHA-256 of effective instruction |

Step 5 `finalize_ablation` materializes this parquet from `requests.jsonl`. GEPA evaluate passes (Step 7) write the same schema under their output dirs.

## Tests to write first

Use a `FakeTypeSafeClient` in `tests/conftest.py` that records `system_one` calls and returns configurable `answers` and `usage` without network.

### `tests/test_rate_limiter.py`

Class `TestRequestStartLimiter`.

```text
given max_starts_per_minute=2
when wait is called 3 times with monotonic time patched
then the third call sleeps until the oldest start exits the 60 s window
```

### `tests/test_retries.py`

Class `TestRunWithRetries`.

```text
given fn raises ValueError twice then returns 7
when run_with_retries with max_extra_attempts 3
then return 7 and fn call count is 3

given fn raises TypeSafeAuthenticationError on first call
when run_with_retries
then propagate without sleep and call count is 1
```

### `tests/test_pricing.py`

Class `TestEstimateJevCostUsd`.

```text
given input_tokens 1_000_000 output_tokens 0
when estimate_jev_cost_usd
then return 0.042

given input_tokens 0 output_tokens 1_000_000
when estimate_jev_cost_usd
then return 0.0
```

### `tests/test_jev_scorer.py`

Class `TestScoreBatch`.

```text
given fake client returning noul 0.7 for post_0 and 0.3 for post_1
when score_batch with two state texts and view pair
then probabilities are [0.7, 0.3]
and input_tokens match fake usage

given fake client and custom instruction OPTIMIZED_PROMPT
when score_batch with two state texts, view pair, and instruction=OPTIMIZED_PROMPT
then post_0 Noul instructions start with Consider `posts[0]`.
and post_0 Noul instructions contain OPTIMIZED_PROMPT
and post_1 Noul instructions start with Consider `posts[1]`.
and post_1 Noul instructions contain OPTIMIZED_PROMPT
and probabilities still match fake client answers

given tasks with post_ids A B C and existing predictions.jsonl containing A
when run_scoring_pass
then only B and C are scored
and predictions.jsonl has three lines after pass when A was pre-seeded

given a batch of 10 tasks and fake client
when run_scoring_pass completes
then each PostPrediction has per_post_latency_ms == request_latency_ms / 10
and per_post_input_tokens == request_input_tokens / 10

given fake client raises generic Exception four times for one batch
when run_scoring_pass
then one deadletter.jsonl record exists for that batch
```

## Implementation order

Follow `/implement-from-spec`. Full auto. One commit per unit of work.

1. `latency.py`, `pricing.py`, `rate_limiter.py`, `retries.py` scaffold
2. `jev_scorer.py` scaffold with models and `main` argparse
3. pytest files (failing)
4. `pricing.py` until `test_pricing.py` is green
5. `rate_limiter.py` until `test_rate_limiter.py` is green
6. `retries.py` until `test_retries.py` is green
7. `score_batch` and `build_client` until `TestScoreBatch` first scenario is green
8. `run_scoring_pass` resume, ordering, deadletter, per-post fields until remaining `test_jev_scorer.py` is green
9. `main` smoke wiring

## Commands

Unit tests:

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q
```

Expected: exit 0.

100-post smoke (run after Step 2 parquet exists):

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

OUT=experiments/predict_keep_remove_jev_gepa_2026_09_23/outputs/smoke
mkdir -p "$OUT"

for VIEW in pair original mirror; do
  PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py \
    --smoke --limit 100 --view "$VIEW" \
    --output-dir "$OUT/$VIEW"
done

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py \
  --smoke --limit 100 --view pair --add-criteria \
  --output-dir "$OUT/pair_addendum"
```

Expected for each run:

- Exit 0.
- `outputs/smoke/<view>/smoke_summary.json` exists with `n_posts=100`.
- Stdout line matches `smoke view=<view> add_criteria=<true|false> n_requests=10 total_cost_usd=<float> p50_ms=<float>`.
- `predictions.jsonl` has 100 lines (or appends to 100 on rerun after resume test).
- `deadletter.jsonl` is empty or absent on success.
- Probabilities are finite floats in `[0, 1]`.

Re-run one view to confirm resume:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py \
  --smoke --limit 100 --view pair --output-dir "$OUT/pair"
```

Expected: prints `n_new_requests=0` or scores zero additional requests; does not duplicate `post_id` lines in `predictions.jsonl`.

Refresh estimates (copy measured medians into the table):

| View | Input tok / post (smoke) | Latency p50 ms / request | Cost / 1k posts |
|------|--------------------------|--------------------------|-----------------|
| pair | from `smoke_summary.json` | from `smoke_summary.json` | computed |
| original | from smoke | from smoke | computed |
| mirror | from smoke | from smoke | computed |
| pair + addendum | from `pair_addendum/smoke_summary.json` | from smoke | computed |

Update `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/estimates.md` section `## Per-view probe (batch 10)` with measured values and date `2026-09-24` smoke run. Adjust Stage A total input token estimate for A4 if addendum tokens differ from the ~250/post assumption by more than 10%.

## Must pass

- Fake-client unit tests exit 0 without network.
- Live smoke scores 100 posts per view with batch size 10 (10 requests per view).
- Rate limiter default is 1,000 starts per minute; `--rate-cap 200` is accepted for later GEPA runs.
- Eight worker threads; per-thread `TypeSafeClient` instances.
- SDK retries disabled; experiment retries 3 extra with 1/2/4 s backoff.
- Auth errors fail fast without deadletter retry loops.
- Resume skips `post_id` values already in `predictions.jsonl`.
- `per_post_latency_ms` equals request latency divided by batch size.
- `score_batch` and `run_scoring_pass` accept optional `instruction`; override uses the same per-index Consider `posts[i]`. prefix as the seed path.
- `requests.jsonl` records use the column names in the Contracts table; `instruction_sha256` is populated for every request.
- `estimates.md` probe table updated from smoke outputs.
- `PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q` exits 0 after all modules land.

## Must fail

- Using `RetryPolicy` with `max_retries > 0` on the SDK client.
- Scoring without `build_questions` from `prompt.py` when `instruction` is None.
- Bypassing the `instruction` parameter with ad hoc `system_one` question builders outside `score_batch`.
- Treating `answer.noul` as P(keep) (must be P(remove)).
- Writing predictions out of `request_index` order.
- Continuing after `TypeSafeAuthenticationError`.
- Running smoke without resolving Jev API key.
- Duplicating `post_id` rows on resume.
- Leaving `estimates.md` unchanged after successful smoke.

## Commit messages

1. `add Jev rate limiter latency and pricing helpers`
2. `add Jev retry helper with auth fail-fast`
3. `add batched Jev scorer with resume and deadletter`
4. `add Jev scorer unit tests with fake client`
5. `run 100-post Jev smoke per view and refresh estimates`

## Implement-from-spec notes

Phase 1 names `jev_scorer.py` `main --smoke` as the caller. Phase 6 completes when unit tests and all four smoke runs succeed and `estimates.md` reflects measured smoke values.
