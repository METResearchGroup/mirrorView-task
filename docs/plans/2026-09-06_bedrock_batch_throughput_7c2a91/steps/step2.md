# Step 2: Add a Bedrock Converse engine and a 100-post smoke

Add a Bedrock engine that labels a list of posts through Nova Micro Converse, then smoke-test 100 `flips.csv` posts with the news-or-opinion prompt.

## Caller / unit of work

**Main caller:** `/workspace/data_platform/generate_features/smoke_bedrock_engine.py` `main()`.

**Slice:** load 100 posts → `build_bedrock_engine` → `batch_label_records` → print metrics JSON with tokens, throughput, and estimated on-demand dollars.

**Out of scope:** changing the OpenAI engine, changing the production feature registry `engine_type`, IAM roles, native `CreateModelInvocationJob`, Steps 4 and 5 live runs, pytest under `experiments/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | Engine shape to copy |
| `/workspace/data_platform/generate_features/smoke_openai_engine.py` | Smoke metrics, `load_smoke_label_tasks`, news-or-opinion spec |
| `/workspace/data_platform/generate_features/engines/base.py` | `BaseBatchExecutionEngine.batch_label_records` |
| `/workspace/data_platform/generate_features/engines/__init__.py` | `ENGINE_BUILDERS` |
| `/workspace/data_platform/generate_features/models.py` | `EngineType` |
| `/workspace/tests/data_platform/generate_features/test_openai_engine.py` | Test shape |
| `/workspace/tests/data_platform/generate_features/conftest.py` | Shared spec helpers |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per public function. Arrange, act, assert. `result` and `expected`. No pytest for `experiments/`. |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/CODING_RULES.md` | Named constants. Constructor injection. Small functions. |

## Files allowed to change

- `/workspace/lib/constants.py` (`DEFAULT_BEDROCK_NOVA_MICRO` if Step 1 did not add it)
- `/workspace/data_platform/generate_features/models.py` (`EngineType` adds `"bedrock"`)
- `/workspace/data_platform/generate_features/engines/bedrock_engine.py` (create)
- `/workspace/data_platform/generate_features/engines/__init__.py` (register `"bedrock"`)
- `/workspace/data_platform/generate_features/smoke_bedrock_engine.py` (create)
- `/workspace/data_platform/generate_features/metadata.py` (`model_id_for_spec` returns Nova Micro for `engine_type="bedrock"`)
- `/workspace/tests/data_platform/generate_features/test_bedrock_engine.py` (create)
- `/workspace/tests/data_platform/generate_features/test_smoke_bedrock_engine.py` (create)
- `/workspace/tests/data_platform/generate_features/test_metadata.py` (one assertion for bedrock model id)
- `/workspace/tests/data_platform/generate_features/conftest.py` (bedrock spec helper only if needed)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/SMOKE_RESULTS.md` (create after the live smoke)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/smoke_metrics.json` (create after the live smoke)

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/openai_engine.py`
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/generate_features/smoke_openai_engine.py`
- `/workspace/experiments/openai_batch_parallelization_2026_09_05/**`

## Contracts to lock

```text
DEFAULT_BEDROCK_NOVA_MICRO = "us.amazon.nova-micro-v1:0"
BEDROCK_REGION = "us-east-2"
BEDROCK_MAX_TOKENS = 32
BEDROCK_TEMPERATURE = 0.0
BEDROCK_JSON_INSTRUCTION = (
    "Reply with a single JSON object only. "
    "The object must have one string field named category "
    "whose value is news, opinion, or neither."
)
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
TOKENS_PER_MILLION = 1_000_000
SMOKE_POST_COUNT = 100
SMOKE_MAX_CONCURRENCY = 8
ID_COLUMN = "post_primary_key"
TEXT_COLUMN = "original_text"
SOURCE_POSTS_CSV = shared/data/raw/study_phase_2_part_2/stimuli/flips.csv
```

