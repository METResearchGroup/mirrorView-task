# Step 3: Deduplicate and embed the candidate features

Step 3 turns the 320 mining rows into one row per distinct feature, and it embeds each distinct feature with Amazon Titan. The main caller is `main` in `experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/run.py`.

Out of scope are clustering, language model calls, and any change to `shared/embeddings/`.

## Decisions

Flatten each mining row into one record per feature string. A record has `batch_id`, `side`, `category`, `position`, and `text`. `side` is `kept` for `features_from_kept_posts` and `removed` for `features_from_removed_posts`, and `position` is the index of the string in its list.

The duplicate key for a feature is the text after these changes, in this order:

1. Lowercase the text.
2. Take the tokens that match the regular expression `[a-z0-9']+`, which also drops punctuation.
3. Drop tokens that are in `sklearn.feature_extraction.text.ENGLISH_STOP_WORDS`.
4. Join the remaining tokens with one space.

When no tokens are left, the key is the lowercased and stripped text. Two records are duplicates when they have the same `category` and the same key. A string that appears in two categories stays as two features, because step 4 clusters each category on its own.

Each distinct feature keeps the text of its first record, in the order of `batch_id`, then `side`, then `position`. It also keeps these counts:

- `n_occurrences`, the number of records
- `n_batches`, the number of distinct batches
- `n_kept_side` and `n_removed_side`, the number of records on each side
- `batch_ids`, the sorted list of distinct batch ids

The `feature_id` is the category, two underscores, and the row number within the category padded to 5 digits, for example `lexical__00012`. Rows are sorted by `category` and then by key.

Embed the kept text with `create_embedding` from `shared/embeddings/bedrock.py`. `create_embedding` uses `amazon.titan-embed-text-v2:0` with 256 dimensions and unit length. Run 8 calls at a time in a thread pool. `create_embedding` has no retry, so retry a `botocore.exceptions.ClientError` whose code is `ThrottlingException` up to 3 more times, waiting 1, 2, and 4 seconds. Any other error stops the run.

Titan is an embedding model, not a language model, so step 3 has no smoke test. The run prints the Titan token total and the cost at $0.02 per million tokens.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-29_study_2_llm_feature_extraction_863f17/plan.md` | Parent plan |
| `/workspace/shared/embeddings/bedrock.py` | `create_embedding`, `BEDROCK_MODEL_ID`, `EMBEDDING_DIMENSIONS` |
| `/workspace/shared/feature_discovery/llm_based/embed_features.py` | The earlier embedding output layout of `embeddings.npy` with `feature_ids.json` |
| `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/schemas.py` | `CandidateFeatureRow` |

## Files allowed to change

All paths are under `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/`.

- Edit `shared/constants.py` to add the constants in the Contracts section
- Create `src/step3_embed_features/__init__.py`, `dedupe.py`, `embed.py`, and `run.py`
- Edit `SETUP.md` to add the step 3 command, and edit `RESULTS.md` under `## Step 3: deduplicated features`

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/**`

## Contracts

Add to `shared/constants.py`:

```text
SIDE_KEPT = "kept"
SIDE_REMOVED = "removed"
EMBED_MAX_WORKERS = 8
EMBED_THROTTLE_BACKOFF_SECONDS = (1.0, 2.0, 4.0)
TITAN_USD_PER_MILLION_TOKENS = 0.02
FEATURES_KEY = "step3_embed_features/features.parquet"
EMBEDDINGS_KEY = "step3_embed_features/embeddings.npy"
FEATURE_IDS_KEY = "step3_embed_features/feature_ids.json"
```

`src/step3_embed_features/dedupe.py`:

```text
flatten_candidate_rows(rows: list[dict]) -> pd.DataFrame
  Columns batch_id, side, category, position, text. Drop strings that are empty after strip.

normalize_feature_text(text: str) -> str
  The four changes in the Decisions section.

dedupe_features(flat: pd.DataFrame) -> pd.DataFrame
  Columns feature_id, category, text, normalized_text, n_occurrences, n_batches,
  n_kept_side, n_removed_side, batch_ids.
```

`src/step3_embed_features/embed.py`:

```text
embed_one_with_retry(text: str, embed_fn: Callable[[str], dict],
                     sleep_fn: Callable[[float], None]) -> dict
embed_texts(texts: list[str], embed_fn: Callable[[str], dict],
            sleep_fn: Callable[[float], None], max_workers: int) -> tuple[np.ndarray, int]
  Return the (n, 256) float64 matrix in input order and the total input_text_token_count.
  Raise ValueError when a vector does not have EMBEDDING_DIMENSIONS values.
```

`src/step3_embed_features/run.py` has `main()`. It downloads `CANDIDATE_FEATURES_KEY`, runs `flatten_candidate_rows`, `dedupe_features`, and `embed_texts` with `create_embedding`, `time.sleep`, and `EMBED_MAX_WORKERS`. It writes `FEATURES_KEY`, `EMBEDDINGS_KEY`, and `FEATURE_IDS_KEY`, where `feature_ids.json` lists `feature_id` in matrix row order, uploads all three, and prints one line.

## Commands

```bash
PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step3_embed_features/run.py
```

The run prints this line, where `M` is the flattened record count, `D` is the distinct feature count, `T` is the Titan token total, and `C` is the cost in dollars:

```text
candidate_records=M distinct_features=D titan_tokens=T titan_cost_usd=C
```

`M` equals the `N` that step 2 printed. Write a table of distinct features per category and the four numbers in the printed line under `## Step 3: deduplicated features` in `RESULTS.md`.

## Pass

`M` equals the step 2 count, `D` is at most `M`, `embeddings.npy` has `D` rows and 256 columns, and all three files are on S3.

## Fail

The step fails when `feature_ids.json` does not match the row order of `features.parquet`, or when any vector does not have length 256.
