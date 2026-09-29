# Step 2: Mine candidate features with GPT-5.6 Terra

Step 2 sends each of the 320 batches to GPT-5.6 Terra through the OpenAI Batch API and saves the candidate features that come back. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py`. Step 2 also adds the three shared helpers that steps 5 and 6 reuse, which are the API key lookup, the GPT-5.6 Terra batch wrapper, and the estimate table.

Out of scope are deduplication, embeddings, and any change to `data_platform/`.

## Decisions

Use `OpenAIBatchEngine` from `data_platform/generate_features/engines/openai_engine.py` with no edits. Build it with `OpenAIBatchEngineConfig(model="gpt-5.6-terra", temperature=1.0, poll_interval_seconds=30.0, completion_window="24h", endpoint="/v1/chat/completions")`. On 2026-09-29 the model returned HTTP 400 for `temperature=0.0` with the message "Only the default (1) value is supported", so the temperature is 1.0.

Call `batch_label_records` once per run, so each run is one provider batch. The method raises when any request fails, and the operator reruns the command. With 320 requests, a full rerun costs at most one more batch and needs no resume code.

The engine sends `spec.system_prompt` as the system message and `LabelTask.text` as the user message. The system message holds the task and the six categories, and the user message holds the stimuli and the repeated task. The row model the engine checks is `{source_record_id, label_timestamp, ...parsed output}`, so the row model adds those two string fields to the output fields.

The engine keeps no token counts, but the Batch output file does. After the batch completes, download `engine.last_batch.output_file_id` with the same client and read `response.body.usage.prompt_tokens` and `response.body.usage.completion_tokens` from each line. The line's `custom_id` is `task-` plus the task index padded to 5 digits, from `CUSTOM_ID_PREFIX` and `CUSTOM_ID_INDEX_WIDTH` in the engine module.

The smoke test sends the first 5 batches, `batch_000` to `batch_004`, as one provider batch. The estimates use these rules:

- Input tokens and output tokens are the median per smoke request times 320.
- Price is the median input tokens times $1.00 per million plus the median output tokens times $6.00 per million. The $1.00 and $6.00 rates are half of the $2.00 and $12.00 list rates pinned for `openai/gpt-5.6-terra` in `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/constants.py` on branch `origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f`, because the Batch API bills at half the list rate.
- Runtime is the wall time of the smoke batch, from submit to the downloaded output. The full run is also one provider batch. The Batch API does not process requests one after another, so the smoke wall time is the closest measure we have, even though a 320-request batch can take longer than a 5-request batch. `RESULTS.md` states the assumption under the table.
- Low is the median times 0.8, and high is the median times 1.2.

The full run refuses to start when `step2_mine_candidate_features/estimates.json` is missing from the local outputs and from S3.

When `OPENAI_API_KEY` is not set, download the secret `openai-api-key` in AWS Secrets Manager in `us-east-2` and set the variable. The secret is either a plain string or a JSON object. For a JSON object, take the first non-empty value among the keys `api_key` and `OPENAI_API_KEY`.

## Prompt

`src/step2_mine_candidate_features/prompt.py` holds the text below exactly. `SYSTEM_PROMPT` is the `## Task` section and the `## Categories of features` section. `USER_TEMPLATE` is the `## Stimuli` section and the `## Task (repeated)` section, with `{kept_pairs}` and `{removed_pairs}` as the only placeholders.

```markdown
## Task

You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

You will be shown a batch of posts that human annotators kept on the platform and a batch of posts that human annotators removed. Your job is to consider them jointly, and to find features that are distinct to the posts that were kept and distinct to the posts that were removed.

Return as structured output.

## Categories of features

Here are the categories that we want to consider:

### Category 1: Surface and lexical (`lexical`)

This category is about how the post is written, not what claim it makes. It covers length, slang, heavy punctuation, all-caps emphasis, profanity, hashtags and account mentions, and a high density of proper names.

Examples include emphatic typography, profane derogatory insults, colloquial language and insults, and hashtags and account mentions.

### Category 2: Topic and subject matter (`topic_subject`)

This category is about the subject of the post. Examples include a policy area (guns, climate, immigration, abortion, elections), a specific event or bill, a geographic scope, a historical analogy, and culture-war salience.

### Category 3: Semantic content (`semantic_content`)

This category is about the kind of claim the post makes. Examples include causal claims, moral language, a factual claim versus speculation, conspiracy, a claim that a group is being persecuted, a policy prescription, and a cost-benefit argument.

### Category 4: Pragmatics and communicative intent (`pragmatics`)

This category is about what the post is doing to the reader. Examples include sarcasm, mockery, a call to action, persuasion, venting, hedging, and outrage.

### Category 5: Target and directionality (`target`)

This category is about who the post attacks or praises, and which political side it points at. Examples include the type of actor criticized or praised, a left/right cue, us-versus-them framing, and elite-versus-populist framing.

### Category 6: Compositional and syntactic structure (`structure`)

This category is about the shape of the sentences. Examples include if-then conditionals, contrast with "but" or "however," rhetorical questions, parallel repetition, lists, quoted or attributed speech, and direct address in the second person.
```

