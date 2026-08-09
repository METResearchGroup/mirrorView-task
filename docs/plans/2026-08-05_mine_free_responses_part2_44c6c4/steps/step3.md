# Step 3: Implement free-response LLM feature generation (with QA)

## Goal

Implement Part 2 Stage 1: batch free responses within one Likert group, call `research_tools.llm.runner.run` with **Part-2-owned** prompts/schemas (`gpt-5.4-nano`), write under `outputs/generated_features/{low,high}/`. Prompts use **open thematic categories** and **garbage/nonsense QA** (return zero features when the batch is clearly unusable). Do **not** reuse keep/remove post-linguistics prompts or schemas.

**Edit the draft prompts in this file before implementing** (section “Draft prompts”). Copy approved text into Part-2-local `src/prompts.py` (and `src/schemas.py`).

## Caller / unit of work

**Main caller (smoke / this step live check):**

```bash
PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \
  --likert-group low \
  --sample-size 10 \
  --docs-per-batch 10 \
  --seed 42
```

(and the same for `--likert-group high`)

**Production caller (Step 7 only):** omit sample cap or pass `--sample-size` ≥ group size so the **full** group is used; `--docs-per-batch 10`; seed `42`. Leftover docs that cannot fill a full batch are recorded as `leftover_participant_ids` and **not** sent to the LLM (same leftover policy as keep/remove).

**In scope:** Stage-1 module + Part-2-local `schemas.py` / `prompts.py`; runner wiring with tqdm via wrapped `writer_map_fn` (call-site reference: `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` and `experiments/llm_based_feature_generation_2026_07_31/stage1.py`).

