# Step 2: Say Reddit ingest stores comments, not submissions

## Goal

Operator docs should say Reddit raw ingest writes a comments file. PRAW submissions are how comments are fetched, not a stored record type.

## Caller / unit of work

**Main caller:** an operator reading:

- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`
- `/workspace/data_platform/README.md`

**Task:** replace wording that says Reddit raw runs write both `posts.csv` and `comments.csv`.

**Out of scope:** Historical plan packets under `/workspace/docs/plans/**`. Product code. Experiments. Dump ingest docs beyond a one-line clarification that PRAW ingest is comments only. `CHANGELOG.md` during implementation.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-03_reddit_comments_only_ingest_9b3a71/plan.md` | Parent plan |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Platform table currently says Reddit raw output is `posts.csv` and `comments.csv` |
| `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` | Layout line `posts.csv or comments.csv`. Stage 1 is empty. Preprocess already says comments only |
| `/workspace/data_platform/README.md` | Reddit ingestion output path does not name the file. Confirm it does not imply both files |
| `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` | Confirm whether it names Reddit `posts.csv`. Do not edit unless it claims Reddit writes posts |

## Files allowed to change

- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`
- `/workspace/data_platform/README.md` only if it currently implies Reddit writes both files

Plan package files under `/workspace/docs/plans/2026-09-03_reddit_comments_only_ingest_9b3a71/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/docs/plans/**` except git commits of this work
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/models/**`
- `/workspace/data_platform/utils/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md` during implementation
- Any file outside the allowed list, except git commits of this work

## Decision (locked)

Use the same words as the issue. Reddit ingest is comments. PRAW submissions are navigation. Bluesky and Twitter still write `posts.csv`. Do not invent a migration story for leftover historical `posts.csv` beyond "old Reddit raw runs may still have unused leftover files."

## Contracts to lock

In `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`, the platform-differences table Reddit raw output cell is `raw/<timestamp>/comments.csv` (or parquet). It is not `posts.csv` and `comments.csv`.

In `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`:

- The layout line may still say Bluesky and Twitter use `posts.csv` and Reddit uses `comments.csv`.
- Stage 1 must say Reddit ingest writes comments. PRAW listings and comment forests are fetch only.
- Do not claim Reddit ingest writes `posts.csv`.

`/workspace/data_platform/README.md` Reddit ingestion row may name `comments.csv` under the raw timestamp directory. Do not list a Reddit `posts.csv`.

## Test design

Docs only. No new pytest. Proof is the three files no longer say Reddit raw ingest writes `posts.csv`.

```text
given DATA_INGESTION_PIPELINE_ARCHITECTURE.md platform table
then Reddit raw output is comments.csv or comments.parquet
and it does not list posts.csv for Reddit

given HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md
then Reddit ingest is described as comments
and PRAW submissions are described as navigation or fetch handles
```

## Implementation notes (implement-from-spec)

Docs-only step. One commit after the edits. Do not change product code.

1. Phase 1 scope. Confirm the three files. No product-code commit.
2. Skip scaffold, contracts, and failing tests. There is no runtime caller.
3. Phase 5, one unit: edit the allowed docs so Reddit raw output is comments only.
4. Phase 6. Grep the allowed files for Reddit `posts.csv` claims. The architecture table must not pair Reddit with `posts.csv`.

## Must pass

```bash
cd /workspace
rg -n "posts.csv" docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md data_platform/README.md
```

Expected: any remaining `posts.csv` hits are Bluesky or Twitter, or generic layout examples that are not Reddit-specific. The architecture platform table Reddit cell does not contain `posts.csv`.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ -q
```

Expected: exit 0. This is a regression check after step 1. Do not change tests in this step.

## Must fail / not happen

- Historical `docs/plans/**` edited.
- Product code edited.
- Bluesky or Twitter described as comments-only.
- Dump ingest documented as implemented.