```markdown
## Stimuli

### Posts that were kept

Here are ten post pairs that were kept by human annotators:

{kept_pairs}

### Posts that were removed

Here are ten post pairs that were removed by human annotators:

{removed_pairs}

## Task (repeated)

Consider the kept post pairs and the removed post pairs jointly. For each of the six categories, list the features that are distinct to the kept post pairs and the features that are distinct to the removed post pairs. Write each feature as one short phrase. Return as structured output.
```

Render each pair as two lines, numbered from 1 within its list, with the kept pairs in `keep_post_ids` order and the removed pairs in `remove_post_ids` order:

```text
1. Original post: {original_text}
   Mirror post: {mirror_text}
```

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | `OpenAIBatchEngine`, `OpenAIBatchEngineConfig`, `create_openai_client`, `CUSTOM_ID_PREFIX`, `CUSTOM_ID_INDEX_WIDTH` |
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `FeatureRunConfig`, `LabelTask` |
| `/workspace/data_platform/generate_features/engines/base.py` | `row_with_label_timestamp`, which sets the row shape |
| `/workspace/tests/data_platform/generate_features/conftest.py` | The fake OpenAI client pattern for tests |
| `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/storage.py` | `download_artifact`, `upload_artifact`, `local_path` |

## Files allowed to change

