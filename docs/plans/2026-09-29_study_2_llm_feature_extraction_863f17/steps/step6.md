# Step 6: Label every pair with Jev

Step 6 asks Jev whether each approved feature is present in each of the 20,000 Study 2 pairs, and it turns the probabilities into 0 or 1 columns with a cutoff of 0.7. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/run.py`.

Step 6 starts only after you approve the feature list at the end of step 5. Out of scope are analyses, charts, and any change to `shared/label_to_detail.py`.

## Decisions

Jev is the TypeSafe model `jev-1.13.0`. Its client is `TypeSafeClient` in the package `typesafe-sdk==0.7.1`. The package is not in `pyproject.toml` on `main`, so every Jev command adds it with `uv run --with typesafe-sdk==0.7.1`. `shared/jev.py` imports the package inside the function that builds the client, so the rest of the experiment imports without it.

A Jev request sends one `state` dictionary and one question per feature. Each question is a `Noul` with an `instructions` string, and each answer has a `noul` value between 0 and 1, which is the probability that the answer is yes. On 2026-09-29 one request with one pair and 60 questions returned in 0.13 seconds, used 2,654 input tokens, and gave 0.88 for all-caps emphasis on a post that ended in "Vote them OUT!". A request therefore holds one pair and up to 60 features. When `LABEL_TO_DETAIL` has more than 60 features, the pair takes more than one request, and each request holds the next 60 keys in sorted order.

The pairs are all 20,000 rows of `STUDY_2_STIMULI`, with `post_id` equal to `post_primary_key` as a string, sorted by `post_id`. The state is one key, `pair`, whose value is this text:

```text
Text 1: {original_text}

Text 2: {mirrored_text}
```

Text 1 is the original post and text 2 is the mirror. The prompt does not say that.

Each question id is the feature's key in `LABEL_TO_DETAIL`, for example `is_sarcasm`. Each question's instructions are the text below, with `{feature_json}` set to `json.dumps({"name": ..., "description": ...}, ensure_ascii=False)` for that feature. The text follows the issue's starting prompt, changed from one post and a list of features to one pair and one feature, because each question scores one feature:

```markdown
You are labeling one social-media post pair against one approved feature. The pair is in `pair`. Each pair is an original post and a mirror of that post. The two texts are labeled text 1 and text 2. Those labels do not say which text is the original.

Return true when the feature clearly applies to the post text, otherwise return false. Use only the provided feature definition.

Feature:
{feature_json}
```

Requests run on 8 threads, with one client per thread. A shared limiter starts at most 1,000 requests per minute, which is the cap the Jev experiment used. A failed request is retried up to 3 more times after 1, 2, and 4 seconds. A pair that still fails goes to `deadletter.jsonl` and is not written to the predictions file, so a rerun picks it up.

Each finished pair appends one line to `jev_predictions.jsonl` with the SHA-256 hash of `LABEL_TO_DETAIL`, serialized as JSON with sorted keys. On a rerun, pairs whose line has the current hash are skipped. Lines with an older hash are ignored, so an edit to the feature list relabels every pair.

The smoke test labels the first 5 pairs in `post_id` order, which is 5 queries when there are 60 features or fewer. The estimates follow the step 2 rules, with these changes:

- The total request count is 20,000 times the number of requests per pair.
- Price uses the pinned Jev rates in `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/pricing.py` on branch `origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f`, which are $0.042 per million input tokens and $0 per million output tokens.
- Runtime is the larger of two numbers. The first is the median request latency times the total request count divided by 8 threads. The second is the total request count divided by 1,000 requests per minute.

A feature is present when its probability is 0.7 or higher. `FEATURE_PRESENT_THRESHOLD = 0.7` goes in `shared/constants.py`, as the issue asks.

When `TYPESAFE_API_KEY` is not set, download the secret `jev-typesafe-api-key` in AWS Secrets Manager in `us-east-2`, and take the first non-empty value among the keys `api_key`, `TYPESAFE_API_KEY`, and `key`.

## Files to inspect

| Path | Why |
|------|-----|
| `docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py` on branch `origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f` | `build_client`, `score_batch`, the thread pool, and resume. Read it with `git show origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f:experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/jev_scorer.py`. |
| `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/rate_limiter.py` on the same branch | The request start limiter |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/constants.py` | `LABEL_TO_DETAIL` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/secrets.py` | `parse_secret_string` |
| `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/estimates.py` | `estimate_row`, `render_estimates_markdown`, `require_estimates` |

## Files allowed to change

All paths are under `experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Edit `shared/secrets.py` to add `get_jev_api_key`
- Create `shared/jev.py`
- Create `src/step6_label_posts_with_features/__init__.py`, `prompt.py`, `label.py`, `threshold.py`, and `run.py`
- Edit `SETUP.md` to add the step 6 commands, and edit `RESULTS.md` under `## Step 6: Jev labels`

