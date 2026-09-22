# Step 2: Lock the study prompt and smoke thinking mode

## Scope

- **Caller:** `experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py` `main` with `--smoke --limit 3`
- **Task:** Add a shared prompt renderer that matches the linked-fate website copy, renders one pair using the stored Post 1 / Post 2 order, and optionally inserts `KEEP_REMOVE_FEATURES_ADDENDUM`. Add a thinking-token counter that counts generated token ids inside the thinking span. Add a Hugging Face runner that turns thinking on for both models. Smoke three posts per model and fail if the thinking span is missing or the count is zero.
- **Out of scope:** The full experiment 1 table, experiment 2, human times, bag-of-words, `RESULTS.md`, downloading models inside pytest, editing `webapp/`, rewriting `KEEP_REMOVE_FEATURES.md`.

## Dependencies

Step 1 has a three-group cohort with `post_1_role` and `post_2_role`. The smoke may use three local fixture posts if the live parquet is not on disk, but the renderer must read those two role columns. Do not shuffle again.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md` | Website copy, one pair at a time, thinking-token rule, model ids |
| `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/steps/step1.md` | Cohort columns and stored pair order |
| `/workspace/webapp/public/main.js` | Linked-fate instructions around lines 607 to 620. Trial prompt is `Allow or Remove?` at lines 637, 680, and 802. Use the training and training_assisted branch, not the control branch. |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | Import `KEEP_REMOVE_FEATURES_ADDENDUM` only. Do not import `STUDY_PROMPT_TEMPLATE`. The prompt-engineering template closes with `Allow Or Remove?` and omits the no-right-or-wrong line. |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py` | Addendum slot is after the judgment paragraph and before Post 1. |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/prompts.py` | Short renderer with a stored presentation order. Do not copy that system prompt. |
| `/workspace/AGENTS.md` | GPU work uses Hugging Face Jobs. Default open-source model is Qwen 3.5 4B. |

## Files allowed to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` (add the smoke command and sampling settings only)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/constants.py` (model ids, sampling, token caps)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/prompt.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/thinking.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/runner.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/jobs.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/__init__.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_render_prompt.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_count_thinking_tokens.py` (new)
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_generation_seed.py` (new)

## Files forbidden to change

- `/workspace/experiments/reasoning_during_moderation_2026_09_15/README.md`
- `/workspace/webapp/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/KEEP_REMOVE_FEATURES.md`
- `/workspace/shared/data/registry.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-15_reasoning_during_moderation_a74e4f/plan.md`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## Prompt contract

`render_prompt(original_text, mirror_text, post_1_role, add_criteria)` returns one user-message string.

Instruction text is the linked-fate (non-control) copy from `webapp/public/main.js`, with HTML tags stripped to plain text. Keep the abortion original and mirror example. Keep the line `There are no right or wrong answers - we are interested in what you personally think.` Drop `Click Next to continue to a practice trial.` Do not use the control-condition paragraph that asks people to review a series of posts rather than pairs.

Closing line is exactly `Allow or Remove?`. Do not use `Allow Or Remove?`.

When `add_criteria` is true, insert `KEEP_REMOVE_FEATURES_ADDENDUM` after the judgment paragraph and before `Post 1:`, the same slot as `generate_prompt.py`. Import the addendum. Do not copy it.

Render exactly one pair. `Post 1:` is the text for `post_1_role`. `Post 2:` is the other text. Labels stay `Post 1` and `Post 2` even when the mirror is first.

Do not add a system prompt. Both models receive this string as the user message.

Golden instruction body, after HTML strip, must contain these lines:

```text
Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.
The pairs are political mirrors of each other.
There are no right or wrong answers - we are interested in what you personally think.
```

Do not copy the twenty-pair JSON prompt from pull request 292.

## Thinking-token contract

`count_thinking_tokens(generated_ids, tokenizer, *, max_new_tokens)` returns a frozen `ThinkingCount` with `status`, `thinking_token_count`, and `close_tag_index`.

Count generated token ids inside the thinking span. Do not decode the thinking text and tokenize it again.

Open sequence is the tokenizer encoding of `<think>` without special tokens. Close sequence is the encoding of `</think>` without special tokens. Exclude both tag sequences from the count.

- If an open tag is present, count ids after that open sequence and before the first close sequence.
- If no open tag is present and a close tag is present, count from index 0 to the close sequence. DeepSeek-R1-Distill may continue a think span that was opened in the prompt.
- `valid`: a close tag is present and `thinking_token_count > 0`
- `empty_thinking`: a close tag is present and `thinking_token_count == 0`
- `truncated`: no close tag, and `len(generated_ids) >= max_new_tokens`
- `missing_close_tag`: no close tag, and the output is shorter than `max_new_tokens`

## Runner contract

Model ids:

- `Qwen/Qwen3.5-4B`
- `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`

Messages for both models:

```python
[{"role": "user", "content": prompt}]
```

Qwen: `tokenizer.apply_chat_template(..., add_generation_prompt=True, enable_thinking=True)`. Do not append `<think>` by hand.

DeepSeek: `tokenizer.apply_chat_template(..., add_generation_prompt=True)`. Do not pass a system message. If the prompt does not already end with `<think>`, append `<think>\n` so the model is forced into a thinking span. The appended characters are prompt tokens, not generated tokens.

Sampling, from the model cards:

- Qwen thinking, general tasks: `do_sample=True`, `temperature=1.0`, `top_p=0.95`, `top_k=20`, `min_p=0.0`, `presence_penalty=1.5`, `repetition_penalty=1.0`
- DeepSeek-R1-Distill: `do_sample=True`, `temperature=0.6`, `top_p=0.95`

`max_new_tokens` is 2048 for `--smoke` and 8192 for the full run. If any smoke post is `truncated` at 2048, rerun that smoke at 8192 before Step 3. Do not raise the cap above 8192 without a plan revision.

`generation_seed(post_id)` is a stable 32-bit integer from `sha256(f"gen:{post_id}")`. Experiment 1 and experiment 2 use the same seed for the same post.

Statuses written per completion: `valid`, `empty_thinking`, `missing_close_tag`, `truncated`, `infrastructure`. Retry `infrastructure` with the same seed only. Do not resample a new seed.

Store the full generation text, thinking text, generated token ids for the thinking span, token count, status, model id, prompt arm, `post_id`, `group`, `post_1_role`, and seed.

Pytest must not download weights. Feed fake `generated_ids` and a tiny fake tokenizer that encodes `<think>` and `</think>` as known id sequences.

## Hugging Face Jobs

GPU inference runs on Hugging Face Jobs with `HF_TOKEN`. Flavor is `l4x1`. Timeout is 24 hours per job. Pass secrets `HF_TOKEN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `METRESEARCHGROUP_GITHUB_PAT_TOKEN`.