All paths are under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `shared/secrets.py`, `shared/llm.py`, and `shared/estimates.py`
- Create `src/step2_mine_candidate_features/__init__.py`, `prompt.py`, `schemas.py`, and `run.py`
- Create `tests/test_secrets.py`, `tests/test_llm.py`, `tests/test_estimates.py`, `tests/test_mining_prompt.py`, and `tests/test_mining_schemas.py`
- Edit `SETUP.md` to add the step 2 commands, and edit `RESULTS.md` under `## Step 2: candidate features`

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/shared/**`
- `/workspace/pyproject.toml` and `/workspace/uv.lock`

## Contracts

Add to `shared/constants.py`:

```text
TERRA_MODEL = "gpt-5.6-terra"
TERRA_TEMPERATURE = 1.0
OPENAI_POLL_INTERVAL_SECONDS = 30.0
TERRA_BATCH_USD_PER_MILLION_INPUT = 1.00
TERRA_BATCH_USD_PER_MILLION_OUTPUT = 6.00
AWS_SECRETS_REGION = "us-east-2"
OPENAI_SECRET_ID = "openai-api-key"
FEATURE_CATEGORIES = ("lexical", "topic_subject", "semantic_content",
                      "pragmatics", "target", "structure")
FEATURE_SIDES = ("features_from_kept_posts", "features_from_removed_posts")
MINING_SMOKE_KEY = "step2_mine_candidate_features/smoke_candidate_features.jsonl"
MINING_ESTIMATES_KEY = "step2_mine_candidate_features/estimates.json"
CANDIDATE_FEATURES_KEY = "step2_mine_candidate_features/candidate_features.jsonl"
```

`shared/secrets.py`:

```text
parse_secret_string(raw: str, keys: tuple[str, ...]) -> str
  Return the stripped string when raw is not a JSON object. For a JSON object, return the first
  non-empty value among keys. Raise ValueError when nothing non-empty is found.

ensure_openai_api_key() -> None
  Leave OPENAI_API_KEY alone when it is set. Otherwise read OPENAI_SECRET_ID in AWS_SECRETS_REGION,
  parse it with keys ("api_key", "OPENAI_API_KEY"), and set OPENAI_API_KEY.
```

`shared/llm.py`:

```text
@dataclass(frozen=True) RequestUsage: source_record_id: str, input_tokens: int, output_tokens: int
@dataclass(frozen=True) BatchRun: rows: list[dict], usage: list[RequestUsage], wall_seconds: float

build_feature_spec(name: str, row_model: type[BaseModel], system_prompt: str,
                   output_schema: type[BaseModel]) -> FeatureSpec
  engine_type="openai".

build_terra_engine(spec: FeatureSpec, client: OpenAIBatchClient) -> OpenAIBatchEngine
  OpenAIBatchEngineConfig from TERRA_MODEL, TERRA_TEMPERATURE, OPENAI_POLL_INTERVAL_SECONDS,
  "24h", and "/v1/chat/completions"; FeatureRunConfig(); time.sleep.

parse_request_usage(output_text: str, ordered_ids: list[str]) -> list[RequestUsage]
  Map each custom_id back to ordered_ids by index. Raise ValueError when a line has no usage.

run_terra_batch(engine: OpenAIBatchEngine, client: OpenAIBatchClient,
                tasks: list[LabelTask], clock: Callable[[], float]) -> BatchRun
  Time batch_label_records with clock, download last_batch.output_file_id, and parse usage.
```

`shared/estimates.py`:

```text
@dataclass(frozen=True) EstimateRow: value_name: str, low: float, median: float, high: float

estimate_row(value_name: str, median: float) -> EstimateRow
  low = median * (1 - ESTIMATE_BAND), high = median * (1 + ESTIMATE_BAND).

build_estimates(input_tokens: list[int], output_tokens: list[int], runtime_minutes: float,
                total_requests: int, usd_per_million_input: float,
                usd_per_million_output: float) -> list[EstimateRow]
  Rows in order "Runtime (minutes)", "Input tokens", "Output tokens", "Price (USD)".
  Raise ValueError when input_tokens or output_tokens is empty.

render_estimates_markdown(rows: list[EstimateRow]) -> str
  A table with header | Value | Low | Median | High |. Tokens have no decimals and use
  thousands separators. Minutes have 1 decimal, and prices have 2 decimals with a $ sign.

write_estimates(rows: list[EstimateRow], relative_key: str) -> Path
require_estimates(relative_key: str) -> None
  Raise FileNotFoundError when download_artifact finds no file locally or in S3.
```

`src/step2_mine_candidate_features/schemas.py`:

```text
FeatureCategoryLists(BaseModel, extra="forbid"):
  lexical, topic_subject, semantic_content, pragmatics, target, structure: list[str]
CandidateFeatures(BaseModel, extra="forbid"):
  features_from_kept_posts: FeatureCategoryLists
  features_from_removed_posts: FeatureCategoryLists
CandidateFeatureRow(CandidateFeatures):
  source_record_id: str, label_timestamp: str
```

Each list field has a `Field(description=...)` that repeats the category title from the prompt. No field has a default, because OpenAI strict structured output requires every field.

`src/step2_mine_candidate_features/prompt.py`:

```text
SYSTEM_PROMPT: str
USER_TEMPLATE: str
render_pair_list(pairs: list[tuple[str, str]]) -> str
render_user_prompt(kept_pairs: list[tuple[str, str]], removed_pairs: list[tuple[str, str]]) -> str
build_mining_tasks(batches: list[dict], cohort: pd.DataFrame) -> list[LabelTask]
  One LabelTask per batch, with uri = batch_id and text = render_user_prompt(...).
  Raise ValueError when a batch has other than 10 kept or 10 removed pairs.
```

`src/step2_mine_candidate_features/run.py` takes exactly one of `--smoke` or `--full`.

- With `--smoke`, it runs the first `SMOKE_QUERY_COUNT` tasks, writes and uploads `MINING_SMOKE_KEY` and `MINING_ESTIMATES_KEY` with `total_requests=EXPECTED_BATCHES`, and prints the estimate table.
- With `--full`, it calls `require_estimates(MINING_ESTIMATES_KEY)`, runs all 320 tasks, raises `ValueError` unless there are 320 rows, writes and uploads `CANDIDATE_FEATURES_KEY`, and prints one line.

## Tests

- `tests/test_secrets.py`: `TestParseSecretString` covers a plain string, a JSON object with `api_key`, and a JSON object with only empty values, which raises `ValueError`. `TestEnsureOpenaiApiKey.test_keeps_existing_env` sets the variable with `monkeypatch` and asserts that Secrets Manager is not called.
- `tests/test_llm.py`: `TestParseRequestUsage` builds two output lines, `task-00000` and `task-00001`, and asserts the token counts map to the right ids. It also asserts that a line without `usage` raises `ValueError`. `TestRunTerraBatch` uses a fake engine and a fake client from the `conftest.py` pattern, and a clock that returns 0.0 and then 90.0, and asserts `wall_seconds == 90.0`.
- `tests/test_estimates.py`: `TestEstimateRow` checks that median 100 gives low 80 and high 120. `TestBuildEstimates` checks that per-request inputs `[10, 20, 30]` with 320 requests give a median of 6,400 input tokens, and that the price row equals the tokens times the rates. `TestRenderEstimatesMarkdown` checks the header and the row order.
- `tests/test_mining_prompt.py`: `TestRenderPairList` checks the two-line numbered format. `TestBuildMiningTasks` checks one task per batch with the batch id as `uri`, and checks that a batch with 9 kept ids raises `ValueError`.
- `tests/test_mining_schemas.py`: `TestCandidateFeatures` checks that the example JSON from the issue validates and that an extra key raises a validation error.

No test calls OpenAI or reads S3.

## Commands

```bash
PYTHONPATH=. uv run pytest experiments/study_2_llm_based_feature_extraction_2026_09_29/tests -q
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --smoke
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --full
```

The smoke command prints a Markdown table with the rows `Runtime (minutes)`, `Input tokens`, `Output tokens`, and `Price (USD)`, and the columns `Low`, `Median`, and `High`. Paste the table under `## Step 2: candidate features` in `RESULTS.md`, with one sentence under it that says the runtime assumes one provider batch.

The full command prints this line, where `N` is the total number of feature strings across all batches, sides, and categories:

```text
mined_batches=320 candidate_features=N
```

Add the count of feature strings per category and per side to `RESULTS.md`.

## Pass

The pytest command exits 0. The smoke command prints the four-row table. The full command prints `mined_batches=320`, and it uploads `candidate_features.jsonl` to the S3 prefix.

## Fail

The step fails when a test calls OpenAI, when the full run starts without `estimates.json`, when the full run writes fewer than 320 rows, or when any file under `data_platform/` changes.
