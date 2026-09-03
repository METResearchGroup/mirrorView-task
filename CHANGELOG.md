# Changelog

This file contains the changelog for this repo. We track all notable
changes here, including those that do not correspond to a GitHub issue.

## 2026-09-03
- 1. Reddit monthly comment dumps from the Pushshift experiment can be filtered, sampled to 500,000 comments per month, and stored as git LFS parquet using the same comment fields as live Reddit ingest. [PR #153](https://github.com/METResearchGroup/mirrorView-task/pull/153)
- 2. The Reddit ingest `created_utc` field is renamed to `created_at` and stored as a UTC timestamp. [PR #158](https://github.com/METResearchGroup/mirrorView-task/pull/158)
- 3. The Reddit ingest CLI now accepts `--subreddits` with comma-separated names. [PR #160](https://github.com/METResearchGroup/mirrorView-task/pull/160)
- 4. The Bluesky ingest CLI now accepts `--handles` with comma-separated handles. [PR #151](https://github.com/METResearchGroup/mirrorView-task/pull/151)
- 5. The ingest CLIs now print each saved parquet path after a successful run. [PR #150](https://github.com/METResearchGroup/mirrorView-task/pull/150)
- 6. The live Reddit ingest comment row now stores only `comment_fullname`, `record_id`, `author`, `body`, `created_at`, and `sync_timestamp`. [PR #148](https://github.com/METResearchGroup/mirrorView-task/pull/148)
- 7. The live ingest CLIs now default `--output-dir` to `data_platform/ingestion/data/raw/<platform>` under the repo root. [PR #145](https://github.com/METResearchGroup/mirrorView-task/pull/145)
- 8. The live ingest CLIs now write one parquet file per run instead of JSONL. [PR #138](https://github.com/METResearchGroup/mirrorView-task/pull/138)
- 9. The `sync_timestamp` field is now UTC ISO-8601 with a `Z` suffix to match `created_at`. [PR #144](https://github.com/METResearchGroup/mirrorView-task/pull/144)
- 10. The ingest CLIs now fail fast when a required API credential is missing. [PR #143](https://github.com/METResearchGroup/mirrorView-task/pull/143)
- 11. The ingest CLI `--max-posts` default is now 100, and 0 still means no limit. [PR #154](https://github.com/METResearchGroup/mirrorView-task/pull/154)
- 12. The ingest CLIs now fail fast when `--max-posts` is negative. [PR #159](https://github.com/METResearchGroup/mirrorView-task/pull/159)

## 2026-09-02
- 1. The live ingest CLIs now write one JSONL file per run instead of one file per post. [PR #142](https://github.com/METResearchGroup/mirrorView-task/pull/142)
- 2. The live ingest CLIs now always overwrite the existing output file. [PR #137](https://github.com/METResearchGroup/mirrorView-task/pull/137)
- 3. The ingest CLIs now require `--max-posts`. [PR #141](https://github.com/METResearchGroup/mirrorView-task/pull/141)
- 4. The ingest CLIs now write `record_id` as `{platform}_{post_id}` on every row. [PR #140](https://github.com/METResearchGroup/mirrorView-task/pull/140)
- 5. The ingest CLIs now write the same fields on post rows and comment rows. [PR #136](https://github.com/METResearchGroup/mirrorView-task/pull/136)
- 6. The ingest CLIs now write a UTC `sync_timestamp` on every row. [PR #135](https://github.com/METResearchGroup/mirrorView-task/pull/135)

## 2026-09-01
- 1. The ingest CLIs now fail if `--output-dir` is missing. [PR #133](https://github.com/METResearchGroup/mirrorView-task/pull/133)
- 2. The ingest CLIs now take `--output-dir` as a required flag. [PR #132](https://github.com/METResearchGroup/mirrorView-task/pull/132)
- 3. The ingest CLIs now write `created_at` as UTC ISO-8601 with a `Z` suffix. [PR #131](https://github.com/METResearchGroup/mirrorView-task/pull/131)
- 4. The ingest CLIs now write only the fields we use in analysis. [PR #130](https://github.com/METResearchGroup/mirrorView-task/pull/130)
- 5. The ingest CLIs now write JSONL instead of CSV. [PR #129](https://github.com/METResearchGroup/mirrorView-task/pull/129)
- 6. The ingest CLIs now write one CSV file per post. [PR #128](https://github.com/METResearchGroup/mirrorView-task/pull/128)
- 7. The ingest CLIs now take `--output-dir` as a flag. [PR #127](https://github.com/METResearchGroup/mirrorView-task/pull/127)
- 8. The ingest CLIs now write CSV instead of printing to stdout. [PR #126](https://github.com/METResearchGroup/mirrorView-task/pull/126)

## 2026-08-31
- 1. Added live ingest CLIs for Bluesky, Reddit, and X. [PR #125](https://github.com/METResearchGroup/mirrorView-task/pull/125)
- 2. Added a `data_platform/` package for platform ingest. [PR #124](https://github.com/METResearchGroup/mirrorView-task/pull/124)
- 3. Added a shared `record_id` helper for ingest rows. [PR #123](https://github.com/METResearchGroup/mirrorView-task/pull/123)
- 4. Added shared UTC timestamp helpers. [PR #122](https://github.com/METResearchGroup/mirrorView-task/pull/122)
- 5. Added a shared environment-variable loader. [PR #121](https://github.com/METResearchGroup/mirrorView-task/pull/121)
- 6. Added a shared filesystem helper. [PR #120](https://github.com/METResearchGroup/mirrorView-task/pull/120)
- 7. Added a shared logging helper. [PR #119](https://github.com/METResearchGroup/mirrorView-task/pull/119)

## 2026-08-30
- 1. Initial commit. [PR #118](https://github.com/METResearchGroup/mirrorView-task/pull/118)
