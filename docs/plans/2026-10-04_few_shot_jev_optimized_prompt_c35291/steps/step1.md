# Step 1: Add the shared prompt constant

## Proposal sections implemented

- "Cross-cutting concerns: Reuse"
- "Cross-cutting concerns: Prompt bytes"
- "File structure: Repository"
- "Schema and key interfaces"
- "Step 1: Add the shared prompt constant"
- "Confirmed decisions" 1 and the settled choice of no final newline

## Goal

Create `OPTIMIZED_STUDY_PROMPT_TEMPLATE` and export it from `shared.models.llm`. The string is the balanced GEPA instruction with the ten issue 329 examples inserted, the space-only line restored, and no final newline.

Run every command from `/workspace` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/workspace/shared/models/llm/__init__.py`, which re-exports the constant.
- **Happy path:** import `OPTIMIZED_STUDY_PROMPT_TEMPLATE` and get the 6,290-byte string whose SHA-256 is `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f`.
- **Unit of work:** one string constant and its public export.
- **Out of scope:** the experiment package, the compiler, S3, Jev calls, analysis, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/workspace/docs/plans/2026-10-04_few_shot_jev_optimized_prompt_c35291/proposal.md`, especially "Prompt bytes" and confirmed decision 1
- `/workspace/experiments/dspy_gepa_balanced_labels_2026_10_02/RESULTS.md`, the fenced text under "Optimized instruction"
- `/workspace/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`, symbol `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`
- `/workspace/shared/models/jev/__init__.py`, as the export shape to copy
- `/workspace/shared/models/__init__.py`, read only

## Files allowed to change

- `/workspace/shared/models/llm/__init__.py` (new)
- `/workspace/shared/models/llm/prompt.py` (new)

## Files forbidden to change

- `/workspace/shared/models/__init__.py`
- `/workspace/shared/models/jev/**`
- `/workspace/experiments/**`
- `/workspace/pyproject.toml`
- `/workspace/uv.lock`
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

### How to assemble the string

Build the constant with these four operations. Do not retype the examples by hand.

1. Read the fenced text under "Optimized instruction" in `/workspace/experiments/dspy_gepa_balanced_labels_2026_10_02/RESULTS.md`. Drop the newline that the fence adds after `Allow Or Remove?`.
2. Remove the suffix `\n\nReturn only the decision.\n\nAllow Or Remove?`.
3. Append `\n\n` and the example block from `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT`, starting at `Here are examples of pairs of posts that human annotators remove:` and stopping before `\nAllow Or Remove?`. Keep the space at the end of the first line of keep example 2. Keep the line that contains only one space before remove example 3.
4. Append `Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\nReturn only the decision.\n\nkeep or remove` with no final newline.

The result is 6,290 UTF-8 bytes. Its SHA-256 is `178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f`. The digest is the byte-level check. A recount of the examples is not.

`prompt.py` imports nothing from `experiments/`. Root `shared/` never imports from `experiments/`.

### Public export

`shared/models/llm/__init__.py` exports `OPTIMIZED_STUDY_PROMPT_TEMPLATE` in `__all__`. `from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE` and `from shared.models.llm.prompt import OPTIMIZED_STUDY_PROMPT_TEMPLATE` return the same string.

## Checks

Run this before creating the module. It must fail with `ModuleNotFoundError`. Run it again after the constant exists. It must print `optimized-prompt-ok`.

```bash
cd /workspace
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from shared.models.llm import OPTIMIZED_STUDY_PROMPT_TEMPLATE
from shared.models.llm.prompt import OPTIMIZED_STUDY_PROMPT_TEMPLATE as direct

assert direct == OPTIMIZED_STUDY_PROMPT_TEMPLATE
text = OPTIMIZED_STUDY_PROMPT_TEMPLATE
assert text.endswith("keep or remove")
assert not text.endswith("\n")
assert text.count("Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n") == 1
assert "\n \n3. Post 1: Woke" in text
assert "other \n" in text
assert "Allow Or Remove?" not in text
encoded = text.encode()
assert len(encoded) == 6290
assert hashlib.sha256(encoded).hexdigest() == (
    "178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f"
)
print("optimized-prompt-ok")
PY
```

A mismatch on the digest, the byte count, the space-only line, or the ending fails the step. Do not add a compiler in this step.

## Pass and fail

- Pass: the second run prints `optimized-prompt-ok`, and `git diff --name-only` lists only the two new files under `shared/models/llm/`.
- Fail: the import succeeds before the files exist, the digest differs, the string ends with a newline, or any forbidden file changes.
