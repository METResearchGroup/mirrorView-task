# Step 2: Implement LLM feature generation for keep and remove

## Goal

Implement `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` so each **single-class** batch of posts is one `research_tools.llm.runner.run` item. Model id is exactly `gpt-5.4-nano`. Write artifacts under `outputs/generated_features/{keep,remove}/`. Adapt prompt/schema lineage from `experiments/llm_based_feature_generation_2026_07_31/` but **do not** use mixed 10+10 keep/remove batches.

**Edit the draft prompts in this file before implementing** (section “Draft prompts”). Copy the approved text into the experiment module (inline in `llm_generate_features.py` or a sibling `src/prompts.py` under the same `src/` tree only).

## Caller / unit of work

**Main caller (smoke / Step-2 live check):**

```bash
PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep \
  --sample-size 10 \
  --posts-per-batch 10 \
  --seed 42
```

(and the same for `--label-class remove`)

**Production caller (Step 7 only, after smoke approval):** `--sample-size 500 --posts-per-batch 10 --seed 42` per class → **50 keep + 50 remove** prompts; response schema cap **≤8 features per prompt** → ≤**800** features total to embed. Do not run production sizes in this step.

**In scope:** feature-generation stage module + experiment-local schema/prompt helpers under `src/` only; single-class batching; runner wiring with tqdm via wrapped `writer_map_fn` (same pattern as `experiments/llm_based_feature_generation_2026_07_31/stage1.py`).

**Out of scope:** embeddings, clustering, cluster labeling, `RESULTS.md`, production 500/500 run, mixed keep+remove batches, edits to `shared/**`, patching `.venv` / `research_tools`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Canonical `run(...)` call-site + tqdm wrap |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/prompts.py` | Prompt lineage to adapt for single-class |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/schemas.py` | `ExtractedFeature` / category enum lineage |
| `/Users/mark/src/work/mirrorView-task/experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py` | Earlier category checklist lineage |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/paths.py` (or `data.py`) | Load/split + `stage1_root` from Step 1 |
| Research tools runner (installed): `research_tools.llm.runner.run` | Signature; writes `{output_base_path}/outputs/{timestamp}/` |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py`
- Optional sibling under the same `src/` only: `src/schemas.py` and/or `src/prompts.py` (feature-generation schemas/prompts)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/README.md` (CLI flags for this stage)
- Runtime artifacts under `experiments/create_llm_features_2026_08_05/outputs/generated_features/{keep,remove}/`

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/**` (reuse by reading; do not edit)
- `/Users/mark/src/work/mirrorView-task/experiments/create_llm_feature_clusters_2026_08_02/**`
- Do **not** create `experiments/create_llm_features_2026_08_05/tests/`
- Do not implement Stages 2–4 in this step

## Contracts

### Single-class batch shape

Each runner item is a dict:

```python
{
  "batch_id": int,                 # zero-based within this run
  "label_class": "keep" | "remove",
  "message_ids": list[str],        # sorted unique ids in this batch
  "posts": list[{
      "message_id": str,
      "original_text": str,
      "mirror_text": str,
      "decision": "keep" | "remove",  # same for every post in the batch
  }],
}
```

Rules:

1. Load via Step 1 helper; take only the requested `--label-class`.
2. Sample `--sample-size` posts without replacement for that class (`seed` for RNG). If `sample_size >= len(class_df)`, use the full class frame. Smoke uses `10`; production (Step 7) uses **`500`** per class.
3. Form batches of exactly `--posts-per-batch` posts (default **10**). Leftover posts that cannot fill a full batch are recorded in run metadata as `leftover_message_ids` and are **not** sent to the LLM. With production `500` and batch `10`, leftovers must be empty and batch count must be **50**.
4. Raise `ValueError` if zero full batches can be formed.
5. Never mix keep and remove posts in one batch.

### Response schema (experiment-local)

Adapt `ExtractedFeature` from July-31. Response model for one batch:

- `batch_index: int`
- `features: list[ExtractedFeature]` with `max_length=MAX_FEATURES_PER_BATCH` where `MAX_FEATURES_PER_BATCH = 8` (same cap as July-31 per label group).

