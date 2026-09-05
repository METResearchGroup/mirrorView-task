# Step 2: Smoke-test 50 synthetic posts through OpenAI Batch

## Goal

Prove the new LLM toxicity classifier on 50 synthetic posts in one OpenAI Batch job. Build the posts with Faker, inject toxic language into a random subset, report elapsed time, estimated dollar cost, and the low/medium/high counts in `RESULTS.md`.

## Caller / unit of work

**Main caller:** `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py` `main()`.

**Slice:** build 50 posts → inject toxicity into a subset → submit one OpenAI Batch via `build_openai_engine` → write metrics, labels, and `RESULTS.md`.

**Out of scope:** changing the OpenAI Batch engine; changing `smoke_openai_engine.py`; replacing Perspective in production; curation; unit tests for experiment code (see UNIT_TESTING_STANDARDS: do not write pytest for `experiments/`).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | `build_openai_engine`, `batch_label_records`, `last_batch.usage` |
| `/workspace/data_platform/generate_features/smoke_openai_engine.py` | Smoke metrics shape and `build_openai_engine` + `batch_label_records` call site |
| `/workspace/experiments/openai_batch_parallelization_2026_09_05/run_experiment.py` | Batch token cost formula (`estimated_cost_usd`) |
| `/workspace/data_platform/generate_features/OPENAI_BATCH_SMOKE_RESULTS.md` | How prior Batch smokes report elapsed time, tokens, and USD |
| `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` | Prompt and schemas from Step 1 |
| `/workspace/data_platform/generate_features/registry.py` | Confirm the feature exists after Step 1 |

## Files allowed to change

- `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py` (create)
- `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/synthetic_posts.py` (create)
- `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/README.md` (create)
- `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/RESULTS.md` (create after the live run)
- `/workspace/experiments/llm_based_toxicity_classifier_2026_09_05/outputs/` (labels JSON, metrics JSON, synthetic CSV written by the live run)
- `/workspace/pyproject.toml` (add `faker`)
- `/workspace/uv.lock` (lockfile after adding `faker`)

Do not edit the plan package during implementation.

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/openai_engine.py`
- `/workspace/data_platform/generate_features/smoke_openai_engine.py`
- `/workspace/data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `/workspace/data_platform/curate/**`
- `/workspace/experiments/openai_batch_parallelization_2026_09_05/**`

## Contracts to lock

Constants (defined at the experiment caller, passed in; no function defaults):

```text
SMOKE_POST_COUNT = 50
INJECTED_TOXIC_COUNT = 15
RANDOM_SEED = 42
INPUT_PRICE_PER_MILLION_TOKENS_USD = 0.20
OUTPUT_PRICE_PER_MILLION_TOKENS_USD = 1.25
TOKENS_PER_MILLION = 1_000_000
```

Use the same GPT-5.4 nano Batch rates as `/workspace/experiments/openai_batch_parallelization_2026_09_05/run_experiment.py`. Do not import from that experiment.

```text
class SyntheticPost(BaseModel):
    source_record_id: str
    text: str
    toxicity_was_injected: bool
    injected_tier: Literal["medium", "high"] | None

def build_synthetic_posts(
    post_count: int,
    injected_toxic_count: int,
    seed: int,
) -> list[SyntheticPost]
  Faker posts (short social-media-like sentences).
  Inject toxic language into exactly injected_toxic_count posts, chosen with random.Random(seed).
  Injected posts split between medium-phrase and high-phrase lists (named constants).
  Remaining posts stay non-toxic Faker text.
  Raise ValueError if injected_toxic_count > post_count or injected_toxic_count < 0.

def openai_toxicity_spec() -> FeatureSpec
  name="llm_toxicity_tiered"
  model=LlmToxicityTieredModel
  engine_type="openai"
  system_prompt and llm_output_schema from the Step 1 module
  generate_fn unset

def run_toxicity_smoke(posts: list[SyntheticPost]) -> SmokeRunResult
  tasks = [LabelTask(uri=post.source_record_id, text=post.text) for post in posts]
  engine = build_openai_engine(openai_toxicity_spec(), FeatureRunConfig())
  one call: engine.batch_label_records(tasks)
  elapsed from time.perf_counter around that single call
  usage from engine.last_batch.usage (required; raise if missing)
  estimated_cost_usd from input/output tokens and the constants above
  label_counts = Counter of toxicity_tier over returned rows
```

