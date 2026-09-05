# AGENTS.md

## Conventions

Follow the conventions defined in https://github.com/mark-torres10/ai_tools/blob/main/conventions/vocabulary.md.

## Cursor Cloud specific instructions

The install step verifies that `uv` is available (`uv --version`) and then provisions the Python environment with `uv sync --frozen`, so `.venv` is ready and `uv run pytest` works without extra setup

For verification, just set up the `uv` environment and run the `pytest` scripts. Successful execution of that means that the environment build works.

### Secrets / environment variables

- `METRESEARCHGROUP_GITHUB_PAT_TOKEN` — the personal access token (PAT) used for accessing GitHub (e.g. authenticated `git`/API operations against `github.com/METResearchGroup`).

### AWS credentials

The repo's boto3 clients (`lib/aws/`, `scripts/export_study_results.py`, etc.) use the default credential chain. Don't set an AWS profile here. Instead, IAM user credentials are provided as `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`. boto3 and the AWS CLI do not read those prefixed names, so export them as the standard variables before running any AWS-touching code:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

### Python tooling (non-obvious)

- Always prefix commands with `PYTHONPATH=.` — scripts import repo-root packages (`lib/`, etc.). Example: `PYTHONPATH=. uv run python scripts/export_study_results.py --help`.
- `uv sync` installs the `dev` dependency group by default (torch/transformers/spacy — large).
