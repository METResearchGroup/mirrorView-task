# Step 1: Add the prompt and confirm the live service contracts

## Outcome

This step adds the issue 329 prompt, pins the optimization dependencies, and proves that DSPy can use GPT-5.6 Terra through Bedrock while Weave uploads the trace. The step uses one paid task prediction and one paid reflection call. Stop immediately if either call or its trace fails.

## Caller and happy path

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only`.

The command loads credentials through the repository environment loader and starts Weave before it constructs the DSPy language model. It then runs one structured classification and one reflection. After Weave flushes, the command confirms both trace URLs. It prints identifiers and counts, but it never prints a secret or full credential object.

## Files

### Inspect

- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/lib/load_env_vars.py`
- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/compare_jev_human_uncertainty_2026_09_25/jev_labels.py`
- Issue 329, including its full prompt and all 10 examples
- The current DSPy, GEPA, LiteLLM Bedrock, and W&B Weave API documentation

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/program.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/telemetry.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py`

### Forbidden to change

- Dataset registry entries and source datasets
- Existing experiment outputs
- Any test file or test directory
- `.env`, AWS credential files, W&B credential files, and committed secret values
- Files under `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/` that belong to later steps

## Contracts to confirm

1. Copy `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` from issue 329 without changing its examples, labels, order, placeholders, or line breaks.
2. Pin DSPy 3.4.0 and GEPA 0.1.4. Pin a Weave version that supports the installed W&B client and DSPy integration, and record the resolved versions in `uv.lock`.
3. Keep the Bedrock model ID `us.openai.gpt-5.6-terra`. Confirm the exact LiteLLM provider string with a live call instead of assuming it.
4. Define the task signature with `post_1_text` and `post_2_text` as inputs. Its outputs are `is_remove: bool` and `p_remove: float`, where `p_remove` must be between 0 and 1.
5. Initialize Weave with `mind_technology_lab/dspy_gepa_optimization_2026_09_30` before constructing or running the DSPy module. Use the default W&B host.
6. Load `WANDB_API_KEY` through `EnvVarsContainer`. If the loader no longer registers the key, add it there without adding a fallback secret source.
7. Raw post text, prompts, model outputs, and reflections may appear in traces. API keys, AWS credentials, authorization headers, and environment dumps may not appear.
8. Confirm the accepted DSPy settings for this reasoning model, including temperature and maximum output tokens. Write the confirmed values to `config.py` and reuse them in every later step.
9. Disable the DSPy response cache for paid experiment calls so usage counts and candidate comparisons describe actual provider calls.

## Implementation sequence

1. Add the prompt package and copy the issue 329 prompt exactly.
2. Add and lock the three dependencies. Run the smallest dependency sync that installs the base project without the large development group.
3. Add immutable configuration values for the model, W&B entity and project, S3 bucket and prefix, random seed, probability threshold, and positive class.
4. Add the typed DSPy signature and a seed program that imports the prompt constant.
5. Add telemetry initialization, shared trace attributes, a flush check, and secret redaction for explicit metadata.
6. Add the `--contract-only` path to the setup caller. The path first uploads a no-cost local trace, then runs one task prediction and one reflection through the same model.
7. Validate both structured outputs. Confirm that Weave returns trace references for the task and reflection calls.
8. Save no generated artifact in Git. Print only the model ID, dependency versions, structured result, call counts, and W&B URLs.

## Smoke verification

```bash
PYTHONPATH=. uv sync --no-dev
```

Expected output. Dependency resolution succeeds without changing an unrelated dependency.

```bash
PYTHONPATH=. uv run python -c "from importlib.metadata import version; print(version('dspy'), version('gepa'), version('weave'))"
```

Expected output. The command prints the three locked versions and exits zero.

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only
```

Expected output. The environment and Weave checks pass, and the task result satisfies the typed contract. One reflection completes, two paid calls are counted, and the command prints the task and reflection trace URLs.

## Pass and stop conditions

Pass only when the prompt matches issue 329, the lock file is consistent, both paid calls use the required model, both structured outputs validate, and both traces are visible in the required W&B project.

Stop this experiment if Bedrock rejects the model or parameters, Weave cannot upload or flush a trace, a structured output fails validation, the cache prevents a paid call, or any secret appears in output or trace metadata. Resolve the contract before Step 2.

## Commit

Suggested commit message. `experiment: add DSPy prompt and service contract smoke`
