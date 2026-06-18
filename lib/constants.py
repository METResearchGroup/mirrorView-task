from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_LLM_MODEL = "gpt-5.4-nano"

# Bedrock — Claude Sonnet 4.6 via US geo inference (not in-region in us-east-2).
BEDROCK_REGION = "us-east-2"
DEFAULT_BEDROCK_SONNET_MODEL = "us.anthropic.claude-sonnet-4-6"