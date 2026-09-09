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


## Model training

Use HuggingFace for model access and compute. Use the `HF_TOKEN` API key.

### Default open-source LLM

For any experiments, let's default to Qwen3.5 4B. Use [this HuggingFace link](https://huggingface.co/collections/Qwen/qwen35) for more information, and [this link](https://huggingface.co/Qwen/Qwen3.5-4B) for the model weights.

### GPU compute

For GPU compute, use Hugging Face Jobs. See [this guide](https://huggingface.co/docs/huggingface_hub/en/guides/jobs) for more details.

### Storage

By default, use S3 for storage. Use the AWS access key and secret login, via `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`, renaming it as needed.

Err on the side of storing artifacts and objects in S3.

Use the following setup:

- S3 bucket: `mind-technology-lab-experiments`
- S3 prefix: use the same folder and prefix that exists locally. For example, if the folder is `experiments/paper-name/`, the S3 prefix is `experiments/paper-name/`.

## Setting up MCP servers

Project MCP servers live in `.cursor/mcp.json`. Do not put secrets in that file. The API key, ALPHAXIV_API_KEY, lives in the environment.

### AlphaXiv

Use the AlphaXiv MCP server for paper search, PDF questions, researcher lookup, and library tools. Docs: [https://www.alphaxiv.org/docs/mcp](https://www.alphaxiv.org/docs/mcp).

- Endpoint: `https://api.alphaxiv.org/mcp/v1`
- Transport: Streamable HTTP
- Auth: send `Authorization: Bearer ${env:ALPHAXIV_API_KEY}`
