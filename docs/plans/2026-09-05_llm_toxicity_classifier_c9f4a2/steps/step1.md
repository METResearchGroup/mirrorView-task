# Step 1: Add the LLM toxicity feature and register it

## Goal

Add an LLM toxicity classifier that returns `low`, `medium`, or `high`, with a system prompt, few-shot examples, and Pydantic models matching the other LLM features. Register it so platform feature generation can run it. Keep Perspective toxicity and curation unchanged.

## Caller / unit of work

**Main caller:** `generate_feature()` in `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py`, plus `FEATURE_REGISTRY` in `/workspace/data_platform/generate_features/registry.py`.

**Slice:** prompt + structured LLM schema + persisted row model + `generate_feature(uri, text)` + registry entry with `engine_type="langchain"`.

**Out of scope:** Perspective client and `is_toxic_tiered`; curation join columns; OpenAI Batch engine internals; experiment smoke (Step 2); swapping production toxicity off Perspective.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/generate_features/is_political/generate_feature.py` | Boolean LLM feature shape: prompt, few-shots, LLM schema, row model, `generate_feature` |
| `/workspace/data_platform/generate_features/political_stance/generate_feature.py` | Multi-class LLM feature shape (`Literal` labels + few-shots) |
| `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py` | Three-class LLM feature to copy most closely |
| `/workspace/data_platform/generate_features/is_toxic_tiered/generate_feature.py` | Existing Perspective three-class labels. Do not edit. |
| `/workspace/data_platform/generate_features/registry.py` | Where the new spec must be added |
| `/workspace/tests/data_platform/generate_features/test_is_likely_spam.py` | Mocked `generate_feature` + registry membership test pattern |
| `/workspace/tests/data_platform/generate_features/test_langchain_engine.py` | Registry engine_type vs `generate_fn` invariant |
| `/workspace/data_platform/curate/consolidate.py` | Confirms curation still keys Perspective only. Do not edit. |

## Files allowed to change

- `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` (create)
- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/tests/data_platform/generate_features/test_llm_toxicity_tiered.py` (create)
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` (add the new feature name to the existing registry list only)

Plan package files under `/workspace/docs/plans/2026-09-05_llm_toxicity_classifier_c9f4a2/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/generate_features/is_toxic_tiered/generate_feature.py`
- `/workspace/ml_tooling/perspective_api.py`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/engines/**`
- `/workspace/data_platform/generate_features/is_political/generate_feature.py`
- `/workspace/data_platform/generate_features/political_stance/generate_feature.py`
- `/workspace/data_platform/generate_features/is_news_or_opinion/generate_feature.py`
- `/workspace/data_platform/generate_features/is_likely_spam/generate_feature.py`
- `/workspace/data_platform/generate_features/is_self_contained/generate_feature.py`
- `/workspace/data_platform/generate_features/is_structurally_complete/generate_feature.py`
- `/workspace/data_platform/generate_features/smoke_openai_engine.py`

## Contracts to lock

Feature name in the registry: `llm_toxicity_tiered`.

`engine_type="langchain"`. `generate_fn` must be `None`. Set `system_prompt` and `llm_output_schema`.

```text
ToxicityTier = Literal["low", "medium", "high"]

class LlmToxicityTieredOutputModel(BaseModel):
    toxicity_tier: ToxicityTier

class LlmToxicityTieredModel(BaseModel):
    source_record_id: str
    label_timestamp: str
    toxicity_tier: ToxicityTier

def generate_feature(uri: str, text: str) -> LlmToxicityTieredModel
  structured_chat_completion(
      user_prompt=text,
      output_schema=LlmToxicityTieredOutputModel,
      system_prompt=SYSTEM_PROMPT,
  )
  wrap with source_record_id=uri and label_timestamp=get_current_timestamp()
```

Do not add `toxicity_prob`. That field stays on Perspective only.

`SYSTEM_PROMPT` must:

- Define `low`, `medium`, and `high` for short social media text.
- Include at least two few-shot examples per class (six examples total).
- Tell the model to return only the structured fields.

