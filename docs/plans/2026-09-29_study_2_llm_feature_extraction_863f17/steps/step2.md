# Step 2: Mine candidate features with GPT-5.6 Terra

Step 2 sends each of the 320 batches to GPT-5.6 Terra with the synchronous OpenAI chat completions API and saves the candidate features that come back. Requests run through asyncio with a thread pool of 8, so at most 8 requests are in flight. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py`. Step 2 also adds the three shared helpers that later steps reuse: the API key lookup, the concurrent runner that step 5 uses, and the estimate table that steps 5 and 6 use.

Out of scope are deduplication, embeddings, and any change to `data_platform/`.

## Decisions

Do not use `OpenAIBatchEngine` or the OpenAI Batch API. On 2026-09-29 batch creation returned HTTP 400 for `completion_window=1h` and said the only supported value is `24h`. This experiment calls the synchronous client's `chat.completions.parse` instead.

`LLM_MODEL` is `gpt-5.6-terra`. On 2026-09-29 that model returned HTTP 400 for `temperature=0.0` with the message "Only the default (1) value is supported", so the temperature is 1.0.

`run_concurrent` starts one asyncio event loop and one `ThreadPoolExecutor` with `max_workers=LLM_CONCURRENCY`. `LLM_CONCURRENCY` is 8. Each worker calls the synchronous OpenAI client. The pool is the cap, so a run never has more than 8 requests in flight. `asyncio.gather` waits for every task. Rows and token counts are stored in the same order as the input tasks. If any request raises, the run raises and the operator reruns the command. There is no resume file, and `run.py` uploads only after `run_concurrent` returns.

Each call sends the system prompt as the system message and `LabelTask.text` as the user message. The system message holds the task and the six categories, and the user message holds the stimuli and the repeated task. The response format is the output schema, `CandidateFeatures` in this step. The saved row is `{source_record_id, label_timestamp, ...parsed output}`. `source_record_id` is `task.uri`. `label_timestamp` is one `get_current_timestamp()` value for the whole run. Token counts come from `response.usage.prompt_tokens` and `response.usage.completion_tokens` on that same response.

The smoke test sends the first 5 batches, `batch_000` to `batch_004`. Those 5 requests share the pool of 8, so they run together. The estimates use these rules:

- Input tokens and output tokens are the median per smoke request times 320.
- Price is the median input tokens times $2.00 per million plus the median output tokens times $12.00 per million. Those are the list rates pinned for `openai/gpt-5.6-terra` in `experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/constants.py` on branch `origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f`. The synchronous API does not get the Batch API half-price rate.
- The runtime median is the smoke wall time, from the start of the first request to the end of the last of the 5, times 40. 320 divided by 8 is 40, and the 5 smoke requests fit in one group of 8. The general rule is `scaled_runtime_minutes`: smoke wall minutes times the full request count divided by 8, rounded up, divided by the smoke request count divided by 8, rounded up. `RESULTS.md` states that under the table.
- Low is the median times 0.8, and high is the median times 1.2.

The full run refuses to start when `step2_mine_candidate_features/estimates.json` is missing from the local outputs and from S3.

`OPENAI_API_KEY` is not set. Download the secret `openai-api-key` in AWS Secrets Manager in `us-east-2` and set the variable. The secret is either a plain string or a JSON object. For a JSON object, take the first non-empty value among the keys `api_key` and `OPENAI_API_KEY`.

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

Each numbered item is one post pair. A pair is an original post and a mirror of that post. The two texts are labeled text 1 and text 2. Those labels do not say which text is the original.

Here are ten post pairs that were kept by human annotators:

{kept_pairs}

### Posts that were removed

Each numbered item is one post pair, labeled the same way as the kept pairs.

Here are ten post pairs that were removed by human annotators:

{removed_pairs}

## Task (repeated)

Consider the kept post pairs and the removed post pairs jointly. For each of the six categories, list the features that are distinct to the kept post pairs and the features that are distinct to the removed post pairs. Write each feature as one short phrase. Return as structured output.
```

Render each pair as two lines, numbered from 1 within its list, with the kept pairs in `keep_post_ids` order and the removed pairs in `remove_post_ids` order. Text 1 is `original_text` and text 2 is `mirror_text`. The prompt does not say that.

```text
1. Text 1: {original_text}
   Text 2: {mirror_text}
```

## Files to inspect

| Path | Why |
|------|-----|
| `docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `data_platform/generate_features/models.py` | `LabelTask` (`uri`, `text`). Do not use `OpenAIBatchEngine`. |
| `lib/timestamp_utils.py` | `get_current_timestamp` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/storage.py` | `download_artifact`, `upload_artifact`, `local_path` |

## Files allowed to change

