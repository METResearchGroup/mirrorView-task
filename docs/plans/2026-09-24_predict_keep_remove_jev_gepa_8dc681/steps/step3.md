# Step 3: Build study-faithful prompt rendering for pair, original, and mirror views

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py` public render functions consumed by tests and later `jev_scorer.py`
- **Task:** Copy study instruction text from `experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` (`STUDY_INSTRUCTION`). Build pair, original-only, and mirror-only renderers. Insert the A4 addendum from `KEEP_REMOVE_FEATURES_ADDENDUM`. Use deterministic pair order via `pair_order_for_post` (seed 0, same hash as Step 2). Build Noul per-post instruction builders for pair and single-text arms. Document and test the exact single-post instruction diff. Run fidelity tests against `webapp/public/main.js` linked-fate (non-control) copy.
- **Out of scope:** Jev API calls, GEPA adapter, `jev_baseline/run.py`, editing `webapp/`, copying `KEEP_REMOVE_FEATURES_ADDENDUM` text into this repo (import only).

## Dependencies

Step 2 must expose `pair_order_for_post` (import from `cohort.py` or duplicate the same function in `prompt.py`; do not reshuffle independently).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/design.md` | Prompt sources, closing line, A4 addendum path, Jev state/question pattern |
| `/workspace/docs/plans/2026-09-24_predict_keep_remove_jev_gepa_8dc681/steps/step2.md` | Pair order seed and cohort columns |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` | `STUDY_INSTRUCTION`, `render_prompt`, `_ordered_texts` |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` | `CLOSING_LINE`, `POST_1_LABEL`, `POST_2_LABEL`, `ROLE_ORIGINAL`, `ROLE_MIRROR` |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | `KEEP_REMOVE_FEATURES_ADDENDUM` import source |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py` | Addendum slot after judgment paragraph, before Post 1 |
| `/workspace/webapp/public/main.js` | Linked-fate instructions lines 607 to 620; closing `Allow or Remove?` lines 637, 680, 802 |
| `/tmp/jev_probe/run_probe.py` | `noul_instruction_pair`, `noul_instruction_single`, `POSTS_STATE_KEY = "posts"` |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/prompt.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_render_pair_prompt.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_render_single_prompt.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_noul_instructions.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_webapp_fidelity.py` (new)

## Files forbidden to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/README.md`
- `/workspace/webapp/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py`
- `/workspace/shared/data/registry.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`

## Contracts

Pinned module constants:

- `POSTS_STATE_KEY = "posts"`
- `QUESTION_ID_PREFIX = "post_"`
- `CLOSING_LINE = "Allow or Remove?"`
- `POST_1_LABEL = "Post 1:"`
- `POST_2_LABEL = "Post 2:"`
- `VIEW_PAIR = "pair"`
- `VIEW_ORIGINAL = "original"`
- `VIEW_MIRROR = "mirror"`

`STUDY_INSTRUCTION` must match `experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` character for character (plain text, no HTML). Do not import `STUDY_PROMPT_TEMPLATE` from the prompt-engineering experiment.

### Pair renderer

```python
def render_pair_prompt(
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool = False,
) -> str:
    """Return full Jev state text for the pair view (A1 or A4 when add_criteria=True).
    Insert KEEP_REMOVE_FEATURES_ADDENDUM after the judgment paragraph and before Post 1 when add_criteria.
    Closing line is exactly CLOSING_LINE."""
```

Equivalent to reasoning `render_prompt(original_text, mirror_text, post_1_role, add_criteria)`.

### Single-text renderers

```python
def render_original_prompt(original_text: str) -> str:
    """Return Jev state text for original-only view (A2). One post body, no Post 2 block."""

def render_mirror_prompt(mirror_text: str) -> str:
    """Return Jev state text for mirror-only view (A3). One post body, no Post 2 block."""
```

### Single-post instruction diff (document in module docstring and test)

Pair `STUDY_INSTRUCTION` opening sentence:

```text
Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.
```

Single-post `STUDY_INSTRUCTION` opening sentence:

```text
Your task will be to review a series of real political social media posts, and decide whether each post should be allowed or removed from the platform.
```

Additional single-post edits (apply consistently in `render_original_prompt` and `render_mirror_prompt`):

1. Remove the abortion Original Text / Mirror Text example block (from `The pairs are political mirrors` through the stance-replication paragraph).
2. Replace `Your job is to decide whether both posts in the pair should be allowed or removed from the platform.` with `Your job is to decide whether the post should be allowed or removed from the platform.`
3. Render one post block labeled `Post 1:` only (no `Post 2:`).
4. Keep the healthy-environment judgment paragraph and the no-right-or-wrong line unchanged.
5. Do not include `Click Next to continue to a practice trial.`

### View router

```python
def render_state_text(
    view: str,
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool = False,
) -> str:
    """Dispatch pair|original|mirror. Raise ValueError on unknown view."""
```

### Noul instruction builders

```python
def build_noul_instruction(index: int, view: str) -> str:
    """Return per-question instruction referencing POSTS_STATE_KEY[index].

    pair view:
      Consider `posts[i]`. You are evaluating a pair of political social media posts shown together,
      including the study instructions and both post texts.
      Should this pair of posts be removed from the platform?
      Answer yes if both posts should be removed; answer no if both should be allowed.

    original or mirror view:
      Consider `posts[i]`. You are evaluating one political social media post.
      Should this post be removed from the platform?
      Answer yes if it should be removed; answer no if it should be allowed.
    """

def build_questions(n_posts: int, view: str) -> dict[str, Noul]:
    """Return {post_i: Noul(instructions=build_noul_instruction(i, view))} for i in 0..n_posts-1."""
```