Class meanings (qualitative match to the existing Perspective tiers, not numeric cutoffs):

- `low`: civil, no insults, no threats, no slurs.
- `medium`: rude, insults, hostility, or mild targeted profanity, without threats, slurs, or dehumanization.
- `high`: threats, slurs, dehumanization, or wishing harm.

Registry spec:

```text
FEATURE_REGISTRY["llm_toxicity_tiered"] = FeatureSpec(
    name="llm_toxicity_tiered",
    model=LlmToxicityTieredModel,
    engine_type="langchain",
    system_prompt=SYSTEM_PROMPT,
    llm_output_schema=LlmToxicityTieredOutputModel,
)
```

Insert it after `is_toxic_tiered` and before `political_stance` so the dict stays grouped with the other toxicity feature.

## Test design

Pseudocode then real tests. Prefer the public `generate_feature` and `FEATURE_REGISTRY` APIs. Mock `structured_chat_completion`. Do not call OpenAI.

```text
given FEATURE_REGISTRY
when looking up "llm_toxicity_tiered"
then the spec exists
and engine_type == "langchain"
and generate_fn is None
and system_prompt is a non-empty string
and llm_output_schema is LlmToxicityTieredOutputModel
and model is LlmToxicityTieredModel

given structured_chat_completion returns toxicity_tier="high"
and get_current_timestamp returns "2026-09-05T00:00:00Z"
when generate_feature("at://example/post/1", "you should disappear")
then result is LlmToxicityTieredModel
and source_record_id == "at://example/post/1"
and label_timestamp == "2026-09-05T00:00:00Z"
and toxicity_tier == "high"

given structured_chat_completion returns toxicity_tier="low"
when generate_feature("at://example/post/2", "thanks for the discussion")
then toxicity_tier == "low"

given structured_chat_completion returns toxicity_tier="medium"
when generate_feature("at://example/post/3", "that take is pretty rude")
then toxicity_tier == "medium"
```

Existing registry tests in `/workspace/tests/data_platform/generate_features/test_langchain_engine.py` and `/workspace/tests/data_platform/generate_features/test_metadata.py` must stay green. The langchain registry loop already treats `langchain` specs as prompt/schema features with no `generate_fn`.

## Implementation notes (implement-from-spec)

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit. Full auto. Do not wait for Phase 3 approval.

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Create `/workspace/data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` with `SYSTEM_PROMPT = ""`, empty model classes, and `generate_feature` raising `NotImplementedError`. Add a registry import stub only if it still imports; otherwise leave registry unchanged until the models exist. Prefer: registry still unchanged in scaffold if importing empty models would break collection. Create the test file only in Phase 4.
3. Phase 3 contracts. Lock the signatures and Pydantic fields above. Bodies stay stubs. `SYSTEM_PROMPT` may stay empty.
4. Phase 4 test design. Add `/workspace/tests/data_platform/generate_features/test_llm_toxicity_tiered.py` from the pseudocode. Tests must fail for `NotImplementedError` or missing registry key, not missing imports.
5. Phase 5 units, in this order, one commit each:
   1. Fill `SYSTEM_PROMPT` with class definitions and six few-shot examples.
   2. Implement `generate_feature`.
   3. Register `llm_toxicity_tiered` in `FEATURE_REGISTRY` and add the name to the runbook feature list.
6. Phase 6. Run the must-pass command. Confirm Perspective and curation files are unchanged.

Do not add an `__init__.py` under the feature folder. Other feature folders do not have one.

File-level docstring must include:

```text
PYTHONPATH=. uv run python data_platform/generate_features/llm_toxicity_tiered/generate_feature.py
```

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/generate_features -q
```

Expected: exit 0. New tests collected and passing. Existing langchain registry and metadata tests still passing.

## Must fail / not happen

- `is_toxic_tiered` or Perspective files changed.
- Curation files changed.
- Registry spec using `engine_type="thread_pool"` or setting `generate_fn`.
- Row model including `toxicity_prob`.
- Live OpenAI calls in unit tests.