`jobs.py` builds the `hf jobs run` command that clones this repo at the current commit SHA, runs `uv sync`, then runs the experiment `run.py`. Do not add `huggingface_hub` to `pyproject.toml` unless the launcher cannot call the `hf` CLI.

Resume: skip `post_id` values already present in that model arm's traces file. Append each completion as it finishes.

## Pytest files

### `tests/test_render_prompt.py`

Class `TestRenderPrompt`.

```text
given original "o" and mirror "m" and post_1_role original and add_criteria false
when render_prompt
then the string contains "Post 1: o"
and contains "Post 2: m"
and ends with "Allow or Remove?"
and contains "There are no right or wrong answers"
and contains "political mirrors"
and does not contain "Allow Or Remove?"
and does not contain "Click Next"
and does not contain KEEP_REMOVE_FEATURES_ADDENDUM text

given the same posts and post_1_role mirror
when render_prompt
then Post 1 is m and Post 2 is o
and the instruction example still uses the website Original Text and Mirror Text abortion sample

given add_criteria true
when render_prompt
then KEEP_REMOVE_FEATURES_ADDENDUM appears after the judgment paragraph and before Post 1
```

### `tests/test_count_thinking_tokens.py`

Class `TestCountThinkingTokens`.

```text
given generated ids [open, 11, 12, close, 99]
when count_thinking_tokens
then status is valid and thinking_token_count is 2
and ids 11 and 12 are the counted span

given generated ids [open, close]
when count_thinking_tokens
then status is empty_thinking and count is 0

given generated ids with no close tag and length equal to max_new_tokens
when count_thinking_tokens
then status is truncated

given generated ids with no close tag and length less than max_new_tokens
when count_thinking_tokens
then status is missing_close_tag

given generated ids [11, 12, close] with no open tag
when count_thinking_tokens
then status is valid and count is 2
```

### `tests/test_generation_seed.py`

Class `TestGenerationSeed`.

```text
given post_id "A"
when generation_seed is called twice
then both integers are equal
and the integer is in 0 through 2**32 - 1
```

## Main caller

Pytest, including Step 1 tests:

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q
```

Expected: exit 0.

Thinking-mode smoke, after `HF_TOKEN` and AWS keys are set:

```bash
PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
```

Expected stdout includes `thinking_enabled=true` for both models, a thinking-token count greater than zero on each smoke post, and local smoke traces under `experiments/reasoning_during_moderation_2026_09_15/experiment1/smoke/`.

If the operator has no local GPU, the same flags run inside the Hugging Face Job from `jobs.py`. Pytest still must pass without a GPU.

## Must pass

- Golden prompt tests match the linked-fate website copy and the stored pair order.
- Thinking-token tests pass without loading a model.
- Smoke prints `thinking_enabled=true` for `Qwen/Qwen3.5-4B` and `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`.
- Each smoke post has `status=valid` and `thinking_token_count > 0`.
- `README.md` is unchanged.

## Must fail

- Importing `STUDY_PROMPT_TEMPLATE` from the prompt-engineering experiment.
- Closing with `Allow Or Remove?`.
- Dropping the no-right-or-wrong line.
- Sending twenty pairs in one prompt.
- Shuffling Post 1 and Post 2 again inside the renderer.
- Putting a DeepSeek system prompt.
- Decoding thinking text and retokenizing to get the count.
- Downloading model weights inside pytest.
- A smoke post with an empty thinking span counted as success.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `experiment1/run.py` `main --smoke` as the caller.

Phase 2 scaffolds `prompt.py`, `thinking.py`, `runner.py`, `jobs.py`, and `experiment1/run.py` with stub bodies.

Phase 3 locks signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files above.

Phase 5 implements in this order, one commit per unit of work:

1. `render_prompt` until `test_render_prompt.py` is green
2. `count_thinking_tokens` until `test_count_thinking_tokens.py` is green
3. `generation_seed`
4. runner wiring with sampling constants, still no weight download in tests
5. `experiment1/run.py --smoke` and `jobs.py`

Phase 6 is complete when shared pytest exits 0 and the smoke command can run.
