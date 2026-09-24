# AGENTS.md

## Conventions

Follow the conventions defined in https://github.com/mark-torres10/ai_tools/blob/main/conventions/vocabulary.md.

## Instructions for agents

IF you are a local agent, this does NOT apply to you.

If you are a remote agent (e.g., via Cursor Cloud, OpenHands, or other harnesses):

When starting:

1. Set up and authenticate to the AWS environment. This will give you the credentials that you need to access the AWS Secrets Manager, which stores all of our actual credentials and secrets. Verify that you can access AWS Secrets Manager, and hard-fail if not.
2. Get the GitHub personal access token from the AWS Secrets Manager and use that to authenticate into GitHub. This is stored in the `kova-github-pat` secret as `GITHUB_PAT_TOKEN`.

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

- S3 bucket: `mirrorview-experimental-artifacts`
- S3 prefix: use the same folder and prefix that exists locally. For example, if the folder is `experiments/paper-name/`, the S3 prefix is `experiments/paper-name/`.

## Setting up MCP servers

Project MCP servers live in `.cursor/mcp.json`. Do not put secrets in that file. The API key, ALPHAXIV_API_KEY, lives in the environment.

### AlphaXiv

Use the AlphaXiv MCP server for paper search, PDF questions, researcher lookup, and library tools. Docs: [https://www.alphaxiv.org/docs/mcp](https://www.alphaxiv.org/docs/mcp).

- Endpoint: `https://api.alphaxiv.org/mcp/v1`
- Transport: Streamable HTTP
- Auth: send `Authorization: Bearer ${env:ALPHAXIV_API_KEY}`

## Experiments

Experiments should live in the experiments/ folder. Typical naming convention is experiments/{identifiable name}_{YYYY_MM_DD}/

Guidelines for experiments:

- README: if not directly provided by the user, should be 1-2 lines with the title and then a redirect to SETUP.md and RESULTS.md.
if the user provides the README, keep it read-only.
- SETUP.md: should discuss what data is required. out of scope is environment related setup
- RESULTS.md: report results here. err towards tables and easy to understand messaging.

For storage, err on the side of using S3 for larger files and derived assets.
