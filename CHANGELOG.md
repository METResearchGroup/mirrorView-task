# Changelog

## 2026-07-20

1. Add experiment-scoped tooling to upload allowlisted `experiments/**/*.csv` and `*.json` to S3 bucket `mirrorview-experimental-artifacts` with path-preserving keys, SQLite-tracked status (discover → upload → verify), dry-run modes, and explicit failed retry — local files are **not** deleted. ([PR #TBD](https://github.com/METResearchGroup/mirrorView-task/pull/TBD))