**Out of scope:** embeddings, clustering, labeling, production full-corpus run, editing keep/remove prompts, editing parent README, putting Stage-1 prompts into `shared/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` | Runner call-site shape, sampling/batching, writer map |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Canonical `run(...)` + tqdm wrap |
| `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/paths.py` | Load/split + `stage1_root` from Step 2 |
| Research tools: `research_tools.llm.runner.run` | Writes `{output_base_path}/outputs/{timestamp}/` |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/schemas.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/prompts.py` (create)
- Runtime artifacts under `part_2_mine_free_responses/outputs/generated_features/{low,high}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/mine_free_response_for_features_2026_08_03/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/**`
- `/Users/mark/src/work/mirrorview-wt/shared/feature_discovery/**` (Stage-1 stays experiment-local)
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- Do **not** implement Stages 2–4 in this step

## Contracts

### Batch shape

Each runner item:

```python
{
  "batch_id": int,
  "likert_group": "low" | "high",
  "participant_ids": list[str],  # sorted unique ids in this batch
  "reflections": list[{
      "participant_id": str,
      "phase1_pair_reflection_text": str,
      "phase1_pair_influence_rating": int | float,
  }],
}
```

Rules:

1. Load via Step 2 helper; take only the requested `--likert-group`.
2. Sample `--sample-size` without replacement (`seed`). If `sample_size >= len(group_df)`, use the full group.
3. Batches of exactly `--docs-per-batch` (default **10**). Leftovers → `leftover_participant_ids` in run metadata; not sent to LLM.
4. Model id exactly `gpt-5.4-nano`.
5. Response cap **≤8 features per prompt**; **min length 0** (empty list allowed after QA reject).

### Response schema (Part-2-local)

Suggested fields (freeze names in `schemas.py`):

| Field | Role |
|-------|------|
| `batch_index` | Zero-based batch index |
| `qa_status` | `usable` \| `rejected_garbage` |
| `qa_notes` | Short reason when rejected; empty string when usable |
| `features` | List length 0–8 |

Each feature:

| Field | Role |
|-------|------|
| `participant_id` | Source document id (required) |
| `feature_name` | Short snake_case |
| `feature_value` | Human-readable value/description |
| `category` | Open thematic string (see draft categories below; not the keep/remove linguistic enum) |
| `is_open_ended` | bool |
| `evidence_span` | Short quote from the reflection text |
| `rationale` | One sentence |

When `qa_status == rejected_garbage`, `features` **must** be empty.

### Writer map

Persist at least: `batch_id`, `likert_group`, `participant_ids`, `feature_count`, `qa_status`, `result` (model dump).

### Output location

`research_tools` runner with `output_base_path=stage1_root(likert_group)` → artifacts under:

`part_2_mine_free_responses/outputs/generated_features/{low|high}/outputs/{timestamp}/`

## Draft prompts

**Edit before implementing.**

### Open thematic categories (guidance, not a rigid checklist)

Use category strings such as:

- `pair_comparison_strategy` — how they compared original vs mirror
- `decision_criteria` — rules/thresholds for keep vs remove
- `affect_or_confidence` — certainty, discomfort, indifference
- `content_cues` — topics, toxicity, partisanship, framing they claim to use
- `process_meta` — task understanding, confusion, ignoring the pair
- `other` — salient theme that does not fit above

Do **not** copy the keep/remove six-category linguistic checklist.

### System prompt skeleton (low; mirror for high with group wording)

```text
You are analyzing free-response reflections from participants who rated how much
seeing both versions of a post (original + political mirror) influenced their
keep/remove decisions.

This batch contains ONLY participants in the LOW influence group
(Likert rating < 4: seeing the pair influenced them little).

Each item has participant_id, phase1_pair_reflection_text, and their Likert rating.

## QA gate (do this first)
- If the batch is clearly garbage or nonsense (keyboard smash, empty meaning,
  unrelated spam, copy-paste gibberish, or text that cannot be interpreted as a
  reflection about the task), set qa_status=rejected_garbage, put a short reason
  in qa_notes, and return features=[] (empty).
- Borderline but readable reflections should be treated as usable.

## Feature extraction (only if qa_status=usable)
- Extract themes that characterize what participants say influenced (or failed to
  influence) their paired keep/remove judgments.
- Be conservative: include a feature ONLY if highly confident.
- At most 8 features total across the batch; each must include participant_id.
- Use open thematic categories (pair_comparison_strategy, decision_criteria,
  affect_or_confidence, content_cues, process_meta, other).
- Provide evidence_span quoted from the reflection text.
- Do NOT invent keep/remove labels for posts. Do NOT use post-linguistics checklists
  from other experiments.
- Return structured JSON matching the Part-2 schema (qa_status, qa_notes, features).
```

User template: dump `reflections` as JSON for the batch.

High group: same QA + themes; state Likert `>= 4` / high influence wording.

## Exact commands

### Offline import check

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src import llm_generate_features as m
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.schemas import BatchFeatureGeneration
assert hasattr(m, 'main')
# empty features must be schema-valid
BatchFeatureGeneration.model_validate({
  'batch_index': 0,
  'qa_status': 'rejected_garbage',
  'qa_notes': 'keyboard smash',
  'features': [],
})
print('step3 stage1 wiring OK')
"
```

### Live smoke (requires `OPENAI_API_KEY` in repo-root `.env`)

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \
  --likert-group low --sample-size 10 --docs-per-batch 10 --seed 42
```

Expected: one feature-gen prompt; JSON under `outputs/generated_features/low/outputs/<ts>/`; print/path to run dir. QA may yield empty features for garbage samples — that is success if schema/qa_status are correct.

### Fail criteria

- Reuses keep/remove `FeatureCategory` / post prompts from `create_llm_features`
- Puts Stage-1 prompts into `shared/`
- Parent README edited
- Empty features disallowed by schema (blocks QA)
- Production full-corpus run in this step

## Done when

1. Stage-1 CLI works for low and high with Part-2-owned prompts/schemas.
2. QA reject path validates with `features=[]`.
3. Artifacts land under `outputs/generated_features/{low,high}/outputs/{ts}/`.
4. Draft prompts above (or user-edited revisions) are what the module uses.
