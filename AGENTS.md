# AGENTS.md

## Cursor Cloud specific instructions

This repo has two loosely-coupled parts that are developed independently:

1. **jsPsych web experiment** (`public/`, `lambda-*.mjs`) — the participant-facing "MirrorView" content-moderation task. Production is fully serverless (static assets on S3 + API Gateway + Lambdas).
2. **Python data-analysis / ML tooling** (`pyproject.toml`, `scripts/`, `jobs/`, `lib/`, `experiments/`) — offline scripts managed with **uv** (Python 3.12).

The update script already runs `npm install` and `uv sync` on startup, so dependencies are ready. `uv` is installed at `~/.local/bin` and is on `PATH` in interactive shells.

### Running the web experiment locally (non-obvious)

- **`npm run dev` / `npm start` are broken**: `package.json` and `README.md` reference `server-local.js` (and `index-local.html` / `main-local.js`), but **those files do not exist in the repo**. Do not rely on them.
- The frontend is pure static files. Serve `public/` with any static server, e.g.:
  `python3 -m http.server 3000 --directory public`
  then open `http://localhost:3000/index.html?PROLIFIC_PID=TEST123`.
- On load the experiment calls the **live** AWS API Gateway (`public/config.js`) to fetch assigned post IDs. That endpoint is public and reachable without AWS credentials.
- The browser then maps those IDs to a **local stimulus catalog** at `public/img/flips_scaled_2026_06_18.csv`. This file is **not in git** (it is an S3 deploy asset, and `*.csv` is gitignored). Without it the experiment shows an "Assignment Error" ("unknown post IDs") after the political-affiliation step. Create it from the in-repo source-of-record (see `docs/runbooks/HOW_TO_REPLACE_STIMULI_DATASET.md`):
  `mkdir -p public/img && cp jobs/mirrorview_scaled_2026_06_18/flips.csv public/img/flips_scaled_2026_06_18.csv`
  This is a local data step, not a code change.
- Data-saving on completion (`SAVE_DATA_URL`) writes to the live S3 bucket via Lambda; expected to work for the public endpoint but not required to exercise the core moderation flow.

### Python tooling (non-obvious)

- Always prefix commands with `PYTHONPATH=.` — scripts import repo-root packages (`lib/`, etc.). Example: `PYTHONPATH=. uv run python scripts/export_study_results.py --help`.
- `uv sync` installs the `dev` dependency group by default (torch/transformers/spacy — large).
- Tests: `PYTHONPATH=. uv run pytest`. Real tests live in `experiments/fetch_reddit_pushshift_dump_2026_06_15/tests/`.
- `testing/smoke_tests/` is a stub intended to hit the live prod Lambda; it is not a functional local test.
- S3-touching scripts (`scripts/export_study_results.py`, `scripts/upload_to_s3/*`) and Bedrock/Titan calls need AWS credentials (not present by default). See `docs/runbooks/ADDING_NEW_AWS_CREDENTIALS.md`. LLM/experiment scripts read API keys from a repo-root `.env` (`lib/load_env_vars.py`: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `WANDB_API_KEY`).

### Lint / test

- No linter is configured (no ruff/flake8/eslint config).
- `npm test` is a placeholder that exits 1; there are no JS tests.
