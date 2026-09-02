# AGENTS.md

## Conventions

Follow the conventions defined in https://github.com/mark-torres10/ai_tools/blob/main/conventions/vocabulary.md.

All current timestamps come from `lib.timestamp_utils.get_current_timestamp`. That helper is UTC. Do not add more timestamp generators.

## Cursor Cloud specific instructions

The startup/update script is intentionally minimal: it only verifies that `uv` is available (`uv --version`) and does **not** install project dependencies. The app does not need to run in this environment. If you need Python deps, run `uv sync` yourself; if you need the web deps, run `npm install` from `webapp/`. `uv` is installed at `~/.local/bin` and is on `PATH` in interactive shells (Python 3.12).

### Secrets / environment variables

- `METRESEARCHGROUP_GITHUB_PAT_TOKEN` — the personal access token (PAT) used for accessing GitHub (e.g. authenticated `git`/API operations against `github.com/METResearchGroup`).
- LLM/experiment scripts read API keys from a repo-root `.env` (`lib/load_env_vars.py`: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `WANDB_API_KEY`). `HF_TOKEN` and AWS role ARNs (`CURSOR_AWS_ASSUME_IAM_ROLE_ARN`, `SAGEMAKER_ROLE_ARN`) are also available as environment secrets.
- Platform ingest (`data_platform/`) also loads from `.env`: `BLUESKY_HANDLE`, `BLUESKY_PASSWORD`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `REDDIT_REDIRECT_URI`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `X_BEARER_TOKEN`, `X_CONSUMER_KEY`, `X_SECRET_KEY`.
- Ingest CLIs: `PYTHONPATH=. uv run python data_platform/...` (e.g. `data_platform/ingestion/sync_bluesky.py`).

### AWS credentials

The repo's boto3 clients (`lib/aws/`, `scripts/export_study_results.py`, etc.) use the default credential chain — they do **not** set a profile explicitly.

- **In the remote Cloud Agent environment, `AWS_PROFILE` is not set.** Instead, IAM user credentials are provided as `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`. boto3 and the AWS CLI do not read those prefixed names, so export them as the standard variables before running any AWS-touching code:
  ```bash
  export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
  export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
  ```
  Verified working via `sts get-caller-identity` (IAM user `mark_iam_credentials`).
- **Locally / outside the remote env**, default to `AWS_PROFILE` (your shared AWS config); the `LAB_*` vars are typically absent there.

### Python tooling (non-obvious)

- Always prefix commands with `PYTHONPATH=.` — scripts import repo-root packages (`lib/`, etc.). Example: `PYTHONPATH=. uv run python scripts/export_study_results.py --help`.
- `uv sync` installs the `dev` dependency group by default (torch/transformers/spacy — large).
- Tests: `PYTHONPATH=. uv run pytest`. Ingest unit tests: `PYTHONPATH=. uv run pytest tests/data_platform`. Other real tests live in `experiments/fetch_reddit_pushshift_dump_2026_06_15/tests/`.
- `webapp/testing/smoke_tests/` is a stub intended to hit the live prod Lambda; it is not a functional local test.
- S3-touching scripts (`scripts/export_study_results.py`, `webapp/scripts/upload_to_s3/*`) need AWS credentials. See the "Secrets / environment variables" section above for the keys available in this environment.

### Lint / test

- No linter is configured (no ruff/flake8/eslint config).
- `npm test` (from `webapp/`) is a placeholder that exits 1; there are no JS tests.
