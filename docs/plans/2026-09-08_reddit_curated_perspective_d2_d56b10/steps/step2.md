# Step 2: Score medium comments with the Perspective thread-pool engine

## Goal

Operators need a Perspective toxicity probability for every medium curated comment, so this step sends the 20727 medium rows from Step 1 through the existing Perspective thread-pool engine, saves the probability, and ignores Perspective's own low, medium, and high tier.

## Dependencies

Step 1 load checks have passed on the pinned curated file. `--load-only` has printed `medium_rows=20727`.

## Scope

- Caller: `experiments/reddit_curated_perspective_v2_2026_09_08/run.py` → `score_medium_comments()` then `main()` with `--score`
- Slice: build `LabelTask` rows for medium comments → `ThreadPoolBatchEngine.batch_label_records` → persist `toxicity_prob` by `source_record_id` → resume from that file
- Out of scope: ranking, writing `mirrorview_v2.parquet`, changing `FEATURE_REGISTRY`, calling `ml_tooling.perspective_api.get_toxicity_prob` except through the registered engine, scoring low or high comments

## Pinned identities

| Field | Value |
|-------|-------|
| Engine | Product thread-pool engine for registry feature `is_toxic_tiered` |
| Builder | `data_platform.generate_features.engines.build_engine` |
| Concurrency | `FeatureRunConfig.max_concurrency = 80` |
| Task id | `LabelTask.uri = source_record_id` |
| Task text | `LabelTask.text = text` |
| Keep | `toxicity_prob` |
| Ignore | Perspective `toxicity_tier` |
| Resume file | `experiments/reddit_curated_perspective_v2_2026_09_08/outputs/medium_perspective_scores.parquet` |
| Secret | `GOOGLE_API_KEY` through `EnvVarsContainer` |

Do not write campaign objects under `features/reddit_2026_09_03_233928_llm_features_v1/`. This experiment is not a product feature run.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/generate_features/engines/thread_pool_engine.py` | `ThreadPoolBatchEngine.batch_label_records` |
| `data_platform/generate_features/engines/__init__.py` | `build_engine` |
| `data_platform/generate_features/registry.py` | `FEATURE_REGISTRY["is_toxic_tiered"]` |
| `data_platform/generate_features/is_toxic_tiered/generate_feature.py` | Returns `toxicity_prob` and `toxicity_tier`. Do not edit. |
| `data_platform/generate_features/models.py` | `LabelTask`, `FeatureRunConfig` |
| `ml_tooling/perspective_api.py` | Retries and `GOOGLE_API_KEY`. Do not edit. |
| `experiments/llm_based_toxicity_classifier_2026_09_05/run_smoke.py` | How an experiment constructs `build_engine` and `LabelTask` |

## Files allowed to change

- `experiments/reddit_curated_perspective_v2_2026_09_08/score_medium.py` (create)
- `experiments/reddit_curated_perspective_v2_2026_09_08/run.py`
- `experiments/reddit_curated_perspective_v2_2026_09_08/README.md`
- `tests/experiments/test_reddit_curated_perspective_v2.py`
- `experiments/reddit_curated_perspective_v2_2026_09_08/outputs/` after a live run (scores parquet is allowed in git if small)

## Files forbidden to change

- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `data_platform/generate_features/engines/thread_pool_engine.py`
- `ml_tooling/perspective_api.py`
- `data_platform/curate/configs/reddit/mirrorview.yaml`
- The pinned `mirrorview.parquet` S3 object

## Contracts to lock

```text
SCORE_FEATURE_NAME = "is_toxic_tiered"
SCORE_BATCH_SIZE = 64
SCORE_MAX_CONCURRENCY = 80

def tasks_for_medium_rows(medium: pd.DataFrame) -> list[LabelTask]
    one LabelTask per row
    uri=str(source_record_id)
    text=str(text)

def score_medium_comments(
    medium: pd.DataFrame,
    *,
    scores_path: Path,
    engine: BatchExecutionEngine | None = None,
) -> pd.DataFrame
```

Construct the production engine with:

```text
spec = FEATURE_REGISTRY["is_toxic_tiered"]
engine = build_engine(spec, FeatureRunConfig(max_concurrency=80, batch_size=64))
```

Tests pass a fake engine whose `batch_label_records` returns rows with `source_record_id` and `toxicity_prob`.

`score_medium_comments` reads `scores_path` if it exists. It skips ids that already have a finite `toxicity_prob` in `[0, 1]`. It scores the rest in batches of 64 through `engine.batch_label_records`. After each successful batch it rewrites `scores_path` so a crash does not lose finished ids.

The saved table has at least `source_record_id` and `toxicity_prob`. It may also store Perspective `toxicity_tier` for debugging, but later steps must not read that column to rank or to write v2.

If any medium id still lacks a probability after the engine returns, raise `ValueError` naming the missing ids (or a count plus a sample). Do not rank until the saved table covers all 20727 medium ids.

`--score` stdout includes:

```text
medium_rows=20727
already_scored=<n>
newly_scored=<n>
scores_path=experiments/reddit_curated_perspective_v2_2026_09_08/outputs/medium_perspective_scores.parquet
```

When the file is complete, `already_scored=20727` and `newly_scored=0` on a repeat run.

## Test design

Mock the engine. Do not call Perspective.

```text
given 3 medium rows and an empty scores file
and a fake engine that returns toxicity_prob 0.2, 0.8, 0.5
when score_medium_comments(...)
then the saved table has 3 rows
and source_record_id matches the inputs
and toxicity_prob matches the fake engine
and the fake engine received LabelTask.uri equal to source_record_id

given a scores file that already has 2 of 3 ids
when score_medium_comments(...)
then the fake engine is called only for the missing id
and the saved table has 3 rows

given a fake engine that omits one id
when score_medium_comments(...)
then ValueError

given medium rows that include a low-tier row
when tasks_for_medium_rows is only used after medium_rows()
then no low-tier id is scored
```

Also assert the CLI default engine is built from `FEATURE_REGISTRY["is_toxic_tiered"]` and `engine_type == "thread_pool"`, without calling `batch_label_records`.

## Implementation notes (implement-from-spec)

Full auto. One Git commit per phase that changes the repo.

1. Phase 2 scaffold `score_medium.py` stubs.
2. Phase 3 lock signatures.
3. Phase 4 add failing tests for resume and missing ids.
4. Phase 5:
   1. `tasks_for_medium_rows`
   2. `score_medium_comments` persist and resume
   3. `--score` in `run.py`
5. Phase 6 pytest. Then a live `--score` run with `GOOGLE_API_KEY` and AWS exports. The live run may take a while because it is 20727 HTTP calls at concurrency 80. Leave the process running. Do not start Step 3 until `already_scored=20727`.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/experiments/test_reddit_curated_perspective_v2.py -q
```

Expected: exit 0 for Step 1 and Step 2 tests.

Live score:

```bash
cd /workspace
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --score
```

Expected: exit 0, `medium_rows=20727`, and a scores parquet with 20727 distinct ids. A second `--score` prints `newly_scored=0`.

## Must fail / not happen

- Direct `get_toxicity_prob` calls that skip `ThreadPoolBatchEngine`.
- Scoring comments whose LLM toxicity tier is not medium.
- Writes to product campaign prefixes or to `mirrorview.parquet`.
- Using Perspective `toxicity_tier` as the rank key.
- Live Perspective calls in unit tests.
