# Step 2: Add the experiment compiler and configuration

## Proposal sections implemented

- "Cross-cutting concerns: Reuse"
- "Cross-cutting concerns: Prompt bytes"
- "Cross-cutting concerns: Rows and metrics"
- "Cross-cutting concerns: Model and request limits"
- "File structure: Repository"
- "Schema and key interfaces"
- "Step 2: Add the experiment variant and compiler"
- "Confirmed decisions" 2 and 3

## Goal

Add the experiment package, compile the shared prompt into Jev instructions, and define `OPTIMIZED_VARIANT`. Add the documentation and package markers. Do not add the three `main.py` command files yet.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/jev.py`, function `build_optimized_remove_request`.
- **Happy path:** one `Study2InputRecord` becomes one `ClassifierRequest` whose instructions are the compiled 6,339-byte string.
- **Unit of work:** prompt bytes to validated instructions to one request adapter and one configuration.
- **Out of scope:** copying S3 input, live Jev calls, analysis, changes to the completed Jev packages, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/proposal.md`
- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/steps/step1.md`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/shared/jev.py`, function `build_few_shot_remove_instructions`, read only
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/shared/config.py`, read only
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/README.md`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/SETUP.md`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`, symbols `REMOVE_QUESTION` and `build_remove_request`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/shared/config.py`, class `JevInferenceVariant`
- `/workspace/shared/models/llm/prompt.py`

## Files allowed to change

- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/README.md` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/SETUP.md` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/RESULTS.md` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/__init__.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/__init__.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/config.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/shared/jev.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/__init__.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step1_setup/__init__.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step2_inference/__init__.py` (new)
- `/workspace/experiments/few_shot_jev_optimized_prompt_2026_10_04/src/step3_analysis/__init__.py` (new)

## Files forbidden to change

- `/workspace/shared/models/llm/**`
- `/workspace/shared/models/jev/**`
- `/workspace/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/few_shot_jev_inference_2026_10_01/**`
- `/workspace/experiments/dspy_gepa_balanced_labels_2026_10_02/**`
- `/workspace/experiments/few_shot_llm_inference_2026_09_30/**`
- Every `main.py` under the new package until its later step
- `/workspace/pyproject.toml` and `/workspace/uv.lock`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

### Compiler

Define `build_optimized_remove_instructions(prompt: str) -> str` in the new `shared/jev.py`. Do not call `build_few_shot_remove_instructions` or `build_remove_instructions`.

The function does these four checks and edits:

1. Require exactly one dynamic block, `Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n`. Any other count raises `ValueError`.
2. Require the prompt to end with `keep or remove` and nothing after it. A final newline, a different terminal line, or extra text raises `ValueError`.
3. Delete that one dynamic block. Leave the surrounding bytes unchanged.
4. Replace the terminal `keep or remove` with `REMOVE_QUESTION` imported from `/workspace/experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`.

Define `OPTIMIZED_REMOVE_INSTRUCTIONS` by compiling `OPTIMIZED_STUDY_PROMPT_TEMPLATE` at import time. The result is 6,339 UTF-8 bytes and has SHA-256 `1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e`. It contains no `{post_1_text}` or `{post_2_text}` placeholder. It contains all ten demonstrations and ends with `REMOVE_QUESTION`.

### Configuration

Define `OPTIMIZED_VARIANT` as a `JevInferenceVariant` in the new `shared/config.py`.

| Field | Value |
| --- | --- |
| `experiment_name` | `few_shot_jev_optimized_prompt_2026_10_04` |
| `s3_bucket` | `mirrorview-experimental-artifacts` |
| `s3_prefix` | `experiments/few_shot_jev_optimized_prompt_2026_10_04/` |
| `input_records_key` | `experiments/few_shot_jev_optimized_prompt_2026_10_04/inputs/study_2_five_labeler/records.jsonl` |
| `input_manifest_key` | `experiments/few_shot_jev_optimized_prompt_2026_10_04/inputs/study_2_five_labeler/manifest.json` |
| `run_manifest_schema_version` | `study2-optimized-prompt-jev-run-v1` |
| `prompt_name` | `optimized_study_prompt` |
| `prompt_sha256` | `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f` |
| `instructions_sha256` | `1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e` |

Set `metric_exclusion_post_ids` to these five ids, in this order:

- `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
- `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
- `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
- `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
- `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

### Request adapter

Define `build_optimized_remove_request(record: Study2InputRecord) -> ClassifierRequest`. Delegate to `build_remove_request` with `instructions=OPTIMIZED_REMOVE_INSTRUCTIONS`. Do not copy `REMOVE_CRITERIA`, the state keys, or `to_prediction_record`.

The request state is `post_1` and `post_2` in input order. The only question id is `is_remove`.

### Documentation

- `README.md` is a title plus links to `SETUP.md` and `RESULTS.md`, in one or two lines.
- `SETUP.md` names the zero-shot Jev prepared input, the counts 13,992, 4,051, and 9,941, the five exclusion ids, and the new S3 input, run, and analysis roots. It has no environment setup and no run commands.
- `RESULTS.md` has the experiment title and says measured results are pending. Do not copy the proposal's token or cost estimates into a measured table. Later steps replace that pending sentence with the measured smoke and production results.

## Checks

Run this before the new package exists. It must fail with `ModuleNotFoundError`. Run it again after the compiler and configuration exist. It must print `optimized-jev-contract-ok`.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.jev import (
    OPTIMIZED_REMOVE_INSTRUCTIONS,
    build_optimized_remove_instructions,
    build_optimized_remove_request,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import REMOVE_QUESTION
from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE

assert callable(build_optimized_remove_request)
compiled = build_optimized_remove_instructions(OPTIMIZED_STUDY_PROMPT_TEMPLATE)
assert compiled == OPTIMIZED_REMOVE_INSTRUCTIONS
assert compiled.endswith(REMOVE_QUESTION)
assert "{post_1_text}" not in compiled
assert len(compiled.encode()) == 6339
assert hashlib.sha256(compiled.encode()).hexdigest() == (
    "1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e"
)
assert OPTIMIZED_VARIANT.prompt_sha256 == (
    "178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f"
)
assert OPTIMIZED_VARIANT.instructions_sha256 == hashlib.sha256(compiled.encode()).hexdigest()
assert OPTIMIZED_VARIANT.s3_prefix == "experiments/few_shot_jev_optimized_prompt_2026_10_04/"
assert len(OPTIMIZED_VARIANT.metric_exclusion_post_ids) == 5
for bad in (
    "",
    OPTIMIZED_STUDY_PROMPT_TEMPLATE + "\n",
    OPTIMIZED_STUDY_PROMPT_TEMPLATE.replace("keep or remove", "Allow Or Remove?"),
    OPTIMIZED_STUDY_PROMPT_TEMPLATE + OPTIMIZED_STUDY_PROMPT_TEMPLATE,
):
    try:
        build_optimized_remove_instructions(bad)
    except ValueError:
        continue
    raise SystemExit(f"compiler accepted invalid prompt bytes={len(bad.encode())}")
print("optimized-jev-contract-ok")
PY
```

The doubled-template case has two dynamic blocks, so it must raise `ValueError`. The other three cases fail the terminal-line check.

## Pass and fail

- Pass: the check prints `optimized-jev-contract-ok`, and the new tree matches the allowed file list. No `main.py` exists yet.
- Fail: the compiler accepts a bad ending, the instruction digest differs, a forbidden package changes, or a `main.py` appears in this step.