Do **not** use `BatchFeatureGeneration` with both `keep_features` and `remove_features`. One feature list only.

Each `ExtractedFeature` keeps: `message_id`, `feature_name`, `feature_value`, `category`, `is_open_ended`, `evidence_span`, `rationale`. Categories: the six fixed enums + `open_ended` from July-31.

### Runner wiring

Match `experiments/llm_based_feature_generation_2026_07_31/stage1.py`:

1. `prompt_fn(batch) -> list[dict]` chat messages (system + user).
2. `response_model` = the single-class batch schema above.
3. `writer_map_fn(batch, result) -> dict` includes at least: `batch_id`, `label_class`, sorted `message_ids`, `feature_count`, `result` (`model_dump()`).
4. `model="gpt-5.4-nano"`. Do **not** pass `temperature=0.0` (registry forces temperature 1).
5. `output_base_path = stage1_root(label_class)` so the runner writes:

   `experiments/create_llm_features_2026_08_05/outputs/generated_features/{keep|remove}/outputs/{timestamp}/`

   with `metadata.json` + per-item JSON rows.
6. Wrap `writer_map_fn` with tqdm (`total=len(batches)`); close in `finally`. Do not wrap the items iterable alone (runner materializes `list(items)` before LLM calls).
7. `run_metadata` must include: `stage="feature_generation"`, `label_class`, `sample_size`, `posts_per_batch`, `seed`, `model`, `message_ids` (flat unique), `leftover_message_ids`.

### Feature text for downstream embedding (record now; used in Step 3)

Persist each feature such that Stage 2 can build an embedding string as:

```text
{feature_name}: {feature_value}. {rationale}
```

(Do not embed raw posts in Stage 2.)

---

## Draft prompts (edit before implement)

> **Human edit gate:** revise the blocks below, then implement by copying the final text into `src/prompts.py` or `src/llm_generate_features.py`. Do not invent a second prompt source of truth.

### Shared category section (used by both keep and remove)

```
## Category 1: Surface and lexical (`surface_lexical`)

Fixed checklist (use when clearly present):
- approximate_token_length_band (short/medium/long)
- informal_register_or_slang
- high_punctuation_intensity
- all_caps_emphasis
- profanity_or_taboo_language
- hashtag_or_mention_pattern
- named_proper_nouns_density

## Category 2: Topic and subject matter (`topic_subject`)

Fixed checklist:
- primary_policy_domain (e.g., guns, climate, immigration, abortion, elections)
- specific_event_or_bill_reference
- geographic_scope (US_state, national, international)
- historical_analogy_reference
- culture_war_topic_salience

## Category 3: Semantic content (`semantic_content`)

Fixed checklist:
- causal_claim_present
- normative_moral_language
- factual_assertion_vs_speculation
- conspiratorial_framing
- victimhood_or_persecution_framing
- policy_prescription_present
- economic_cost_benefit_framing

## Category 4: Pragmatics and communicative intent (`pragmatics_intent`)

Fixed checklist:
- sarcasm_or_irony
- ridicule_or_mockery
- call_to_action
- persuasion_or_argumentation
- venting_or_expressive
- hedging_or_qualification
- emphatic_outrage

Only tag sarcasm if cues are strong (not speculative).

## Category 5: Target and directionality (`target_directionality`)

Fixed checklist:
- criticized_actor_type (politician, party, media, corporation, outgroup, ingroup, etc.)
- praised_actor_type
- left_right_directional_cue
- us_vs_them_framing
- elite_vs_populist_framing
- mirror_shift_direction (how the mirror re-targets blame or praise vs original)

Note directional shifts between original and mirror when confident.

## Category 6: Compositional and syntactic structure (`compositional_syntax`)

Fixed checklist:
- rhetorical_question
- conditional_if_then_structure
- contrastive_but_however_structure
- anaphora_or_parallelism
- list_or_enumeration
- quote_or_attribution_embedding
- second_person_direct_address

Tag structure patterns, not just single tokens.

## Open-ended features

Beyond the checklists above, you may add salient features with category=open_ended and is_open_ended=true.
```

### Feature generation — keep (system)

