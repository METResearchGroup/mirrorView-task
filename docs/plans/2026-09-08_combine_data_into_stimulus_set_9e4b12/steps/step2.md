# Step 2: Run the command and write RESULTS.md

## Scope

- **Caller:** the same `run.py` `main` from Step 1.
- **Task:** Export AWS credentials, run the combine command, confirm local and S3 parquet, copy logs to `/opt/cursor/artifacts/`, and commit `RESULTS.md` with the two crosstab tables filled from the live run.
- **Out of scope:** pytest, editing product curate files, changing pinned source objects, rewriting Step 1 modules except docstring fixes required by `write-docstring`.

## Files to inspect (read-only)

- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/run.py`
- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/RESULTS.md`
- `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/wide_run_report.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/wide_run_report.md`
- `/workspace/docs/plans/2026-09-08_join_twitter_llm_curate_19e01b/reports/wide_run_report.md`
- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/RESULTS.md`

## Files allowed to change

- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/RESULTS.md` (written by the live command, then committed)
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/README.md` (command and expected stdout only, if Step 1 left placeholders)

## Files forbidden to change

- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/curate/configs/**`
- `/workspace/tests/**`
- `/workspace/experiments/reddit_curated_perspective_v2_2026_09_08/**`
- The four source S3 objects
- `/workspace/docs/plans/2026-09-08_combine_data_into_stimulus_set_9e4b12/**`

## Live commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py
```

Expected stdout includes `combined_rows=55573`, a local path under `experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet`, `dataset_sha256=`, and two JSON tables.

```bash
aws s3 cp s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet /tmp/combine_stimulus_dataset.parquet
PYTHONPATH=. uv run python - <<'PY'
import hashlib
from pathlib import Path
import pyarrow.parquet as pq

local = Path("experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet")
downloaded = Path("/tmp/combine_stimulus_dataset.parquet")
want = [
    "integration",
    "source_dataset_id",
    "source_curated_run",
    "record_id",
    "source_record_id",
    "platform_id",
    "author_handle",
    "text",
    "created_at",
    "sync_timestamp",
    "news_or_opinion_category",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tier",
]
table = pq.read_table(downloaded)
assert table.column_names == want, table.column_names
assert table.num_rows == 55573
assert hashlib.sha256(local.read_bytes()).hexdigest() == hashlib.sha256(downloaded.read_bytes()).hexdigest()
print("combined ok", table.num_rows, len(table.column_names))
PY
```

Expected: `combined ok 55573 17`.

Also list the prefix:

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/experiments/combine_data_into_stimulus_set_2026_09_08/
```

Expected listing includes `dataset.parquet`.

Copy command stdout, the parquet assertion, and the S3 listing to `/opt/cursor/artifacts/`.

## RESULTS.md

`RESULTS.md` must include:

- The four source URIs, SHA-256 values, and row counts
- Combined row count 55573
- Combined parquet local path, S3 URI, and SHA-256
- Overall political stance by LLM toxicity tier table (`left`/`right` by `low`/`medium`/`high`, with totals)
- The three-platform table with `integration`, `political_stance`, `low`, `medium`, `high`, `total`
- The exact rerun command

Twitter rows from both collections must sit in the Twitter group of the three-platform table. Bluesky counts in that table must match the Bluesky wide-run report (9756 rows). Reddit counts must match the v2 report (43061 rows, with 3000 medium comments moved to high). Twitter counts must equal 1457 + 1299 = 2756.

Sanity check against source reports before committing RESULTS.md:

| Platform | left low | left medium | left high | right low | right medium | right high | total |
|----------|---------:|------------:|----------:|----------:|-------------:|-----------:|------:|
| bluesky | 3563 | 4179 | 585 | 529 | 755 | 145 | 9756 |
| reddit v2 | 13423 | 12632 | 3056 | 7998 | 5095 | 857 | 43061 |
| twitter 1 | 563 | 142 | 12 | 392 | 279 | 69 | 1457 |
| twitter 2 | 512 | 118 | 9 | 342 | 245 | 73 | 1299 |

Twitter combined: left 1075 / 260 / 21, right 734 / 524 / 142, total 2756.

Overall: left 18061 / 17071 / 3662, right 9261 / 6374 / 1144, total 55573.

If a live cell disagrees with this table, stop. Do not invent numbers.

## Must pass

- Live command exits 0 on the first run.
- `combined ok 55573 17`.
- S3 object exists and matches local SHA-256.
- RESULTS.md tables match the sanity-check totals above.
- Source S3 objects are unchanged.

## Must fail

- A second run that tries to `put_new` the same S3 key (expected `FileExistsError`). Do not treat that as a product bug.
- Any change to product curate scripts.

## Implement-from-spec notes

This step is a live run, not new product logic. Do not add pytest. After a green run, commit RESULTS.md. Apply `write-docstring` only if Step 1 docstrings are incomplete, as a separate commit.