## Files forbidden to change

- `experiments/study_2_llm_based_feature_extraction_2026_09_29/shared/label_to_detail.py`
- `pyproject.toml` and `uv.lock`
- `shared/**`
- `experiments/predict_keep_remove_jev_gepa_2026_09_23/**`

## Contracts

Add to `shared/constants.py`:

```text
JEV_MODEL_ID = "jev-1.13.0"
JEV_SECRET_ID = "jev-typesafe-api-key"
JEV_STATE_KEY = "pair"
JEV_REQUEST_TIMEOUT_SECONDS = 120.0
JEV_MAX_WORKERS = 8
JEV_MAX_REQUESTS_PER_MINUTE = 1000
JEV_RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
MAX_FEATURES_PER_JEV_REQUEST = 60
JEV_USD_PER_MILLION_INPUT = 0.042
JEV_USD_PER_MILLION_OUTPUT = 0.0
FEATURE_PRESENT_THRESHOLD = 0.7
LABEL_COLUMNS_PREFIX = ("post_id", "original_text", "mirror_text")
LABELING_SMOKE_KEY = "step6_label_posts_with_features/smoke_jev_predictions.jsonl"
LABELING_ESTIMATES_KEY = "step6_label_posts_with_features/estimates.json"
JEV_PREDICTIONS_KEY = "step6_label_posts_with_features/jev_predictions.jsonl"
JEV_DEADLETTER_KEY = "step6_label_posts_with_features/deadletter.jsonl"
JEV_PROBABILITIES_KEY = "step6_label_posts_with_features/jev_probabilities.parquet"
POST_FEATURE_LABELS_KEY = "step6_label_posts_with_features/post_feature_labels.parquet"
```

`shared/secrets.py` adds:

```text
get_jev_api_key() -> str
```

`shared/jev.py`:

```text
@dataclass(frozen=True) JevResponse: probabilities: dict[str, float], input_tokens: int,
                                     output_tokens: int, latency_ms: float

class JevScorer:
  __init__(self, client: Any, question_factory: Callable[[str], Any],
           clock: Callable[[], float]) -> None
  score(self, state: dict[str, str], instructions: dict[str, str]) -> JevResponse
    Build one question per id with question_factory, call client.system_one(state=...,
    questions=..., model=JEV_MODEL_ID), and read answers[id].noul as float.
    Raise KeyError when an answer is missing, and ValueError when a value is outside 0 to 1.

build_jev_scorer(api_key: str) -> JevScorer
  Import TypeSafeClient, Noul, and RetryPolicy from typesafe_sdk inside the function. Build
  TypeSafeClient(api_key=..., model=JEV_MODEL_ID, retry=RetryPolicy(max_retries=0),
  timeout=JEV_REQUEST_TIMEOUT_SECONDS) with question_factory=lambda text: Noul(instructions=text)
  and clock=time.perf_counter.

class RequestStartLimiter:
  __init__(self, max_per_minute: int, clock: Callable[[], float],
           sleep_fn: Callable[[float], None]) -> None
  wait(self) -> None
```