```text
@dataclass(frozen=True)
class BedrockUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

class BedrockConverseEngine(BaseBatchExecutionEngine):
    last_usage: BedrockUsage | None
    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]

def build_bedrock_engine(spec: FeatureSpec, run_config: FeatureRunConfig) -> BedrockConverseEngine
  boto3 bedrock-runtime client in BEDROCK_REGION
  model DEFAULT_BEDROCK_NOVA_MICRO
  sleep_fn is not required

def converse_label(client, model_id, system_prompt, user_text) -> tuple[parsed_schema, BedrockUsage]
  Converse with system = system_prompt + BEDROCK_JSON_INSTRUCTION
  inferenceConfig maxTokens=BEDROCK_MAX_TOKENS, temperature=BEDROCK_TEMPERATURE
  Parse JSON from the first text block (strip optional markdown fences)
  Validate with spec.llm_output_schema
  Return parsed model and token usage from the response

def parse_json_object(text: str) -> dict
  Strip optional ```json fences
  json.loads
  Raise ValueError if not an object

batch_label_records:
  empty tasks -> []
  run converse_label per task with a thread pool of size run_config.max_concurrency
  preserve input order
  sum usage into last_usage
  attach label_timestamp like the OpenAI engine
```

Smoke metrics dataclass mirrors `OpenAIEngineSmokeMetrics`, plus:

```text
estimated_cost_usd: float
```

`compute_bedrock_engine_smoke_metrics` uses on-demand Ohio rates. Reuse `load_smoke_label_tasks` from `smoke_openai_engine.py`.

The smoke spec uses `engine_type="bedrock"` and is built only in the smoke script. Do not change `FEATURE_REGISTRY`.

`run_config` for the smoke is `FeatureRunConfig(max_concurrency=SMOKE_MAX_CONCURRENCY)`.

## Tests (pseudocode then real)

given a mocked Converse client that returns JSON `{"category":"news"}` and usage 10/2
when `batch_label_records` is called with one task
then the row has that task uri, category news, and a label_timestamp
and `last_usage.total_tokens == 12`

given two mocked Converse responses, news then opinion
when two tasks are labeled
then categories are news, opinion in input order

given empty tasks
when `batch_label_records` is called
then the result is `[]` and Converse is not called

given Converse text that is not JSON
when `batch_label_records` is called
then raise `ValueError`

given `compute_bedrock_engine_smoke_metrics` with 1000 input tokens, 50 output tokens, 10 requests, 2.0 seconds
when the helper runs
then posts_per_second is 5.0, tokens_per_second is 525.0, estimated_cost_usd is `(1000 * 0.035 + 50 * 0.14) / 1_000_000`

given `build_engine` with `engine_type="bedrock"`
when `build_engine` is called
then it returns the Bedrock engine builder result

Follow UNIT_TESTING_STANDARDS. One test class per public function. Use `result` and `expected`.

## Pass / fail

Must pass:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/generate_features/test_bedrock_engine.py tests/data_platform/generate_features/test_smoke_bedrock_engine.py tests/data_platform/generate_features/test_metadata.py -q
```

Exit 0.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python data_platform/generate_features/smoke_bedrock_engine.py \
  --posts-csv shared/data/raw/study_phase_2_part_2/stimuli/flips.csv \
  --post-count 100 \
  --id-column post_primary_key \
  --text-column original_text
```

Expected: exit 0. Stdout is metrics JSON with `labeled_count` 100, `model` `us.amazon.nova-micro-v1:0`, and a positive `estimated_cost_usd`. Write the same JSON to `experiments/bedrock_batch_parallelization_2026_09_06/smoke_metrics.json` and a short table to `SMOKE_RESULTS.md`.

Must fail the step if:

- Production registry features change `engine_type`.
- The engine calls `create_model_invocation_job`.
- The smoke labels fewer than 100 posts.
- Tests hit live AWS.

## Commands with expected output

```bash
PYTHONPATH=. uv run pytest tests/data_platform/generate_features -q
```

Expected: exit 0.
