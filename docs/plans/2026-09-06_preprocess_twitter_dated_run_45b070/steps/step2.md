# Step 2: Commit the preprocessed csv through Git LFS

## Goal

Commit the preprocessed run from step 1. Store `posts.csv` as a Git LFS pointer. Store `metadata.json` as an ordinary git file. Record the run in the changelog and in the architecture runbook sentence that already names this dated Twitter dataset.

## Caller / unit of work

**Main caller:** git add, git commit, and `git lfs ls-files` for `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/<timestamp>/`.

**Task:** confirm the new csv is not gitignored, confirm Git LFS tracks it through the existing csv rule from pull request 213, commit the run plus the changelog and architecture-runbook line.

**Out of scope:** Re-running preprocess. Changing Git LFS rules unless `git check-ignore` proves the csv is ignored. Feature generation. Curation. S3. Editing preprocess Python.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-06_preprocess_twitter_dated_run_45b070/steps/step1.md` | Preprocessed run that must already exist |
| `/workspace/.gitattributes` | Existing csv Git LFS rule for this dataset |
| `/workspace/.gitignore` | Dataset exceptions from pull request 213 |
| `/workspace/CHANGELOG.md` | 2026-09-06 already has the raw ingest line from pull request 213 |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Sentence that already allows this dated Twitter run |

## Files allowed to change

- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`

Do not rewrite plan files during implementation.

`.gitignore` and `.gitattributes` stay unchanged unless `git check-ignore` or `git lfs track` proves the existing pull request 213 rules miss the preprocessed csv. If that happens, add the smallest extra exception or LFS pattern that matches the raw csv rules, and say so in the commit message.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/**`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- Any file outside the allowed list, except git commits of this work and a tracking fix described above

## Decision (locked)

Do not add a new Git LFS parquet rule. This dataset is csv. Reuse `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**/*.csv`.

Do not un-ignore other Twitter datasets.

`CHANGELOG.md` under `## 2026-09-06` gets one new numbered item after the pull request 213 raw ingest line. Wording must say this dataset now has a preprocessed `posts.csv` in Git LFS. Do not claim a sample size.

In `docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`, the sentence that currently says the dated Mirrorview Twitter run is allowed and that its `posts.csv` is stored with Git LFS must also say the preprocessed `posts.csv` is stored with Git LFS. Do not add a new section.

## Commands

From the repo root, with `PREPROCESSED_RUN` set to the timestamp directory from step 1 stdout:

```bash
git check-ignore -v \
  "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/posts.csv" \
  "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/metadata.json"
```

Expected: no output, exit 1. If either path is ignored, add the missing `.gitignore` exception before `git add`.

```bash
git add \
  "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/posts.csv" \
  "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/metadata.json" \
  CHANGELOG.md \
  docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md
```

```bash
git lfs ls-files --name-only | grep "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/.*/posts.csv"
```

Expected: the new `posts.csv` path is listed.

```bash
git show :data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/posts.csv | head -n 1
```

Expected: `version https://git-lfs.github.com/spec/v1`

```bash
git show :data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/${PREPROCESSED_RUN}/metadata.json | head -n 5
```

Expected: ordinary JSON starting with `{`, not a Git LFS pointer.

Commit with a message that names the dataset id, the preprocessed timestamp, the kept row count, and Git LFS.

## Tests that must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_preprocess_twitter.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Expected: exit 0, with no new failures.

## Pass / fail

Pass when:

- The preprocessed `posts.csv` is committed as a Git LFS pointer.
- The preprocessed `metadata.json` is committed as ordinary git and still shows `source_raw_runs` of `raw/2026_09_06-19:05:35`.
- `CHANGELOG.md` and `docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` name the preprocessed csv.
- Other Twitter datasets stay gitignored.
- Preprocess and ingest Python are unchanged.

Fail if:

- `posts.csv` is committed as a full csv blob without Git LFS.
- `metadata.json` is stored as Git LFS.
- A parquet file is added.
- `.gitignore` is widened to all of `data_platform/data/twitter/`.
