# Step 1: Add the root Jev module

## Goal

Create `shared/models/jev/`, a reusable Jev package that does not depend on any task. Given any LangChain TypeSafe `ClassifierRequest`, it calls Jev once with rate limiting and retries for transient errors. It returns one validated `JevResult` that holds every requested Noul probability, keyed by question ID. Also pin the `langchain-typesafe` dependency in the project.

All paths in this step are relative to the repository root. Run every command from the repository root.

## Scope

- **Main caller:** `shared/models/jev/scorer.py::build_jev_scorer`, then `JevScorer.score`.
- **Main task:** build a classifier pinned to `jev-1.13.0`, wait on the request-start limiter, run the classifier once, check the response model and requested answers, and return a `JevResult`.
- **Unit of work:** one Jev request in, one `JevResult` out.
- **Out of scope:** keep or remove prompts, Study 2 data, S3, issue 326 schemas, thread pools, batching, live Jev calls, and changes to `experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

## Hard rule

No file under `shared/models/` may import from `experiments/`. Phase 4 checks the rule with `grep`.

## Exact file tree

```text
shared/
  models/
    __init__.py
    jev/
      __init__.py
      constants.py
      schemas.py
      client.py
      rate_limit.py
      scorer.py
pyproject.toml
uv.lock
```

## Files to inspect

- `docs/plans/2026-10-01_study_2_zero_shot_jev_inference_41eb9f/plan.md`
- `docs/plans/2026-10-01_study_2_zero_shot_jev_inference_41eb9f/proposal.md` (sections "Schema models" and "Jev code" hold the approved source for every file in this step)
- `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/jev.py` (`RequestStartLimiter` source)
- `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/secrets.py` (`get_jev_api_key` and `parse_secret_string` behavior)
- `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` (Jev constants)
- `shared/data/dataloader.py` (`_use_lab_credentials_when_unset`)
- The installed `langchain_typesafe` package: `classifier.py`, `client.py`, `types.py`

## Files allowed to change

- `shared/models/__init__.py`
- `shared/models/jev/__init__.py`
- `shared/models/jev/constants.py`
- `shared/models/jev/schemas.py`
- `shared/models/jev/client.py`
- `shared/models/jev/rate_limit.py`
- `shared/models/jev/scorer.py`
- `pyproject.toml`
- `uv.lock`

## Files forbidden to change

- `shared/data/**`
- Every other path under `shared/` outside `shared/models/`
- `data_platform/**`
- `experiments/**`

## Confirmed contracts

### Dependency

Add exactly `"langchain-typesafe==0.0.1a3"` to `[project].dependencies` in `pyproject.toml` with `uv add`. Resolving this pin also upgrades the following existing lock entries, and the upgrade is expected:

| Package | Before | After |
| --- | --- | --- |
| `langchain-core` | 1.4.6 | 1.6.6 |
| `langchain-protocol` | 0.0.15 | 0.0.19 |
| `idna` | 3.13 | 3.20 |

The lock also gains `langchain-typesafe`, `httpx2`, `httpcore2`, `httpx2-jsfetch`, and `truststore`. No other locked version may change.

### Constants

`shared/models/jev/constants.py` defines exactly these values:

| Name | Value |
| --- | --- |
| `JEV_MODEL_ID` | `"jev-1.13.0"` |
| `JEV_SECRET_ID` | `"jev-typesafe-api-key"` |
| `JEV_SECRETS_REGION` | `"us-east-2"` |
| `JEV_REQUEST_TIMEOUT_SECONDS` | `120.0` |
| `JEV_RETRY_BACKOFF_SECONDS` | `(1.0, 2.0, 4.0)` |
| `JEV_MAX_REQUESTS_PER_MINUTE` | `1000` |
| `JEV_USD_PER_MILLION_INPUT` | `0.042` |
| `JEV_USD_PER_MILLION_OUTPUT` | `0.0` |

### `JevResult`

`JevResult` is a strict, immutable Pydantic model (`frozen=True`) that rejects extra fields. It has these fields and methods:

- `model: str`, nonempty
- `request_id: str | None`
- `nouls: dict[str, float]`, nonempty, with each value in the closed interval from 0 through 1
- `input_tokens: int` and `output_tokens: int`, both 0 or greater
- `latency_ms: float`, 0 or greater
- `attempts: int`, 1 or greater
- `noul(question_id) -> float` raises `KeyError` for an unknown ID
- `total_tokens` property equals `input_tokens + output_tokens`

The proposal's `JevResult` does not bound each `nouls` value, so add the bound in this step with `dict[str, Annotated[float, Field(ge=0.0, le=1.0)]]`.

### Client

- `get_jev_api_key()` returns the stripped `TYPESAFE_API_KEY` value when that variable is nonempty. Otherwise it calls `_use_lab_credentials_when_unset()`, reads `JEV_SECRET_ID` from Secrets Manager in `JEV_SECRETS_REGION`, and returns the secret. A plain-text secret is returned stripped. A JSON secret is searched in key order `api_key`, `TYPESAFE_API_KEY`, `key`. An empty secret, or a JSON secret with none of those keys, raises `ValueError`. The function never logs or prints the key.
- `build_jev_classifier(model_id=JEV_MODEL_ID, api_key=None, timeout=JEV_REQUEST_TIMEOUT_SECONDS)` returns a `TypeSafeClassifier`. It calls `get_jev_api_key()` only when `api_key` is `None`.

### Scorer

- `parse_response(request, response, expected_model, latency_ms, attempts)` raises `ValueError` when `response.model != expected_model`. It raises `KeyError` naming every requested `Noul` question ID that has no answer. It maps a `None` token count to `0`.
- `JevScorer(classifier, limiter, clock, sleep_fn, backoff_seconds=JEV_RETRY_BACKOFF_SECONDS)` makes at most `1 + len(backoff_seconds)` attempts and calls `limiter.wait()` before each one. Only these errors are retried: `TypeSafeRateLimitError`, `TypeSafeInternalServerError`, `TypeSafeAPIConnectionError`, and `TypeSafeAPITimeoutError`. The delay before attempt `n + 1` is `backoff_seconds[n - 1]`, or the error's `retry_after_ms / 1000` when that is larger. Every other exception, including those from `parse_response`, is raised at once. `expected_model` is the classifier's own `model`.
- `build_jev_scorer(model_id=JEV_MODEL_ID)` wires the live classifier, a `RequestStartLimiter(JEV_MAX_REQUESTS_PER_MINUTE, time.monotonic, time.sleep)`, `time.perf_counter`, and `time.sleep`.
- `shared/models/jev/rate_limit.py` holds `RequestStartLimiter`, copied byte for byte from `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/jev.py`. Do not edit the Study 2 copy.
- `shared/models/jev/__init__.py` re-exports `JEV_MODEL_ID`, `JevResult`, `JevScorer`, `RequestStartLimiter`, `build_jev_classifier`, `build_jev_scorer`, `get_jev_api_key`, and `parse_response`.

## Caller-first implementation phases

### Phase 0: Confirm scope

Name `build_jev_scorer` and `JevScorer.score` as the only callers. Confirm the file tree and the out-of-scope list above.

The phase passes when there is one caller path, only the listed files exist, and no file imports from `experiments/`.

### Phase 1: Add the dependency and scaffold

```bash
uv add "langchain-typesafe==0.0.1a3"
grep -n '"langchain-typesafe==0.0.1a3"' pyproject.toml
PYTHONPATH=. uv run python -c "import langchain_typesafe, langchain_aws, langchain_openai; print(langchain_typesafe.__version__)"
```

In the expected output, `uv add` exits 0, `grep` prints one dependency line, and the final command prints `0.0.1a3`.

Create every file in the tree with working imports and typed signatures. Function and method bodies are `...` or raise `NotImplementedError`, and constants hold their final values.

```bash
PYTHONPATH=. uv run python -c "from shared.models.jev import JEV_MODEL_ID, JevResult, JevScorer, RequestStartLimiter, build_jev_classifier, build_jev_scorer, get_jev_api_key, parse_response; print('jev-imports-ok', JEV_MODEL_ID)"
```

Expected output:

```text
jev-imports-ok jev-1.13.0
```

Commit `pyproject.toml` and `uv.lock` first, then the scaffold, as two separate commits.

### Phase 2: Confirm contracts

Fill in the `JevResult` fields and validators, the public signatures, the docstrings, and the retryable error tuple. Keep `get_jev_api_key`, `parse_response`, `JevScorer.score`, and `_retry_delay` stubbed. Commit.

The phase passes when the signatures and field rules match the "Confirmed contracts" section. Stop for plan review before Phase 3 unless the reviewer has approved this step file without revisions.

### Phase 3: Implement one unit at a time

Implement in this order, committing each unit separately:

1. `JevResult` validation and `noul` and `total_tokens`
2. `RequestStartLimiter`
3. `get_jev_api_key`
4. `build_jev_classifier`
5. `parse_response`
6. `JevScorer.score` and `_retry_delay`
7. `build_jev_scorer`

After each unit, rerun the Phase 1 import check. Step 1 adds no test files and no mock checks. Step 4's smoke run is the first check of live Jev behavior.

### Phase 4: Verify

```bash
grep -rn "experiments" shared/models/ --include='*.py'
git diff --stat origin/main -- experiments shared/data data_platform
```

In the expected output, `grep` prints nothing and exits 1, and `git diff` prints nothing.

## Pass

- The Phase 1 import check passes.
- No test files are added.
- `pyproject.toml` contains `langchain-typesafe==0.0.1a3`, and only the lock changes listed above appear.
- Existing `langchain_aws` and `langchain_openai` imports still work after the `langchain-core` upgrade.
- `shared/models/` imports nothing from `experiments/`.

## Fail

- A test file or test directory is added.
- A non-retryable error is retried, or a retryable error is retried more than three times.
- A probability outside 0 to 1 passes validation.
- The lock changes any version other than the ones listed above.
- Any forbidden file changes.