The OpenAI spec is constructed in the experiment. Do not change the production registry `engine_type` in this step.

`run_smoke.py` is the CLI:

```bash
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

It must:

1. Build exactly 50 posts with seed 42 and 15 injected.
2. Write `experiments/llm_based_toxicity_classifier_2026_09_05/outputs/synthetic_posts.csv`.
3. Submit **one** OpenAI Batch (do not call `label_records`, which can split by `batch_size`).
4. Write `experiments/llm_based_toxicity_classifier_2026_09_05/outputs/labels.json` and `outputs/metrics.json`.
5. Write `experiments/llm_based_toxicity_classifier_2026_09_05/RESULTS.md`.

`RESULTS.md` must include:

- Command used
- Model id (`gpt-5.4-nano` / `DEFAULT_LLM_MODEL`)
- Post count 50, injected count 15, seed 42
- Elapsed seconds
- Input tokens, output tokens, total tokens
- Estimated cost USD
- Counts and percents for `low`, `medium`, and `high`
- Path to the output files

Do not claim classification accuracy. The injected phrases are a smoke signal, not a labeled gold set. Optionally note how many injected posts landed in each predicted tier, without calling it accuracy.

Add `faker` to `[project] dependencies` in `/workspace/pyproject.toml` with `uv add faker`. Do not add it only to the `dev` group.

## Test design

No pytest for this experiment folder. UNIT_TESTING_STANDARDS: do not write unit tests for experimental code.

Verification is the live command in Must pass.

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit. Full auto.

Because this slice is experiment code, Phase 4 does not add pytest. Scaffold and contracts still apply.

1. Phase 1 scope. Confirm caller and out-of-scope.
2. Phase 2 scaffold. Create the experiment modules with stub functions (`raise NotImplementedError`). Add `faker` in the same scaffold commit if imports otherwise fail. README can list the run command.
3. Phase 3 contracts. Lock the signatures above. Bodies stay stubs.
4. Phase 4. Skip pytest. Record the given/when/then live scenario in a short comment at the top of `run_smoke.py` if helpful. No test file.
5. Phase 5 units, in this order, one commit each:
   1. `build_synthetic_posts`
   2. `openai_toxicity_spec` + `run_toxicity_smoke` (engine call, metrics, cost)
   3. CLI `main` that writes CSV, JSON, and RESULTS.md
6. Phase 6. Run the live smoke command. Commit `RESULTS.md` and output artifacts in a separate commit after the run.

Live scenario:

```text
given OPENAI_API_KEY is set
and faker can build 50 posts with 15 injected
when PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
then one OpenAI Batch job labels 50 posts
and RESULTS.md contains elapsed seconds, estimated USD, and low/medium/high counts that sum to 50
```

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run python experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py
```

Expected: exit 0. Prints progress. Writes:

- `experiments/llm_based_toxicity_classifier_2026_09_05/outputs/synthetic_posts.csv` (50 rows)
- `experiments/llm_based_toxicity_classifier_2026_09_05/outputs/labels.json` (50 labels)
- `experiments/llm_based_toxicity_classifier_2026_09_05/outputs/metrics.json`
- `experiments/llm_based_toxicity_classifier_2026_09_05/RESULTS.md` with elapsed seconds, estimated cost, and label counts summing to 50

Also keep Step 1 tests green:

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/generate_features -q
```

Expected: exit 0.

## Must fail / not happen

- Calling `label_records` (would split batches).
- More than one OpenAI Batch create for the 50 posts.
- Importing cost helpers from `experiments/openai_batch_parallelization_2026_09_05/`.
- Changing production `FEATURE_REGISTRY` engine type in this step.
- Pytest files under the experiment folder.
- Using a study CSV instead of Faker.
