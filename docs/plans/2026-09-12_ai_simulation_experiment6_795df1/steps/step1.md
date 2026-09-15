# Step 1: Add the one-pair yes/no prompt, pair-level runner, stitch, tests, and experiment 6 folder

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment6/run.py` dispatched through `shared/run.py` `main` with `--experiment 6`
- **Slice:** prompt render → yes/no schema → pair-level `LabelTask` ids → stitch 20 answers → Claude rejection. Pytest only. No OpenAI, Bedrock, or S3 writes.
- **Out of scope:** `--smoke`, `--estimate-cost`, full `--model` labeling, `--score`, `RESULTS.md`, `COST_ESTIMATE.md`, `CHANGELOG.md`, experiment 1 through 5 artifacts, Claude labeling

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/plan.md` | Confirmed decisions |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` | Frozen `STUDY_SYSTEM_PROMPT` and `render_pairs`. Do not change the 20-pair string. |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` | `LlmRemoveIndexesModel`, `RemoveIndexesRow`, `remove_indexes_spec`, `expand_remove_indexes` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` | `parse_args`, `ordered_full_input`, `full_feature_paths`, `campaign_config_for_experiment`, `main` dispatch, `--experiment` choices `[1, 2, 3, 4, 5]` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/constants.py` | `POSTS_PER_USER`, model folder names, `CohortTrial` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` | `_load_final_labels` expects `source_record_id` = `prolific_id` and `remove_pair_indexes` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/run.py` | Thin `--experiment 1` wrapper to copy |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/README.md` | Banner plus one-question README |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner text |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_render_prompt.py` | Arrange-act-assert for prompt tests |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_expand_remove_indexes.py` | Failure cases for invalid indexes |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_full_label_paths.py` | Path and approval tests. Experiment 1 `--smoke` must keep working. |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/conftest.py` | `sample_user`, `sample_trials` |
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `LabelTask` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function, arrange-act-assert |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/SETUP.md` (new, prompt contract only; no filled live example yet)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/run.py` (new, same wrapper pattern as experiment 1 with `--experiment 6`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/constants.py` (add `EXPERIMENT6_MODEL_ORDER` and `PAIR_YES_NO_FEATURE_NAME`; do not remove Claude from `MODEL_ORDER`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` (add one-pair system prompt and `render_single_pair`; do not edit `STUDY_SYSTEM_PROMPT`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` (add yes/no models, `pair_yes_no_spec`, pair record-id helpers, stitch helper)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (`--experiment` include 6; pair-level `ordered_full_input` when experiment is 6; Claude rejection; do not change experiment 1 through 5 command behavior)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_render_prompt.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_pair_yes_no.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_full_label_paths.py` (add experiment 6 prefix and Claude-reject cases)

Do not write `RESULTS.md`, `COST_ESTIMATE.md`, or `APPROVAL.md` in this step.

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/shared/flip_generation/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/README.md` (agent read-only)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/APPROVAL.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment{1,2,3,4,5}/**` except you may read them
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` `STUDY_SYSTEM_PROMPT` string body
- Cohort parquet and all existing S3 objects

## README contract

`experiment6/README.md` must:

1. Start with the agent read-only banner from `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. State in one or two sentences that this run repeats experiment 1 with one unnumbered pair per yes/no call, without Claude.
3. Redirect to `SETUP.md` and `RESULTS.md`.

`experiment6/SETUP.md` must state:

- Humans judged one pair at a time. Experiment 6 does the same. Experiment 1 saw all 20 pairs in one prompt.
- Output field is `remove` with values `yes` or `no`.
- Models are OpenAI nano, Nova Micro, and Qwen 32B. Claude is excluded.
- Cohort is the existing 998 unique users. Do not rebuild it.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Do not pass unstructured dictionaries for source identity.

### `constants.py`

Add, without changing existing experiment 1 through 5 constants:

- `PAIR_YES_NO_FEATURE_NAME = "pair_yes_no"`
- `EXPERIMENT6_MODEL_ORDER = (MODEL_FOLDER_OPENAI, MODEL_FOLDER_BEDROCK_MICRO_NOVA, MODEL_FOLDER_BEDROCK_QWEN)`
- `PAIR_RECORD_SEPARATOR = ":"`

Leave `MODEL_ORDER` as the four-model tuple. Experiment 5 and experiment 1 through 4 still use it.

### `prompts.py`

Add `STUDY_SYSTEM_PROMPT_SINGLE_PAIR`. Copy the website instruction paragraph and the political-mirror example from `STUDY_SYSTEM_PROMPT`. Do not copy the sentence that says the model will see all 20 pairs. Close with: the user message contains one pair; return JSON `{"remove": "yes"}` or `{"remove": "no"}`; `yes` means remove both posts; `no` means keep both.

Add:

- `render_single_pair(trial: CohortTrial) -> str` returns `Post 1:\n{first}\n\nPost 2:\n{second}` using `_texts_for_pair_order`. No `## Post pair`. No integer pair index. No "of 20".
- Do not route experiment 6 through `render_user_prompt`. That function stays 20-pair ablations 1 through 4.

### `schema.py`

Add:

```text
LlmPairYesNoModel.remove: Literal["yes", "no"]  extra=forbid
PairYesNoRow.source_record_id: str
PairYesNoRow.label_timestamp: str
PairYesNoRow.remove: Literal["yes", "no"]
```

Add:

- `pair_yes_no_spec(engine_type) -> FeatureSpec` with `name=PAIR_YES_NO_FEATURE_NAME`, `model=PairYesNoRow`, `system_prompt=STUDY_SYSTEM_PROMPT_SINGLE_PAIR`, `llm_output_schema=LlmPairYesNoModel`
- `pair_record_id(prolific_id: str, pair_index: int) -> str` returns `{prolific_id}:{pair_index}`
- `parse_pair_record_id(record_id: str) -> tuple[str, int]` splits on the last `:`
- `parse_remove_yes_no(value: str) -> int` returns 1 for `yes`, 0 for `no`, raises `ValueError` otherwise
- `stitch_pair_predictions(rows: list[tuple[str, int, str]]) -> dict[str, list[int]]` where each tuple is `(prolific_id, pair_index, remove)`. For a user with exactly 20 distinct pair indexes in `1..20` and every `remove` in `{yes, no}`, return `prolific_id -> remove_pair_indexes` (1-indexed study indexes where `remove` is `yes`). Omit users with missing pairs, extra pairs, or invalid values.

Do not change `expand_remove_indexes` or `remove_indexes_spec`.

### `run.py`

- `--experiment` choices become `[1, 2, 3, 4, 5, 6]`.
- `experiment6/run.py --smoke` must not call `smoke_command()` (that path is experiment 1 four-model smoke). Step 1 may raise `SystemExit` for `--experiment 6` plus `--smoke` / `--estimate-cost` / `--model` / `--score` with a message that those flags land in later steps, or may stub the functions that Step 2 through 4 will fill. Bare `shared/run.py --smoke` without `--experiment 6` must still run the frozen experiment 1 smoke.
- `full_labels_root_uri(6)` is `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/`
- `ordered_full_input` for experiment 6 returns 20 ids per user, each `pair_record_id(prolific_id, pair_index)`, and texts from `render_single_pair`. User order matches `select_all_users`. Pair order matches `pair_index` 1 to 20.
- `campaign_config_for_experiment(6)` uses `campaign_id=ai_simulation_responses_2026_09_11_experiment6`.
- `--model bedrock_claude` with `--experiment 6` exits non-zero and names Claude as excluded. Do not create an experiment 6 Claude prefix.

## Tests (write first)

### `test_render_prompt.py`

1. Given `sample_trials[0]` with `pair_order` mirror then original, when `render_single_pair`, then the string starts with `Post 1:\nmirror-0` and contains `Post 2:\noriginal-0`, and does not contain `Post pair`, `of 20`, or `pair_index`.
2. Given `STUDY_SYSTEM_PROMPT_SINGLE_PAIR`, then it contains the website opening sentence and does not contain `20 post pairs` or `remove_pair_indexes`.
3. Given `STUDY_SYSTEM_PROMPT`, then it still contains `You will see all 20 post pairs` (frozen).

### `test_pair_yes_no.py`

1. Given `yes` on pairs 1 and 20, when stitch, then `remove_pair_indexes == [1, 20]` and `expand_remove_indexes` of that list is twenty binaries with 1 at both ends.
2. Given `no` on all 20 pairs, when stitch, then empty remove list.
3. Given 19 pairs for a user, when stitch, then that user is omitted.
4. Given `remove="maybe"`, when `parse_remove_yes_no`, then `ValueError`.
5. Given record id `abc:7`, when parse, then `("abc", 7)`.
6. Given `pair_yes_no_spec("openai").llm_output_schema`, then the schema forbids extra fields and accepts only `yes` and `no`.

### `test_full_label_paths.py`

1. Given experiment 6 and `openai`, when `full_feature_paths`, then prefix contains `experiment6/outputs/openai/` and does not contain `smoke/` or `bedrock_claude`.
2. Given `--experiment 6 --model bedrock_claude`, when `main`, then `SystemExit` with a nonzero code and the word `Claude`.
3. Given experiment 6 ordered input for one user with 20 trials, then there are 20 ids and 20 texts, and no text contains `Post pair`.

## Pass / fail

### Must pass before leaving this step

- [ ] `PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q` exits 0
- [ ] `STUDY_SYSTEM_PROMPT` is byte-for-byte unchanged from experiment 1
- [ ] `experiment6/run.py` exists and injects `--experiment 6`
- [ ] No OpenAI, Bedrock, or S3 `put_new` ran

### Must fail / must not happen

- [ ] Experiment 6 user text containing a pair number or `remove_pair_indexes`
- [ ] `MODEL_ORDER` losing Claude (breaks experiments 1 through 5 scoring)
- [ ] `shared/run.py --smoke` writing under `experiment6/`
- [ ] Creating `experiment6/outputs/bedrock_claude/`
- [ ] Editing parent `README.md`

## Commands

```bash
PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q
```

Expected: exit 0.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto for this step (user confirmed the plan).

Phase 1 caller is `experiment6/run.py` → `shared/run.py` `main`.

Phase 2 scaffold `experiment6/` files and new helpers with `NotImplementedError` only if tests are not yet written. Prefer writing the tests in Phase 4 then implementing.

Phase 5 units, one commit each if they split cleanly: (1) README/SETUP/wrapper, (2) one-pair prompt, (3) yes/no schema and stitch, (4) `run.py` pair-level ids and Claude rejection, (5) tests green.

Phase 6 is complete when pytest is green and no model was called.
