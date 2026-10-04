# Step 2: Add the few-shot prompt and Jev adapter

## Proposal sections implemented

- "Cross-cutting concerns: Prompt contract"
- "Cross-cutting concerns: Demonstration overlap"
- "Cross-cutting concerns: Data and S3 isolation"
- "File structure: Repository"
- "Schema and key interfaces"
- "Step 2: Add the few-shot prompt and request adapter"

## Goal

Create the few-shot experiment package, copy the issue 329 prompt exactly, compile it into Jev instructions, define `FEW_SHOT_VARIANT`, and expose one request builder. Add the documentation and package scaffold needed by the setup, inference, and analysis steps without implementing those three command callers yet.

Run every command from `/Users/mark/src/work/mirrorview-wt` with `PYTHONPATH=.`.

## Scope

- **Main caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/jev.py::build_few_shot_remove_request`.
- **Happy path:** receive one `Study2InputRecord`, place both post texts in classifier state, attach the compiled 6,000-byte few-shot instructions to the existing remove `Noul`, and return one `ClassifierRequest`.
- **Unit of work:** exact prompt bytes to validated transformed instructions to one request adapter.
- **Out of scope:** copying S3 input, setup behavior, Jev calls, inference and resume behavior, analysis, final result values, unit tests, and checked-in smoke scripts.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_jev_inference_659f8a/proposal.md`, especially the exact fenced prompt and the five overlap IDs
- [Issue 329](https://github.com/METResearchGroup/mirrorView-task/issues/329), read only, as the prompt source
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/shared/jev.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/RESULTS.md`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/README.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/SETUP.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/RESULTS.md` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/config.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/prompts.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/shared/jev.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/__init__.py` (new)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_jev_inference_2026_10_01/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- Every `main.py` under the new package until its owning later step
- Every `tests/` directory, every `test_*.py` file, and every checked-in smoke script

## Contracts

### Exact source prompt

Define `BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT` in `shared/prompts.py`. Copy the fenced prompt from the approved proposal, replacing each `⟦SPACE⟧` marker with one literal U+0020 space. Preserve every source character, including:

- all ten demonstrations and their order
- the remove and keep headings
- the two placeholders
- the blank line containing one space before remove example 3
- the newline inside keep example 2 after `other `
- Unicode punctuation
- the three newlines before the terminal question
- no newline after the final `Allow Or Remove?`

The string is 5,953 UTF-8 bytes and has SHA-256 `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3`. The digest, not a demonstration recount performed by new code, is the byte-level authority.

### Dedicated few-shot compiler

The existing zero-shot `build_remove_instructions` cannot compile this prompt. It requires a terminal dynamic pair block, but the few-shot pair block occurs before the demonstrations. Define:

```python
build_few_shot_remove_instructions(prompt: str) -> str
```

The compiler performs these exact operations:

1. Require exactly one dynamic block: `Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n`.
2. Require the prompt to end exactly with `Allow Or Remove?` and no trailing newline or text.
3. Remove the one dynamic block without changing adjacent prompt bytes.
4. Replace the terminal `Allow Or Remove?` with `REMOVE_QUESTION` imported from the zero-shot Jev adapter.

Do not call the zero-shot `build_remove_instructions`. Do not format the placeholders with current post text. Do not normalize whitespace, Unicode punctuation, or line endings.

Define `FEW_SHOT_REMOVE_INSTRUCTIONS` by compiling the exact source prompt at import time. The result is 6,000 UTF-8 bytes and has SHA-256 `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac`. It contains no `{post_1_text}` or `{post_2_text}` placeholder. It contains all ten demonstrations and ends with the existing state-pointer remove question.

### Few-shot configuration

Define `FEW_SHOT_VARIANT` in `shared/config.py` with these values:

| Field | Value |
| --- | --- |
| `experiment_name` | `few_shot_jev_inference_2026_10_01` |
| `s3_bucket` | `mirrorview-experimental-artifacts` |
| `s3_prefix` | `experiments/few_shot_jev_inference_2026_10_01/` |
| `input_records_key` | `experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/records.jsonl` |
| `input_manifest_key` | `experiments/few_shot_jev_inference_2026_10_01/inputs/study_2_five_labeler/manifest.json` |
| `run_manifest_schema_version` | `study2-few-shot-jev-run-v1` |
| `prompt_name` | `baseline_few_shot_keep_remove` |
| `prompt_sha256` | `ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3` |
| `instructions_sha256` | `a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac` |

Set `metric_exclusion_post_ids` to the five proposal IDs in their listed order. The tuple contains five unique values. All five are unanimous rows, but this step does not read S3 to establish that fact. Step 3 checks them against copied input.

### Request adapter

Define `build_few_shot_remove_request(record: Study2InputRecord) -> ClassifierRequest` in the few-shot `shared/jev.py`. Delegate to the zero-shot request builder with `instructions=FEW_SHOT_REMOVE_INSTRUCTIONS`. The request uses the existing state keys, remove question ID, `NoulCriteria`, and input order. Do not copy `REMOVE_CRITERIA` or the prediction adapter.

The request must have:

```python
{
    "state": {"post_1": record.post_1_text, "post_2": record.post_2_text},
    "questions": {"is_remove": Noul(instructions=FEW_SHOT_REMOVE_INSTRUCTIONS, ...)},
}
```

### Package and documentation scaffold

- `README.md` contains a title and links to `SETUP.md` and `RESULTS.md` in one or two lines.
- `SETUP.md` names the zero-shot Jev prepared input as the source, the required 13,992, 4,051, and 9,941 counts, the five metric exclusions, and the few-shot S3 input, run, and analysis roots. It contains no environment setup or run commands.
- `RESULTS.md` contains the experiment title and states that measured results are pending the full run. Do not copy estimates from the proposal into measured-result tables.
- Add only the listed `__init__.py` package markers. Later steps own the three `main.py` files.

## Caller-first implementation phases

The user approved the full plan and requested one commit per step. Do not pause after contracts, and do not create test files. The given, when, then cases below become inline Python assertions. Work through the phases in order and commit only after the full step passes.

### Phase 1: Confirm the unit of work

Name the few-shot `build_few_shot_remove_request` adapter as the one main caller boundary. Confirm the exact source and transformed digests before creating files. Stop if the proposal prompt no longer hashes to `ca6f0d...`.

### Phase 2: Scaffold packages and imports

Create the package markers, documentation files, `shared/prompts.py`, `shared/jev.py`, and `shared/config.py`. Add final names and signatures with stubbed compiler and request bodies. Do not create any `main.py` file.

The scaffold passes when the package imports reach the stubs and no zero-shot module imports from the new few-shot package.

### Phase 3: Confirm contracts

Confirm the compiler's two structural checks, the variant field values, the five exclusion IDs, and the adapter signature against this file. Keep behavior stubbed until the contract import succeeds. Do not commit a stubbed intermediate state.

### Phase 4: Design executable checks

Use these cases as the executable specification. Run their inline forms before implementation and confirm that each new case fails because a body is stubbed, not because an import is missing.

1. Given the exact issue 329 string, when hashed, then it is 5,953 bytes with source digest `ca6f0d...`.
2. Given the exact source string, when compiled, then it is 6,000 bytes with transformed digest `a45540...`.
3. Given a missing dynamic block, a duplicated dynamic block, trailing text, or a trailing newline, when compiled, then `ValueError` is raised.
4. Given one valid input record, when the adapter runs, then state holds current post text and the `Noul` holds the compiled instructions.
5. Given `FEW_SHOT_VARIANT`, when validated, then the prefix and input keys are disjoint from `ZERO_SHOT_VARIANT`, both digests match the module constants, and five unique exclusions are stored.

### Phase 5: Implement in dependency order

Implement and smoke one unit at a time:

1. Exact source prompt bytes.
2. Structural validation and the dedicated compiler.
3. `FEW_SHOT_REMOVE_INSTRUCTIONS` and its transformed digest assertion.
4. `FEW_SHOT_VARIANT` and its five exclusions.
5. The request adapter.
6. Package documentation.

After each unit, run the compilation and import checks. Do not edit the shared zero-shot implementation in this step.

### Phase 6: Verify and commit

Run every smoke check and inspect the final diff. Commit the allowed files once with:

```bash
git add \
  experiments/few_shot_jev_inference_2026_10_01/README.md \
  experiments/few_shot_jev_inference_2026_10_01/SETUP.md \
  experiments/few_shot_jev_inference_2026_10_01/RESULTS.md \
  experiments/few_shot_jev_inference_2026_10_01/__init__.py \
  experiments/few_shot_jev_inference_2026_10_01/shared/__init__.py \
  experiments/few_shot_jev_inference_2026_10_01/shared/config.py \
  experiments/few_shot_jev_inference_2026_10_01/shared/prompts.py \
  experiments/few_shot_jev_inference_2026_10_01/shared/jev.py \
  experiments/few_shot_jev_inference_2026_10_01/src/__init__.py \
  experiments/few_shot_jev_inference_2026_10_01/src/step1_setup/__init__.py \
  experiments/few_shot_jev_inference_2026_10_01/src/step2_inference/__init__.py \
  experiments/few_shot_jev_inference_2026_10_01/src/step3_analysis/__init__.py
git commit -m "feat: add few-shot Jev prompt adapter"
```

## Smoke checks

### Prompt, compiler, configuration, and request

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib

from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT
from experiments.few_shot_jev_inference_2026_10_01.shared.jev import (
    FEW_SHOT_REMOVE_INSTRUCTIONS,
    build_few_shot_remove_instructions,
    build_few_shot_remove_request,
)
from experiments.few_shot_jev_inference_2026_10_01.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
)
from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord

source_bytes = BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT.encode("utf-8")
instructions_bytes = FEW_SHOT_REMOVE_INSTRUCTIONS.encode("utf-8")
assert len(source_bytes) == 5_953
assert hashlib.sha256(source_bytes).hexdigest() == "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
assert len(instructions_bytes) == 6_000
assert hashlib.sha256(instructions_bytes).hexdigest() == "a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac"
assert "{post_1_text}" not in FEW_SHOT_REMOVE_INSTRUCTIONS
assert "{post_2_text}" not in FEW_SHOT_REMOVE_INSTRUCTIONS
assert FEW_SHOT_REMOVE_INSTRUCTIONS.count("Here are examples of pairs of posts that human annotators remove:") == 1
assert FEW_SHOT_REMOVE_INSTRUCTIONS.count("Here are examples of pairs of posts that human annotators keep:") == 1
assert FEW_SHOT_REMOVE_INSTRUCTIONS.count("\n1. Post 1:") == 2
assert FEW_SHOT_REMOVE_INSTRUCTIONS.count("\n5. Post 1:") == 2
assert FEW_SHOT_VARIANT.prompt_sha256 == hashlib.sha256(source_bytes).hexdigest()
assert FEW_SHOT_VARIANT.instructions_sha256 == hashlib.sha256(instructions_bytes).hexdigest()
assert FEW_SHOT_VARIANT.s3_prefix != ZERO_SHOT_VARIANT.s3_prefix
assert len(FEW_SHOT_VARIANT.metric_exclusion_post_ids) == 5
assert len(set(FEW_SHOT_VARIANT.metric_exclusion_post_ids)) == 5

record = Study2InputRecord(
    post_id="smoke",
    post_1_text="POST_ONE_SENTINEL",
    post_2_text="POST_TWO_SENTINEL",
    gold_is_remove=False,
    n_keep=5,
    n_remove=0,
    n_raters=5,
    is_unanimous=True,
)
request = build_few_shot_remove_request(record)
assert request["state"] == {"post_1": "POST_ONE_SENTINEL", "post_2": "POST_TWO_SENTINEL"}
assert tuple(request["questions"]) == ("is_remove",)
assert request["questions"]["is_remove"].instructions == FEW_SHOT_REMOVE_INSTRUCTIONS
assert build_few_shot_remove_instructions(BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT) == FEW_SHOT_REMOVE_INSTRUCTIONS
print("few-shot-prompt-adapter-ok source_bytes=5953 instructions_bytes=6000 exclusions=5")
PY
```

Expected stdout is exactly:

```text
few-shot-prompt-adapter-ok source_bytes=5953 instructions_bytes=6000 exclusions=5
```

### Compiler failure cases

```bash
PYTHONPATH=. uv run python - <<'PY'
from experiments.few_shot_jev_inference_2026_10_01.shared.jev import (
    build_few_shot_remove_instructions,
)
from experiments.few_shot_jev_inference_2026_10_01.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
)

block = "Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\n"
bad_prompts = (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT.replace(block, "", 1),
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT.replace(block, block + block, 1),
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT + "trailing",
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT + "\n",
)
for prompt in bad_prompts:
    try:
        build_few_shot_remove_instructions(prompt)
    except ValueError:
        continue
    raise AssertionError("malformed few-shot prompt was accepted")
print("few-shot-compiler-rejections-ok cases=4")
PY
```

Expected stdout is exactly `few-shot-compiler-rejections-ok cases=4`.

### Imports, compilation, documentation, and scope

```bash
PYTHONPATH=. uv run python -m compileall -q \
  experiments/few_shot_jev_inference_2026_10_01 && echo compileall-ok
PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT; from experiments.few_shot_jev_inference_2026_10_01.shared.jev import build_few_shot_remove_request; print('few-shot-imports-ok', FEW_SHOT_VARIANT.experiment_name)"
test "$(wc -l < experiments/few_shot_jev_inference_2026_10_01/README.md | tr -d ' ')" -le 3
rg -n 'SETUP\.md|RESULTS\.md' experiments/few_shot_jev_inference_2026_10_01/README.md
if rg -n 'AWS_ACCESS_KEY|uv run|python -m' experiments/few_shot_jev_inference_2026_10_01/SETUP.md; then
  echo "SETUP.md contains environment setup or run commands" >&2
  exit 1
fi
if find experiments/few_shot_jev_inference_2026_10_01 -name 'main.py' -o -name 'test_*.py' | grep -q .; then
  echo "step added a deferred main or a test file" >&2
  exit 1
fi
if rg -n 'few_shot_jev_inference_2026_10_01' experiments/zero_shot_jev_inference_2026_10_01 shared; then
  echo "zero-shot or root shared code imports the few-shot package" >&2
  exit 1
fi
echo few-shot-scaffold-scope-ok
```

Expected output includes:

```text
compileall-ok
few-shot-imports-ok few_shot_jev_inference_2026_10_01
few-shot-scaffold-scope-ok
```

## Must pass

- The source prompt and transformed instructions match both approved byte counts and SHA-256 digests.
- The compiler rejects all four structural failures before creating a request.
- The request uses current post text only in classifier state and uses the compiled instructions in the one `Noul`.
- The five exclusion IDs are unique and stored in proposal order.
- The few-shot and zero-shot S3 roots differ.
- Documentation follows the repository experiment rules.
- No command caller, unit test, or checked-in smoke script is added.

## Must fail

- Any changed source-prompt byte, demonstration order, label, placeholder, whitespace, punctuation, or final newline.
- Any transformed-instructions byte that changes digest `a455405f...`.
- A compiler input with zero or multiple dynamic blocks, or a nonterminal `Allow Or Remove?`.
- A request that interpolates current posts into instructions or changes their state order.
- A duplicate or missing metric exclusion ID.
- Any change to a forbidden path.
