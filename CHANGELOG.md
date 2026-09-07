# CHANGELOG

## 2026-09-06

1. Operators can compare Amazon Nova Micro on Bedrock Converse with the OpenAI Batch runs that label posts as news, opinion, or neither. A smoke run, the matching size jobs, and the matching process jobs now record throughput and estimated cost, and live feature generation still uses OpenAI. [PR #212](https://github.com/METResearchGroup/mirrorView-task/pull/212)
2. A dated Mirrorview Twitter ingest config and a recent-search run (6,901 unique posts inside the 7-day window) are now in the repo. `posts.csv` is stored in Git LFS. [PR #213](https://github.com/METResearchGroup/mirrorView-task/pull/213)
3. Twitter preprocess on that dated collection kept 6,374 of 6,901 posts. The preprocessed `posts.csv` is stored in Git LFS. [PR #215](https://github.com/METResearchGroup/mirrorView-task/pull/215)
4. Pipeline storage now reads and writes the `mirrorview-experimental-artifacts` S3 bucket by default, and `DATA_PLATFORM_STORAGE_BACKEND=local` switches a developer back to local disk. The 25 parquet files of the pinned Bluesky dataset are no longer tracked by git or Git LFS, while its JSON manifests stay in git, and every test is pinned to local disk and a fake bucket so the suite cannot touch production. [Issue #183](https://github.com/METResearchGroup/mirrorView-task/issues/183)