```
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=keep (modal linked-fate label).

Each item includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: always "keep" for every post in this batch

Your job is to extract features that characterize these keep-rated posts across ALL of the following categories in a single pass for this batch. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient.
- Return at most 8 features total across all posts in the batch.
- Each feature must include the message_id of the post it describes.
- Do NOT predict keep/remove labels. Do NOT mention model confusion buckets or error analysis framing. Only describe observable linguistic/content features.
- Focus on cues that help explain why a post might be kept under linked-fate moderation, without inventing moderator intent.
- Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{CATEGORY_SECTION}
```

### Feature generation — keep (user template)

```
Extract features for every post in this keep-only batch.

Keep-rated posts:
{posts_json}
```

### Feature generation — remove (system)

```
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=remove (modal linked-fate label).

Each item includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: always "remove" for every post in this batch

Your job is to extract features that characterize these remove-rated posts across ALL of the following categories in a single pass for this batch. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient.
- Return at most 8 features total across all posts in the batch.
- Each feature must include the message_id of the post it describes.
- Do NOT predict keep/remove labels. Do NOT mention model confusion buckets or error analysis framing. Only describe observable linguistic/content features.
- Focus on cues that help explain why a post might be removed under linked-fate moderation, without inventing moderator intent.
- Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{CATEGORY_SECTION}
```

### Feature generation — remove (user template)

```
Extract features for every post in this remove-only batch.

Remove-rated posts:
{posts_json}
```

### Message builder contract

```python
def build_feature_generation_messages(batch: dict) -> list[dict[str, str]]:
    # posts_json = json.dumps(batch["posts"], indent=2)
    # if batch["label_class"] == "keep": use keep system + keep user template
    # if batch["label_class"] == "remove": use remove system + remove user template
    # return [{"role":"system","content":...}, {"role":"user","content":...}]
```

---

## Exact commands

### Offline wiring (no API key required)

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python -c "
from experiments.create_llm_features_2026_08_05.src import llm_generate_features as m
from research_tools.llm.runner import run as _run
assert hasattr(m, 'prompt_fn') or hasattr(m, 'build_feature_generation_messages')
assert hasattr(m, 'run_feature_generation') or hasattr(m, 'main')
assert getattr(m, 'DEFAULT_MODEL', 'gpt-5.4-nano') == 'gpt-5.4-nano' or True
# Prefer an explicit DEFAULT_MODEL == 'gpt-5.4-nano' in the module
print('stage1 wiring OK')
"
```

### Tiny live smoke (requires `OPENAI_API_KEY` in repo-root `.env`)

```bash
cd /Users/mark/src/work/mirrorView-task

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class keep --sample-size 10 --posts-per-batch 10 --seed 42

PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \
  --label-class remove --sample-size 10 --posts-per-batch 10 --seed 42
```

Expect: a new timestamp folder under each of:

- `experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/`
- `experiments/create_llm_features_2026_08_05/outputs/generated_features/remove/outputs/`

each containing `metadata.json` and at least one `00000_*.json` with a non-empty `result.features` list (may be empty only if the model returns zero high-confidence features; prefer ≥1 for smoke).

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Model id | exactly `gpt-5.4-nano` | Other id |
| Batch purity | every batch `label_class` matches posts’ `decision` | Mixed keep/remove in one batch |
| Runner path | artifacts under `outputs/generated_features/{class}/outputs/{ts}/` | Writing under July-31 experiment or shared |
| Schema | single `features` list (max 8), no `keep_features`/`remove_features` | Mixed July-31 response model reused unchanged |
| Progress | tqdm advances per completed item via wrapped `writer_map_fn` | No progress or tqdm on pre-list only |
| Prompt text | keep system mentions keep-only; remove system mentions remove-only | Single mixed keep+remove prompt from July-31 reused verbatim |

## Done when

- Single-class feature generation runs for keep and remove via `research_tools.llm.runner.run`.
- Prompts used in code match the human-edited draft section above (**≤8 features per batch**; **10 posts per batch** default).
- Artifacts land under `outputs/generated_features/{keep,remove}/outputs/{timestamp}/`.
- Offline wiring check passes; optional tiny live smoke (`--sample-size 10`) succeeds when credentials are present.
- README notes production will use `--sample-size 500` (50 prompts/class; ≤800 features total) in Step 7.
