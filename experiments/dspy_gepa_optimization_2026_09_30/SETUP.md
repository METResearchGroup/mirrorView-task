# Setup

This experiment scores unanimous Study 2 pairs after removing the ten labeled examples in the issue 329 prompt.

## Required data

- Registered dataset `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS`, loaded with `shared.data.dataloader.load_dataset`.
- The issue 329 prompt in `experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`.
- Exclusion ids in `EXCLUDELIST_POST_IDS`. Those ten pairs are demonstrations, not scored rows.

The setup command writes the prepared inputs under `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_optimization_2026_09_30/inputs/`. Optimizer and evaluation artifacts are written under `runs/` in that same prefix. They are outputs, not inputs that must already exist.

The source table has 4,051 unanimous five-labeler pairs. After the ten exclusions, 4,041 pairs remain. The pilot cohort has 405 pairs, split into 222 optimization, 61 GEPA validation, 61 development, and 61 test rows.

## Credentials

`WANDB_API_KEY` comes from AWS Secrets Manager through `EnvVarsContainer` in `lib/load_env_vars.py`. The setup command fails before a paid model call when the key is missing. Do not pass the key on the command line or commit it.

Bedrock and S3 use the lab AWS keys when the standard AWS variables are empty. The region is `us-east-2`.

## Traces

Weave project: `mind_technology_lab/dspy_gepa_optimization_2026_09_30` on the default W&B host.

Traces may contain raw post text, prompts, model outputs, and reflections. They must not contain API keys, AWS credentials, authorization headers, or environment dumps.

## Commands

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --smoke --max-metric-calls 30
```

The 1,000-call pilot stays blocked until the smoke run's measured cost and runtime are approved.