`src/step6_label_posts_with_features/prompt.py`:

```text
NOUL_INSTRUCTION_TEMPLATE: str
render_pair_state(original_text: str, mirror_text: str) -> dict[str, str]
render_feature_instruction(detail: dict[str, str]) -> str
```

`src/step6_label_posts_with_features/label.py`:

```text
@dataclass(frozen=True) PairLabelResult: post_id: str, probabilities: dict[str, float],
                                         input_tokens: int, output_tokens: int,
                                         latency_ms: float, n_requests: int, attempts: int
chunk_feature_keys(keys: list[str], max_per_request: int) -> list[list[str]]
features_sha256(label_to_detail: dict[str, dict[str, str]]) -> str
label_pair(scorer: JevScorer, pair: pd.Series, label_to_detail: dict[str, dict[str, str]],
           limiter: RequestStartLimiter, sleep_fn: Callable[[float], None]) -> PairLabelResult
  One request per chunk, each retried per the Decisions section.
labeled_post_ids(predictions_path: Path, sha: str) -> set[str]
run_labeling(pairs: pd.DataFrame, scorer_factory: Callable[[], JevScorer],
             label_to_detail: dict[str, dict[str, str]], predictions_path: Path,
             deadletter_path: Path, limiter: RequestStartLimiter,
             sleep_fn: Callable[[float], None], max_workers: int) -> list[PairLabelResult]
  Skip labeled pairs, append each finished pair, and deadletter each pair that ran out of retries.
```

`src/step6_label_posts_with_features/threshold.py`:

```text
probabilities_frame(predictions_path: Path, sha: str, label_keys: list[str]) -> pd.DataFrame
  One row per post_id with one float column per label key. Raise ValueError on a duplicate
  post_id or a missing key.
apply_threshold(probabilities: pd.DataFrame, threshold: float) -> pd.DataFrame
  1 when the value is at least threshold, else 0, as int8.
build_label_table(labels: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame
  Columns LABEL_COLUMNS_PREFIX, then the label keys in sorted order.
```

`src/step6_label_posts_with_features/run.py` takes exactly one of `--smoke` or `--full`. It calls `validate_label_to_detail` from `src/step5_name_clusters/write_label_details.py` on `LABEL_TO_DETAIL` before anything else.

- With `--smoke`, it labels the first `SMOKE_QUERY_COUNT` pairs into `LABELING_SMOKE_KEY`, writes and uploads `LABELING_ESTIMATES_KEY`, and prints the table.
- With `--full`, it calls `require_estimates(LABELING_ESTIMATES_KEY)`, labels all pairs, and uploads the predictions and the dead letters. It raises `ValueError` when the dead letter file has lines or when fewer than 20,000 pairs have the current hash. Otherwise it writes and uploads `JEV_PROBABILITIES_KEY` and `POST_FEATURE_LABELS_KEY`, and prints one line.

## Commands

```bash
PYTHONPATH=. uv run --with typesafe-sdk==0.7.1 python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/run.py --smoke
PYTHONPATH=. uv run --with typesafe-sdk==0.7.1 python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/run.py --full
```

Paste the smoke table under `## Step 6: Jev labels` in `RESULTS.md`. The full command prints this line, where `F` is the approved feature count and `R` is the number of requests the run sent:

```text
labeled_pairs=20000 features=F requests=R deadletters=0
```

## Pass

The full command prints `labeled_pairs=20000` and `deadletters=0`. `post_feature_labels.parquet` on S3 has 20,000 rows, the three text columns, and `F` label columns, all 0 or 1 with no missing values.

## Fail

The step fails when it starts before your approval, when `pyproject.toml` changes, or when any pair is missing from the label table.