All paths are under `experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `shared/secrets.py`, `shared/llm.py`, and `shared/estimates.py`
- Create `src/step2_mine_candidate_features/__init__.py`, `prompt.py`, `schemas.py`, and `run.py`
- Edit `SETUP.md` to add the step 2 commands, and edit `RESULTS.md` under `## Step 2: candidate features`

## Files forbidden to change

- `data_platform/**`
- `shared/**`
- `pyproject.toml` and `uv.lock`

## Contracts

Add to `shared/constants.py`:

```text
LLM_MODEL = "gpt-5.6-terra"
LLM_TEMPERATURE = 1.0
LLM_CONCURRENCY = 8
LLM_USD_PER_MILLION_INPUT = 2.00
LLM_USD_PER_MILLION_OUTPUT = 12.00
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
  Download OPENAI_SECRET_ID in AWS_SECRETS_REGION, parse it with keys ("api_key", "OPENAI_API_KEY"),
  and set OPENAI_API_KEY. Do this even when the variable is already set.
```

`shared/llm.py`:

```text
@dataclass(frozen=True) RequestUsage: source_record_id: str, input_tokens: int, output_tokens: int
@dataclass(frozen=True) ConcurrentRun: rows: list[dict], usage: list[RequestUsage], wall_seconds: float

complete_one(client: OpenAI, task: LabelTask, output_schema: type[BaseModel],
             row_model: type[BaseModel], system_prompt: str, label_timestamp: str) -> tuple[dict, RequestUsage]
  One synchronous client.chat.completions.parse call.
  model=LLM_MODEL, temperature=LLM_TEMPERATURE, response_format=output_schema.
  Messages are the system prompt and task.text.
  Raise ValueError when the parsed object is missing or usage is missing.
  source_record_id is task.uri. Validate the saved row with row_model.

run_concurrent(tasks: list[LabelTask], output_schema: type[BaseModel],
               row_model: type[BaseModel], system_prompt: str,
               clock: Callable[[], float]) -> ConcurrentRun
  Call ensure_openai_api_key(), then build one synchronous OpenAI client.
  asyncio.run drives a ThreadPoolExecutor(max_workers=LLM_CONCURRENCY).
  Each complete_one runs on that executor. At most LLM_CONCURRENCY calls are in flight.
  rows and usage follow the input task order.
  wall_seconds is the clock after the gather minus the clock before it.
  One label_timestamp from get_current_timestamp() is shared by every row.
  Raise the request error. Do not return a partial run.
```

`shared/estimates.py`:

```text
@dataclass(frozen=True) EstimateRow: value_name: str, low: float, median: float, high: float

estimate_row(value_name: str, median: float) -> EstimateRow
  low = median * (1 - ESTIMATE_BAND), high = median * (1 + ESTIMATE_BAND).

scaled_runtime_minutes(smoke_wall_minutes: float, smoke_requests: int,
                       total_requests: int, concurrency: int) -> float
  Raise ValueError when any argument is <= 0.
  Return smoke_wall_minutes * ceil(total_requests / concurrency) / ceil(smoke_requests / concurrency).

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

- With `--smoke`, it runs the first `SMOKE_QUERY_COUNT` tasks through `run_concurrent`, writes and uploads `MINING_SMOKE_KEY` and `MINING_ESTIMATES_KEY` with `total_requests=EXPECTED_BATCHES`, and prints the estimate table. The runtime median comes from `scaled_runtime_minutes` with `concurrency=LLM_CONCURRENCY`. The price rates are `LLM_USD_PER_MILLION_INPUT` and `LLM_USD_PER_MILLION_OUTPUT`.
- With `--full`, it calls `require_estimates(MINING_ESTIMATES_KEY)`, runs all 320 tasks through `run_concurrent`, raises `ValueError` unless there are 320 rows, writes and uploads `CANDIDATE_FEATURES_KEY`, and prints one line.

## Commands

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --smoke
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --full
```

The smoke command prints a Markdown table with the rows `Runtime (minutes)`, `Input tokens`, `Output tokens`, and `Price (USD)`, and the columns `Low`, `Median`, and `High`. Paste the table under `## Step 2: candidate features` in `RESULTS.md`, with one sentence under it that says the runtime scales the smoke wall time by the number of groups of 8 requests.

The full command prints this line, where `N` is the total number of feature strings across all batches, sides, and categories:

```text
mined_batches=320 candidate_features=N
```

Add the count of feature strings per category and per side to `RESULTS.md`.

## Pass

The smoke command prints the four-row table. The full command prints `mined_batches=320`, and it uploads `candidate_features.jsonl` to the S3 prefix.

## Fail

The step fails when the full run starts without `estimates.json`, when the full run writes fewer than 320 rows, when the code calls the OpenAI Batch API, or when any file under `data_platform/` changes.
