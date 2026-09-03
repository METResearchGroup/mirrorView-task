# Run every feature generator on 500,000 posts

## TL;DR

The operator can already resume an unfinished feature folder, and skip posts that already have labels. Each feature writes one CSV or parquet file. A 500,000 post run will still fail in the ways that matter for a job that lasts a day or more.

The operator must run every LLM feature and the Perspective toxicity feature, one after another, on every remaining unlabeled post. At 500,000 posts that is about 3 million LLM calls and 500,000 Perspective calls. Public list prices for `gpt-5.4-nano` put the LLM bill around $200 to $500 if retries stay rare. Wall time is likely a full day for the LLM features if concurrency stays near 64. Toxicity takes much longer if the Perspective quota is near 1 request per second.

The run cannot finish after a single failed batch, because `failed_batches` never goes back to 0. Bluesky curation also requires a completed feature run. When the API is down, the process does not stop. It writes failed batches to deadletter (a log of batches that exhausted every retry) until the feature is done failing. A crash while appending parquet can wipe the labels already written for that feature. Git LFS is the right store for the dump inputs, and the wrong store for live feature outputs.

Do the following first, in this order:

- Stop the process after a streak of failed batches, and leave the feature run unfinished so `--checkpoint` can continue it.
- Let a feature complete once every post has a label, even if an earlier batch had failed and was later retried.
- Write labels in a crash-safe append form (JSON lines, or a temp file that replaces the output).
- Load the skip set for the current feature file once, and keep it in memory.
- Add a deadletter replay command.
- Copy dump parquet into a real `data_platform/data/` dataset before you try to label 500,000 comments. The dump files are not in that pipeline yet.

## Purpose

The last few merged pull requests built a local, resumable pipeline. They did not yet make feature generation safe for a 500,000 post run.

Recent work, in pipeline order:

- Live Reddit ingest now writes comments only ([PR #151](https://github.com/METResearchGroup/mirrorView-task/pull/151)).
- Ingest, preprocess, and feature skip share one skip-set session ([PR #144](https://github.com/METResearchGroup/mirrorView-task/pull/144)).
- Preprocess is a shared runner with standardized columns, and it drops posts already used as study stimuli ([PR #154](https://github.com/METResearchGroup/mirrorView-task/pull/154), [PR #158](https://github.com/METResearchGroup/mirrorView-task/pull/158)).
- Feature generation refuses to start until every preprocessed run is complete ([PR #160](https://github.com/METResearchGroup/mirrorView-task/pull/160)).
- Feature generation resumes with `--checkpoint`, and it will not start a second unfinished folder ([PR #159](https://github.com/METResearchGroup/mirrorView-task/pull/159), [PR #161](https://github.com/METResearchGroup/mirrorView-task/pull/161)).
- Reddit Pushshift dumps are filtered to 500,000 comments per month and stored as Git LFS parquet ([PR #153](https://github.com/METResearchGroup/mirrorView-task/pull/153)).
- A Bluesky Jetstream day dump is also in Git LFS ([PR #135](https://github.com/METResearchGroup/mirrorView-task/pull/135)).

The dump sample size in `data_platform/ingestion/data_dumps/reddit/filtered/` is 500,000 comments per month. May and June each have 500,000 comments. A single feature run that labels one of those months is the scale the rest of the writeup plans for. Labeling both months in one folder would be 1,000,000 comments, and the same failure modes apply.

The dump parquet files are not a `dataset_id` under `data_platform/data/` yet. Feature generation still reads preprocessed runs from `data_platform/data/{platform}/{dataset_id}/preprocessed/`. Getting dump comments into that layout is a separate cluster below. Later sections assume the posts have already landed there.

## How feature generation works today

The operator runs a platform script such as `data_platform/generate_features/generate_reddit_features.py`. Shared logic lives in `data_platform/generate_features/platform_cli.py` and `data_platform/generate_features/generate_features.py`.

The happy path is:

1. Require every preprocessed run for the dataset to be complete.
2. Load every preprocessed row into one pandas table, and validate each row with the platform Pydantic model.
3. Create `features/{timestamp}/` or continue a named unfinished folder via `--checkpoint`.
4. Loop `FEATURE_REGISTRY` in `data_platform/generate_features/registry.py` in order.
5. For each feature, skip posts that already have a label in any feature folder, using `FeatureLabelQuery` in `data_platform/utils/feature_labels.py`.
6. Label remaining posts in batches (default 64) through LangChain `chain.batch` or a thread pool.
7. Append successful rows to `{feature}.csv` or `{feature}.parquet`.
8. Flush `metadata.json` after every batch.
9. After retries are exhausted, append the failed batch to `deadletter.jsonl` and keep going.
10. Mark the feature completed only when `failed_batches` is 0. Mark the whole run completed only when every stored feature is completed.

`FEATURE_REGISTRY` lists seven features. The LLM features call `gpt-5.4-nano` through LangChain structured output (`is_news_or_opinion`, `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`). The remaining feature calls the Perspective API (`is_toxic_tiered`).

Resume has two layers, and they are easy to mix up. `--checkpoint` chooses the folder. The skip set chooses which rows still need labels. [PR #161](https://github.com/METResearchGroup/mirrorView-task/pull/161) split those jobs. A feature marked `completed` in the current folder is not reopened for new posts. New posts wait for a later run without `--checkpoint`.

## Probe measurements

I ran a local probe of the disk and pandas paths on 500,000 synthetic rows, with no LLM calls. The script is saved with the review artifacts for this pull request. Defaults matched production (`batch_size=64`).

| Path | Result at 500,000 rows |
| ---- | ---------------------- |
| Preprocessed table in memory, short repeated text | 64 MB |
| Skip set of 500,000 ids | 25 MB peak |
| Pydantic round trip like `load_preprocessed_records` | 2.8 s |
| `DataFrame.iterrows` used by `tasks_from_dataframe` | about 21 s (from a 20,000 row sample) |
| Column zip instead of `iterrows` | 1.0 s |
| One feature CSV of id, timestamp, and a bool | 18.9 MB, 0.54 s to write |
| One full CSV id scan (`load_seen_ids_from_disk`) | 0.45 s |
| Current engine, which rereads the whole CSV on every batch | about 1,700 to 1,800 s of extra CPU per feature, because each new batch rereads every row written so far |
| One parquet rewrite of 500,000 label rows (today's append) | 0.16 s and 2.6 MB |
| Parquet rewrite once per batch, growing to 500,000 | about 10 minutes extra per feature, and a crash can drop the whole file |

RAM is enough for 500,000 rows. API time, API failure handling, and crash-safe writes are what will stop the run.

## Cluster 1. Keeping checkpoint files accurate after a crash

The folder checkpoint from [PR #159](https://github.com/METResearchGroup/mirrorView-task/pull/159) and [PR #161](https://github.com/METResearchGroup/mirrorView-task/pull/161) is the right shape. A 500,000 post run still needs the files inside that folder to stay true after a kill, a reboot, or a disk full error.

### 1a. `failed_batches` makes completion unreachable

`data_platform/generate_features/generate_features.py` refuses to mark a feature completed when `failed_batches` is greater than 0. The counter only increases. `update_batch_counts` in `data_platform/generate_features/metadata.py` never decreases it.

On `--checkpoint` resume, deadlettered ids are unlabeled, so they are tried again. If they succeed, the CSV gains the rows, and the counter still says the feature failed. The run `sync_status` stays unfinished. A new run cannot start, because an unfinished folder already exists. Bluesky curate calls `require_features_complete` and will refuse the dataset.

At 500,000 posts, one 64-post batch that hit a timeout can leave a job that ran all day unable to close.

Proposal:

- Treat `failed_batches` as a count for the current process, not as a permanent flag on the folder.
- Mark a feature completed when every input id has a label row, or when pending ids are only those you have chosen to leave in deadletter on purpose.
- Keep a separate `deadletter_batches` history field if you still want the failure log in metadata.

### 1b. Parquet append can lose the whole feature file

`StorageManager.append_records` in `data_platform/utils/storage.py` handles parquet by reading the existing file, concatenating, and writing the file again. A crash in `to_parquet` can leave a truncated file, or replace a good file with a partial one. CSV append is safer for a crash at the end of the file, and still unsafe in the middle of a batch write, because a half-written row will break `csv.DictReader` on resume.

Pick one of the following and use it for every feature file:

- Write each successful batch as a JSON lines file (`{feature}.jsonl`), and build the CSV or parquet once when the feature completes.
- Or write `{feature}.csv.{batch}.tmp`, fsync, then append in a small helper that copies to a new file and replaces the output with `Path.replace`.
- Stop rewriting a growing parquet file on every batch of 64.

JSON lines matches how `deadletter.jsonl` already works, and it is a simple crash-safe append.

### 1c. In-flight LLM work is billed and then thrown away

`LangChainBatchEngine.batch_label_records` in `data_platform/generate_features/engines/langchain_engine.py` calls `chain.batch` on the whole chunk. If one of 64 items raises after the provider billed the other 63, the batch retry runs the whole chunk again. If retries end, all 64 ids go to deadletter, including posts that already had a valid label in memory.

`ThreadPoolBatchEngine` in `data_platform/generate_features/engines/thread_pool_engine.py` has the same shape. `executor.map` raises on the first worker error, and the successful worker results in that batch are not written.

Proposal:

- For LangChain, pass `return_exceptions=True` (or the current LangChain equivalent), write the successful rows, and deadletter only the failed ids.
- For the thread pool, collect per-future exceptions the same way.
- Shrink the default batch if you want fewer posts lost per failed batch while that change is pending. 16 is a safer default than 64 for a first 500,000 run. Concurrency can stay at 64 or 80.

### 1d. Empty folder with no `metadata.json` can get stuck

`feature_run_dir` can create `features/{timestamp}/` before `init_feature_run_metadata` writes `metadata.json`. A crash in that window leaves a folder that counts as unfinished. `--checkpoint` on that folder then calls `load_feature_run_metadata`, which raises `FileNotFoundError`. Starting a new run also raises, because the empty folder is unfinished.

Proposal:

- If `--checkpoint` points at a folder with no `metadata.json`, call `init_feature_run_metadata` instead of load.
- Or write `metadata.json` before returning from `create_new_run_dir` for feature runs.

### 1e. Metadata labeled counts can drift from the file

A crash after `append_records` and before `on_batch_complete` leaves rows on disk and a stale `labeled` count. Resume still skips those ids, so labels are not redone. The count in metadata is wrong, and completion uses that count.

Proposal:

- On resume, set `labeled` from a count of rows (or distinct ids) in the feature file.
- Use metadata as a cache, and treat the feature file as the source of truth.

## Cluster 2. Stopping after repeated failures, and replaying deadletter

A circuit breaker here means a rule that stops the process after repeated failures, instead of continuing through the rest of the posts and the rest of the features.

Ingest already retries only transient errors, in `data_platform/ingestion/retry.py`. Perspective scoring does the same in `ml_tooling/perspective_api.py` (HTTP 429 and 5xx). Feature LLM retries do not.

`retry_llm_completion` in `data_platform/generate_features/llm_retry.py` retries every `Exception`, 3 times, with a cap of 60 seconds of backoff. After that, `label_records` in `data_platform/generate_features/engines/base.py` writes the batch to deadletter and continues. There is no stop after a streak of failures. There is no replay command for `deadletter.jsonl`.

At 500,000 posts, an OpenAI outage or a bad API key produces about 7,812 failed batches per LLM feature. Each failed batch still pays for 4 attempts (the first try plus 3 retries) before deadletter. The process then starts the next feature and does it again.

Proposal:

- Retry only timeouts, connection errors, and HTTP 429 / 5xx, the way ingest and Perspective already do.
- Honor `Retry-After` when the provider sends it, and cut `max_concurrency` after repeated 429s.
- Stop the process after N consecutive failed batches (start with N=5). Exit nonzero, leave `sync_status` as `in_progress`, and print the `--checkpoint` timestamp. Do not walk the rest of the registry while the provider is down.
- Add a spend cap and a wall-time cap on the CLI, for example `--max-usd` and `--max-hours`, so a retry loop cannot empty the OpenAI account.
- Add `replay_deadletter.py` (or a `--replay-deadletter` flag) that reads `deadletter.jsonl`, rebuilds tasks from the preprocessed table, labels those ids, and removes the JSON lines that succeed.

A circuit breaker is the change that most protects a first 500,000 run. Checkpoint resume only helps if the process is still in a state you are willing to continue.

## Cluster 3. Extra disk reads in the skip set

The skip set is loaded in two places.

`FeatureLabelQuery.filter_unlabeled` loads ids from every `features/{timestamp}/{feature}.csv` (or parquet) at the start of a feature. `filter_seen_tasks` then rereads the current feature file on every batch of 64.

`filter_unlabeled` is the right path for posts already labeled in an earlier folder. `filter_seen_tasks` is only useful for a crash in the current folder, and it does that job by rereading a file that grows on every batch. The probe put that extra cost at about 30 minutes of CPU per feature at 500,000 rows. It will not dominate LLM time, and it will add disk pressure and resume latency for no benefit.

`tasks_from_dataframe` uses `iterrows`, which the probe put at about 21 seconds for 500,000 rows. A column zip is about 1 second. `load_preprocessed_records` builds a Python dict per row and validates it with Pydantic. The probe put that at 2.8 seconds for short text. Real Reddit bodies are longer, so plan for tens of seconds and a few hundred MB, which is still fine.

Proposal:

- Load seen ids for the current feature file once at the start of `label_records`, keep them in a `set`, and add ids after a successful append.
- Replace `iterrows` with a column zip in `tasks_from_dataframe`.
- Optionally load only `id` and `text` columns from preprocessed parquet, and skip the per-row Pydantic round trip inside feature generation (preprocess already validated the rows).

Do not shard the skip set across machines until the in-memory set is the only reader of the current feature file. 500,000 ids in a Python set used 25 MB in the probe.

## Cluster 4. Where outputs live, and why Git LFS is the wrong tool for labels

[PR #153](https://github.com/METResearchGroup/mirrorView-task/pull/153) already uses Git LFS for dump inputs:

- `data_platform/ingestion/data_dumps/reddit/filtered/*.parquet` (about 80 MB each, 500,000 comments)
- Bluesky hourly parquet under `data_platform/ingestion/data_dumps/bluesky/data/parquet/` ([PR #135](https://github.com/METResearchGroup/mirrorView-task/pull/135))

`.gitignore` already ignores `data_platform/data/`, which is where feature runs are written. A 500,000 row feature CSV was 19 MB in the probe. All seven feature files together are about 150 MB of labels, plus deadletter if things go wrong. Disk size is not the problem.

Git LFS is a way to store large files that you want inside the git clone. Live feature outputs are not that. A run that appends 7,812 times should not touch git. A Cloud Agent or laptop clone should not grow a 150 MB LFS object on every retry of a labeling job.

Proposal:

- Keep Git LFS for dump inputs only.
- Keep live feature outputs under `data_platform/data/{platform}/{dataset_id}/features/{timestamp}/`, which is already the checkpoint.
- After each feature completes, copy that feature file plus `metadata.json` to a durable place that is not git. The old S3 upload path was removed from `data_platform/` in [PR #50](https://github.com/METResearchGroup/mirrorView-task/pull/50). If the 500,000 run will last overnight on a machine that can vanish, add a small copy helper (rsync, or a one-shot S3 sync of the run folder) and call it from `on_batch_complete` every N batches, or at feature completion. Do not bring Glue, Athena, or Prefect back for this.
- Do not `git add` anything under `data_platform/data/`.
- If you want a checked-in snapshot of labels for an experiment, copy a completed run into an experiment folder and LFS that copy on purpose, the same way dump parquet is stored in LFS.

## Cluster 5. API cost, quotas, and wall time

The LLM features run one after another. Default `max_concurrency` is 80, and default `batch_size` is 64, so each batch runs up to 64 calls at a time. System prompts in the six LLM files are about 230 to 440 tokens each, and LangChain structured output adds a schema on top of that.

A rough bill at public `gpt-5.4-nano` list prices ($0.20 per million input tokens, $1.25 per million output tokens, $0.02 per million cached input tokens), for 500,000 posts times 6 features:

- Without prompt cache, about $400 to $500 if retries stay rare.
- With prompt cache on the system prompt and schema, about $150 to $250.
- OpenAI Batch API is half those rates, and it does not fit the current `chain.batch` loop unless you redesign the engine around submitted batches and a poll.

Retries, structured-output failures, and an outage that is not stopped by a circuit breaker will multiply that bill. Confirm live prices before you start. The dollar ranges in the list come from August and September 2026 writeups of public list prices, not from an invoice.

Wall time, if one call is about 1.5 seconds and 64 run at once, is about 3 to 4 hours per LLM feature, or about 20 hours for all six, plus toxicity. Toxicity is 500,000 Perspective `comments:analyze` calls. The Perspective client retries 429 and 5xx up to 8 times. Default Google quotas are often near 1 request per second unless a higher quota is approved. At 1 request per second, toxicity alone is about 6 days. At 80 concurrent requests against a 1 request-per-second quota, almost every batch will 429, retry, and go to deadletter.

Proposal:

- Before the 500,000 run, measure one live feature on 1,000 posts. Record tokens in, tokens out, cache hits, 429s, elapsed time, and dollars. Extrapolate. Do not guess from the dollar ranges in this writeup.
- Turn on OpenAI prompt caching if `ChatOpenAI` in `ml_tooling/llm/llm.py` does not already send a stable prefix. The six system prompts are fixed strings, so they should cache.
- Ask Google for a Perspective quota that matches the concurrency you will set. Until that quota exists, run `is_toxic_tiered` with `max_concurrency` near the quota, not 80.
- Keep features sequential in one process for the first 500,000 run. Parallel features on the same folder will overwrite `metadata.json`, because `flush_metadata` replaces the whole file.
- If you later want overlap, give each feature its own run folder, or lock metadata. A simpler first step is to run `--features is_political` to completion, then other features in later runs that continue an unfinished folder. Today a subset run that inits only some names can mark `sync_status` completed while other registry features were never in that folder. Decide whether a completed run means "this folder's listed features" (today) or "the full registry" (what curate implies).

## Cluster 6. Operator workflow for a long run

The current CLI is enough to start and resume, and it is missing the things a job that runs overnight needs.

Proposal:

- Print a start banner with dataset id, run folder, feature list, pending counts per feature, batch size, and concurrency.
- Always write tqdm (or a line every N batches) even when stderr is not a TTY. Cloud logs often are not a TTY, and `label_records` currently disables the bar in that case.
- Write a `progress.jsonl` heartbeat with time, feature name, labeled, failed, pending, last error, and consecutive failures. `metadata.json` already has counts. A log with one JSON object per line is easier to tail.
- Refuse to start if `OPENAI_API_KEY` or `GOOGLE_API_KEY` is missing, before the first batch.
- Document the operator loop in `docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md`: start, watch `metadata.json` and `deadletter.jsonl`, Ctrl-C, `--checkpoint`, replay deadletter, only then curate.
- Do not add preprocess runs to the dataset while a feature run is in progress. On resume, `load_preprocessed_records` loads every preprocessed folder, and `source_preprocessed_runs` is rewritten. Completed features in the current folder will skip the new posts ([PR #161](https://github.com/METResearchGroup/mirrorView-task/pull/161)). In-progress features will label them. The folder then has mixed coverage.

`--features` remains useful when you want to run one generator at a time, for example toxicity after the LLM features. Keep one unfinished folder at a time, which is already the rule.

## Cluster 7. Getting 500,000 dump comments into the pipeline

`data_platform/ingestion/data_dumps/reddit/process_dump.py` writes Git LFS parquet that uses `SyncRedditCommentModel`. Feature generation never reads that directory.

To label those comments you still need:

1. A `dataset_id` and `dataset.json` (csv or parquet format).
2. A complete raw run under `data_platform/data/reddit/{dataset_id}/raw/{timestamp}/`.
3. A complete preprocessed run that adds `text`, `source_record_id`, and `author_handle`, and that applies the current length and English gates.

Preprocess gates from [PR #132](https://github.com/METResearchGroup/mirrorView-task/pull/132) will drop short and non-English comments. The dump README says downstream stages should filter. If the intent is to run every generator on all 500,000 comments, preprocess will not pass 500,000 rows unless those gates are relaxed for dump datasets. That is a product choice, not a performance choice. Make the choice explicit in the command that copies the dump into a raw run.

Proposal:

- Add a dump import command that copies a filtered parquet into a new raw run, writes `metadata.json` with `sync_status: completed`, and writes `dataset.json`.
- Run the existing preprocess CLI on that dataset.
- Then run feature generation.
- Keep dump parquet in Git LFS as the immutable input. The raw and preprocessed copies under `data_platform/data/` are local, like every other dataset.

If you import both May and June into one dataset, feature generation will load 1,000,000 preprocessed rows (minus gates). Prefer one month per dataset for the first scale run.

## What I recommend doing first

Do not shard across machines, and do not put feature CSVs in Git LFS. The current single-folder checkpoint is enough if the folder can finish.

Work in this order:

1. Circuit breaker plus typed LLM retries (Cluster 2). Without this, an outage wastes money and fills deadletter.
2. Completion rules that follow the feature file, not a `failed_batches` counter that never clears (Cluster 1a and 1e).
3. Crash-safe append, JSON lines preferred (Cluster 1b and 1c).
4. In-memory skip set and drop `iterrows` (Cluster 3).
5. Deadletter replay and a progress heartbeat (Cluster 2 and 6).
6. Dump import into `data_platform/data/` and an explicit preprocess-gate decision (Cluster 7).
7. A 1,000 post live measurement, then quota and cache changes (Cluster 5).
8. Optional copy of the run folder to S3 or another disk after each feature (Cluster 4).

After the items in that list are done, a 500,000 post run is start, wait, `--checkpoint` if the machine dies, replay deadletter, then curate. Parallel feature processes and OpenAI Batch API are later optimizations, not prerequisites.

## Limits of the writeup

No code in this pull request changes feature generation. The probe used synthetic rows and did not call OpenAI or Perspective. Live token counts, 429 rates, and dollars need a 1,000 post measurement on the dataset you will actually label.

Curation join via DuckDB in `data_platform/curate/consolidate.py` should handle 500,000 rows. It is not the bottleneck, and it still requires a completed feature run on Bluesky. Fix completion before you worry about the join.