Import `Noul` from `typesafe_sdk`.

### Golden pair body lines (must appear in `render_pair_prompt`)

```text
Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.
The pairs are political mirrors of each other.
There are no right or wrong answers - we are interested in what you personally think.
```

### Golden single-post body lines

```text
Your task will be to review a series of real political social media posts, and decide whether each post should be allowed or removed from the platform.
There are no right or wrong answers - we are interested in what you personally think.
```

Single-post output must not contain `Post 2:` or `political mirrors of each other`.

## Tests to write first

### `tests/test_render_pair_prompt.py`

Class `TestRenderPairPrompt`.

```text
given original "o" mirror "m" post_1_role original add_criteria false
when render_pair_prompt
then output contains "Post 1: o" and "Post 2: m"
and ends with "Allow or Remove?"
and contains golden pair body lines
and does not contain KEEP_REMOVE_FEATURES_ADDENDUM phrase "Imperative policy or punishment demands"

given post_1_role mirror
when render_pair_prompt
then Post 1 is m and Post 2 is o
and the abortion example still names Original Text and Mirror Text

given add_criteria true
when render_pair_prompt
then KEEP_REMOVE_FEATURES_ADDENDUM appears after "Your job is to decide whether both posts"
and before "Post 1:"
```

### `tests/test_render_single_prompt.py`

Class `TestRenderOriginalPrompt` and class `TestRenderMirrorPrompt`.

```text
given original "o"
when render_original_prompt
then output contains "Post 1: o"
and contains golden single-post opening sentence
and does not contain "Post 2:"
and does not contain "political mirrors"
and ends with "Allow or Remove?"

given mirror "m"
when render_mirror_prompt
then output contains "Post 1: m"
and same single-post constraints as original arm
```

Class `TestSinglePostInstructionDiff`.

```text
given the pair and single renderers
when comparing opening task sentences
then pair uses "pairs" and "both posts in the pair"
and single uses "each post" without "pairs"
```

### `tests/test_noul_instructions.py`

Class `TestBuildNoulInstruction`.

```text
given index 3 view pair
when build_noul_instruction
then the string contains "posts[3]" and "pair of posts"

given index 0 view original
when build_noul_instruction
then the string contains "posts[0]" and "one political social media post"
and does not contain "pair"

given n_posts 2 view mirror
when build_questions
then keys are post_0 and post_1
and each value is a Noul with non-empty instructions
```

### `tests/test_webapp_fidelity.py`

Class `TestWebappFidelity`.

```text
given render_pair_prompt with add_criteria false
when stripping HTML tags from webapp linked-fate block in main.js lines 607-620 to plain text
then every non-empty webapp instruction sentence (excluding "Click Next") appears as a substring of the rendered prompt after normalizing whitespace
and closing line matches webapp prompt "Allow or Remove?" exactly
and rendered prompt does not contain "Allow Or Remove?"
```

Build the webapp plain-text fixture once in the test from the literal strings in `main.js` (do not import `main.js` at runtime).

## Implementation order

Follow `/implement-from-spec`. Full auto. One commit per unit of work.

1. `prompt.py` scaffold with `STUDY_INSTRUCTION` copied and stub renderers
2. pytest files (failing)
3. `render_pair_prompt` and `render_state_text` pair branch until `test_render_pair_prompt.py` is green
4. `render_original_prompt`, `render_mirror_prompt`, and single-post instruction diff until `test_render_single_prompt.py` is green
5. `build_noul_instruction` and `build_questions` until `test_noul_instructions.py` is green
6. `test_webapp_fidelity.py` until green

## Commands

Pytest (includes Steps 1 and 2):

```bash
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests -q
```

Expected: exit 0.

Spot-check pair versus single diff:

```bash
PYTHONPATH=. uv run python -c "
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import render_pair_prompt, render_original_prompt
pair = render_pair_prompt('o','m','original', False)
single = render_original_prompt('o')
assert 'pairs of real political' in pair
assert 'each post should be allowed' in single
assert 'Post 2:' not in single
print('prompt_views_ok')
"
```

Expected stdout: `prompt_views_ok`

## Must pass

- `STUDY_INSTRUCTION` matches reasoning-during-moderation copy.
- Pair renderer preserves stored `post_1_role` order without reshuffling.
- A4 addendum imports from `experiments.llm_prompt_engineering_2026_08_05.prompt`.
- Closing line is `Allow or Remove?` (capital o in or).
- Single-post arms use the documented instruction diff.
- Noul builders reference ``posts[i]`` state slots.
- Webapp fidelity test passes for linked-fate copy.
- All shared tests exit 0.

## Must fail

- Importing `STUDY_PROMPT_TEMPLATE`.
- Closing with `Allow Or Remove?`.
- Including `Click Next to continue`.
- Using control-condition copy (single-post review without pairs language in pair arm).
- Rendering both Post 1 and Post 2 in original-only or mirror-only arms.
- Re-shuffling pair order inside the renderer.
- Hardcoding `KEEP_REMOVE_FEATURES_ADDENDUM` text in this experiment.

## Commit messages

1. `add study instruction and pair prompt renderer`
2. `add original and mirror single-post prompt renderers`
3. `add Noul instruction builders for Jev scoring`
4. `add prompt fidelity and view tests`

## Implement-from-spec notes

Phase 1 names `render_state_text` as the primary caller-facing API. Phase 6 completes when all prompt tests are green and the spot-check command prints `prompt_views_ok`.
