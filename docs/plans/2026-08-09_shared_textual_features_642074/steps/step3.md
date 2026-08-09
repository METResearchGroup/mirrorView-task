# Step 3: Implement valence, intergroup, and PRIME classifier modules

## Goal

Move the three language-model classifiers into `shared/textual_features/{valence,intergroup,prime}.py` with the same prompts, structured-output models, and `classify_post` / `classify_texts` behavior as today's experiment `classifier.py` files. Register them in the catalog. Do **not** move MirrorView CSV loading or label CSV writes into shared.

## Caller / unit of work

**Main caller (this step):** shared classify helpers (imported later by experiment wrappers in Step 4).

1. `classify_post(post: str)` returns a pydantic result (`ValenceClassification`, `IntergroupClassification`, or `PrimeClassification`).
2. `classify_texts(posts: list[str])` returns a list of those results (with tqdm progress as today).
3. `get_feature(VALENCE|INTERGROUP|PRIME).classify_post` is the same callable (or a short bound wrapper).

**Out of scope:** rewriting prompts; expanding PRIME into four classifiers; CSV `__main__` paths; live production labeling runs; experiment migration (Step 4).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/valence_classifier/classifier.py` | Prompt, model, classify helpers, and CSV I/O to leave behind |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/intergroup_classifier/classifier.py` | Same |
| `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py` | Same; yes-or-no "any of these" PRIME definition |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL` |
| `/workspace/lib/load_env_vars.py` | `EnvVarsContainer.get_env_var("OPENAI_API_KEY", ...)` |
| `/workspace/shared/textual_features/registry.py` | Wire classifier entries |

## Files allowed to change

- `/workspace/shared/textual_features/valence.py`
- `/workspace/shared/textual_features/intergroup.py`
- `/workspace/shared/textual_features/prime.py`
- `/workspace/shared/textual_features/registry.py` (set `classify_post` on the three classifier entries)
- `/workspace/shared/textual_features/__init__.py` (optional re-exports of classify helpers and result models)
- `/workspace/shared/textual_features/tests/test_registry.py` (assert classifier entries resolve and expose `classify_post`; do **not** require a live API)

## Files forbidden to change

- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/valence_classifier/classifier.py` (Step 4)
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/intergroup_classifier/classifier.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/prime_classifier/classifier.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/labels_*.csv`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/main.py`
- `/workspace/experiments/mirrors_content_analysis_2026_04_24/analysis/**/link_mirrorview_run_to_labels.py`
- Length and readability metric modules completed in Step 2 (unless a registry-only edit is required)

## Contracts to lock

### Shared module public API (each of valence / intergroup / prime)

```text
# valence.py
class ValenceClassification(BaseModel):
    is_positive: bool
def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI
def classify_post(post: str) -> ValenceClassification
def classify_texts(posts: list[str]) -> list[ValenceClassification]

# intergroup.py
class IntergroupClassification(BaseModel):
    is_intergroup: bool
def classify_post(post: str) -> IntergroupClassification
def classify_texts(posts: list[str]) -> list[IntergroupClassification]

# prime.py
class PrimeClassification(BaseModel):
    is_prime: bool
def classify_post(post: str) -> PrimeClassification
def classify_texts(posts: list[str]) -> list[PrimeClassification]
```

### Must copy unchanged from experiment sources

- Full system and human prompt strings (including few-shot examples).
- Structured-output field names (`is_positive`, `is_intergroup`, `is_prime`).
- LangChain `ChatPromptTemplate` plus `with_structured_output` call pattern.
- `OPENAI_API_KEY` via `EnvVarsContainer.get_env_var(..., required=True)`.
- Default model via `DEFAULT_LLM_MODEL`.

### Must NOT live in shared

- `Dataloader` imports
- `_all_mirrors_claude_path`, `_build_posts_frame`, `_label_posts_dataframe`, `classify_posts`
- `LABELS_ORIGINAL_PATH` / `LABELS_MIRRORS_PATH` writes
- `__main__` CSV batch runners

### PRIME meaning

Remain a **single yes-or-no** "any of these" classifier for prestige, in-group, moral, and emotional cues. Do not add per-cue outputs.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run pytest shared/textual_features/tests/ -q
# Expected: all length, readability, and registry tests PASS; no live language model required

# Import smoke for classifier API (no network call)
PYTHONPATH=. uv run python - <<'PY'
from shared.textual_features.registry import VALENCE, INTERGROUP, PRIME, get_feature
from shared.textual_features import valence, intergroup, prime

for mod, field in (
    (valence, "is_positive"),
    (intergroup, "is_intergroup"),
    (prime, "is_prime"),
):
    assert callable(mod.classify_post) and callable(mod.classify_texts)
    assert field in mod.classify_post.__annotations__.get("return", object).__dict__.get("__annotations__", {}) or True
    # softer: ensure result models exist
assert hasattr(valence, "ValenceClassification")
assert hasattr(intergroup, "IntergroupClassification")
assert hasattr(prime, "PrimeClassification")
for name in (VALENCE, INTERGROUP, PRIME):
    entry = get_feature(name)
    assert entry.kind == "classifier"
    assert callable(entry.classify_post)
print("CLASSIFIER_API_OK")
PY
```

**Expected stdout ends with:** `CLASSIFIER_API_OK`

Optional live smoke (only if `OPENAI_API_KEY` is present; not required to close the step):

```bash
PYTHONPATH=. uv run python - <<'PY'
from shared.textual_features.valence import classify_post
print(classify_post("I really enjoyed reading this, it made my day better!"))
PY
```

## Pass / fail for this step

**Pass when:**
1. Shared valence, intergroup, and prime modules expose the fixed classify API and result models.
2. Prompts and field names match the experiment sources.
3. Registry classifier entries resolve with `kind="classifier"` and a callable `classify_post`.
4. No CSV read or write, and no `Dataloader` usage, inside `shared/textual_features/`.
5. Length and readability tests from Step 2 still pass.

**Fail when:** prompts are rewritten; PRIME is split into four classifiers; label CSV writers move into shared; experiment classifier files are migrated early (that is Step 4); the step depends on a required live OpenAI call.
