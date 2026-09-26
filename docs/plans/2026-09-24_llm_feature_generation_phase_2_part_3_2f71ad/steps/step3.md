# Step 3: LLM batch feature generation (discovery half only)

Run mixed-contrast and single-class LLM feature discovery on the discovery split only. Run it separately for each text arm (`original_only`, `mirror_only`, `paired`). **Keep the finished production mixed run** on the original Part 3 discovery half (Part 3 majority labels at run time). About 12% of those discovery posts now have a different union majority label; document this label-drift caveat in run metadata and SETUP.md. Discovery only proposes features; all Q1 through Q7 tests use union labels on held-out posts. **Add a top-up mixed run** on new discovery posts only (about 550 Part-2-only posts), with `batch_design=mixed_topup` in a new run directory per arm. Step 4 reads both the main mixed run and the top-up run.

## Scope

- **Caller / entrypoint:** `generate_features` CLI (`if __name__ == "__main__"`).
- **In scope:**
  - `batching.py`: form mixed batches (10 keep + 10 remove), top-up batches on Part-2-only discovery posts (`mixed_topup`), and single-class batches (10 posts per batch, 500 keep + 500 remove sampled per arm) from discovery-split cohort rows.
  - `prompts.py`: **all** LLM prompt templates for this experiment, including discovery prompts per arm and batch design, cluster labeling (`build_cluster_label_messages`), and post labeling through a prompt builder that prepends the codebook as a fixed prefix.
  - `schemas.py`: **all** LLM response schemas for this experiment, including discovery models (`ExtractedFeature`, `BatchFeatureGeneration`, `SingleClassBatchFeatureGeneration`), cluster labeling (`ClusterLabelResult`), and post labeling (per-text present/absent schema).
  - `llm_client.py`: LiteLLM structured completion, per-call JSON artifacts, `metadata.json`, spend logging, spend cap enforcement.
  - `generate_features.py`: smoke (Phase 0 LiteLLM probe + 1 mixed batch per arm), production mixed (existing run retained; optional rerun flag), production `mixed_topup` on new discovery posts only, production single-class ablation.
  - `smoke_tests/run_smoke_discovery.py`: packaged smoke runner.
  - Unit tests with mocked LiteLLM (no network in pytest).
- **Out of scope:**
  - Embeddings, clustering, codebook, labeling, analysis (Steps 4-7).
  - Held-out test split posts (never send to the LLM in this step).
  - Editing `shared/`, other `experiments/*`, or Step 1/2 modules except reading them.
  - Human approval file creation (the user writes `outputs/shared/approval_step3_production.json` after reviewing smoke).

## Files to inspect (read-only)

Read the reference implementations below before writing new modules. They define batch shapes, prompt patterns, and artifact fields this step must match.

- `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` - single-class batch CLI, `form_single_class_batches`, writer row shape.
- `experiments/create_llm_features_2026_08_05/src/prompts.py` - category checklist, single-class system prompts.
- `experiments/create_llm_features_2026_08_05/src/schemas.py` - `ExtractedFeature`, `SingleClassBatchFeatureGeneration`, `FeatureCategory`.
- `experiments/llm_based_feature_generation_2026_07_31/batching.py` - `form_batches` for mixed 10+10 design.
- `experiments/llm_based_feature_generation_2026_07_31/prompts.py` - mixed-batch system prompt and `build_feature_generation_messages`.
- `experiments/llm_based_feature_generation_2026_07_31/schemas.py` - `BatchFeatureGeneration`, `MAX_KEEP_FEATURES_PER_BATCH`, `MAX_REMOVE_FEATURES_PER_BATCH`.
- `experiments/llm_based_feature_generation_2026_07_31/stage1.py` - `prompt_fn`, `writer_map_fn`, run metadata fields.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/paths.py`: `discovery_run_dir`, `cost_log_path`, `make_run_timestamp`, `latest_timestamp_subdir` (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/constants.py` - `LLM_MODEL_ID`, `LLM_REASONING_EFFORT`, `TEXT_ARMS`, batch design constants, spend cap (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/cohort.py` - load cohort parquet with `split == "discovery"` (from Step 1).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/data/post_split/discovery_post_ids.csv` - committed discovery IDs (from Step 1).

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/batching.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/prompts.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/schemas.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/llm_client.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/generate_features.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/smoke_tests/run_smoke_discovery.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batching.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_prompts.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_schemas.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_llm_client.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_features.py` - create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/**`: discovery JSON, `metadata.json`, `cost_log.jsonl` (gitignored).
- `pyproject.toml` and `uv.lock`: add LiteLLM dependency (required; see Dependency check below).

## Files forbidden to change

- `shared/` (read-only).
- Other `experiments/*` (no cross-experiment imports).
- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md` and sibling step files.
- Step 1 modules: `paths.py`, `constants.py`, `cohort.py`, `split.py`, `s3_sync.py` (read-only).
- Step 2 `baselines.py` (read-only).
- `lib/` (read-only).

## Dependency check (run before Phase 2)

Add LiteLLM before any implementation work. Confirm the lockfile pin, install the package, and verify the import.

```bash
# Verify pinned version in uv.lock
rg -n -A2 '^name = "litellm"' /workspace/uv.lock

# Add LiteLLM (required for Step 3)
uv add 'litellm==1.84.0'

PYTHONPATH=. uv run python -c "import litellm; print('litellm_ok')"
```

Step 3 **must** run `uv add 'litellm==1.84.0'` and update `pyproject.toml` and `uv.lock`. Do this even if a local import check already succeeds.

## Contract overrides (orchestrator)

The orchestrator contract differs from the older `research_tools` runner in three ways:

1. **Timestamp format:** use `%Y-%m-%dT%H-%M-%S` local time for every output folder and per-call JSON filename (not `research_tools` runner `%Y_%m_%d-%H:%M:%S`).
2. **`llm_client.py`:** call `litellm.completion` directly with `model="openai/gpt-6-luna"` and `reasoning_effort="none"` on every call. Do not import `research_tools.llm.runner`.
3. **Per-call artifacts:** `llm_client` writes its own JSON files (request, response, usage including `reasoning_tokens`) plus run-level `metadata.json`. Match row field names from Section 6.3, but do not copy the `research_tools` runner output layout.

## Implementation phases (TDD - mandatory order)

Complete phases in order. Make one git commit per phase, or one commit per unit of work in Phase 5. Do not skip a phase.

| Phase | Goal | Gate |
|-------|------|------|
| 1 - Scope | Name caller, file tree, out-of-scope | Caller + tree listed in commit message |
| 2 - Scaffold | Create modules; stub bodies only | Imports resolve; `raise NotImplementedError` |
| 3 - Contracts | Types, signatures, schemas; no business logic | Matches contract Section 6.3; stubs only |
| 4 - Test design | Pseudocode to failing tests (happy + key failures) | Tests fail for the right reason |
| 5 - Implement | One function/path per commit until green | Targeted tests pass |
| 6 - Done | Full step pytest + CLI smoke (mocked in tests) | All pass/fail criteria met |

### Phase 1 - Scope details

**Caller:** `experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features`

**File tree (this step creates):**

```text
experiments/llm_feature_generation_phase_2_part_3_2026_09_24/
  src/
    batching.py
    prompts.py
    schemas.py
    llm_client.py
    generate_features.py
  smoke_tests/
    run_smoke_discovery.py
  tests/
    test_batching.py
    test_prompts.py
    test_schemas.py
    test_llm_client.py
    test_generate_features.py
  outputs/
    <arm>/discovery/outputs/<run_timestamp>/
    shared/cost_log.jsonl
```

**Batch counts (discovery half after union Step 1, per arm):**

| Design | Posts used | Batch size | Expected batches |
|--------|------------|------------|------------------|
| `mixed` (primary; existing production run) | original Part 3 discovery keep + remove | 10 keep + 10 remove | about 287 (unchanged run artifact) |
| `mixed_topup` | new Part-2-only discovery posts only | 10 keep + 10 remove | about 28 (about 550 posts) |
| `single_class` (ablation) | 500 keep + 500 remove sampled | 10 per batch | 50 keep + 50 remove = 100 per arm |

### Phase 3 - Contract signatures

**`batching.py`**

```python
def load_discovery_cohort(arm: str) -> pd.DataFrame: ...

def form_mixed_batches(
    cohort: pd.DataFrame,
    *,
    keep_per_batch: int = 10,
    remove_per_batch: int = 10,
) -> list[dict[str, Any]]: ...

def form_single_class_batches(
    cohort: pd.DataFrame,
    *,
    keep_sample_size: int = 500,
    remove_sample_size: int = 500,
    posts_per_batch: int = 10,
    seed: int,
) -> list[dict[str, Any]]: ...
```

Each batch dict must include `batch_id`, `arm`, `batch_design`, `message_ids` (list of `post_id` strings), and post lists keyed for prompts (`keep_posts` / `remove_posts` for mixed; `posts` + `label_class` for single_class). Post dicts use `post_id` as `message_id` in prompt payloads so they match Part 2 JSON field names.

**`llm_client.py`**

```python
class SpendCapExceeded(Exception): ...

def make_run_timestamp() -> str: ...  # strftime("%Y-%m-%dT%H-%M-%S")

def read_cumulative_cost_usd() -> float: ...

def append_cost_log(
    *,
    stage: str,
    arm: str | None,
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    cost_usd: float,
) -> float: ...  # returns new cumulative_cost_usd

def complete_structured(
    messages: list[dict[str, str]],
    response_model: type[BaseModel],
    *,
    stage: str,
    arm: str | None,
    call_index: int,
    output_dir: Path,
    run_metadata: dict[str, Any],
) -> BaseModel: ...
```

**`complete_structured` behavior (required):**

1. Before the API call: if `read_cumulative_cost_usd() >= SPEND_CAP_USD` (25.00), raise `SpendCapExceeded`.
2. Call `litellm.completion(model="openai/gpt-6-luna", messages=messages, response_format=..., reasoning_effort="none", ...)`.
3. Parse JSON into `response_model` (Pydantic validation).
4. Write `output_dir / f"{call_index:05d}_{make_run_timestamp()}.json"` with keys: `request` (messages), `response` (raw text + parsed dict), `usage` (`input_tokens`, `output_tokens`, `reasoning_tokens`, `cached_input_tokens` if present).
5. Append one line to `outputs/shared/cost_log.jsonl` per Section 6.10. Cost formula: input $0.10/1M, cached input $0.01/1M, output $0.50/1M (no reasoning token charge).
6. Update `output_dir / "metadata.json"` with `run_metadata` keys: `model`, `reasoning_effort`, `arm`, `batch_design`, `seed`, `stage`, `max_keep_features_per_batch`, `max_remove_features_per_batch`, `litellm_model`, `timestamp_format`.

**`generate_features.py` CLI flags**

| Flag | Required | Description |
|------|----------|-------------|
| `--arm` | yes | `original_only` \| `mirror_only` \| `paired` |
| `--batch-design` | yes | `mixed` \| `mixed_topup` \| `single_class` |
| `--seed` | no (default 42) | batch sampling RNG |
| `--smoke` | mutually exclusive with `--production` | Phase 0 probe + 1 mixed batch only |
| `--production` | mutually exclusive with `--smoke` | full run; requires approval file |

Production guard:

```python
APPROVAL_PATH = EXPERIMENT_ROOT / "outputs/shared/approval_step3_production.json"
# if --production and not APPROVAL_PATH.is_file(): raise SystemExit("missing approval_step3_production.json")
```

### Phase 4 - Test design (named tests and assertions)

**`test_batching.py`**

| Test | Given | When | Then |
|------|-------|------|------|
| `test_form_mixed_batches_counts` | fixture cohort with 30 keep, 30 remove | `form_mixed_batches(..., 10, 10)` | returns 3 batches; each has 10 keep + 10 remove; no duplicate `message_ids` across batches |
| `test_form_mixed_batches_zero_when_insufficient` | 5 keep, 20 remove | `form_mixed_batches` | raises `ValueError` |
| `test_form_single_class_batch_count` | cohort with 600 keep, 600 remove | `form_single_class_batches(..., keep_sample_size=500, remove_sample_size=500, posts_per_batch=10, seed=42)` | 50 keep batches + 50 remove batches; each batch has exactly 10 posts |
| `test_discovery_filter` | cohort with discovery + test rows | `load_discovery_cohort` | only `split == "discovery"` rows returned |

**`test_prompts.py`**

| Test | Given | When | Then |
|------|-------|------|------|
| `test_original_only_hides_mirror` | mixed batch, `arm=original_only` | `build_feature_generation_messages` | user JSON for each post contains `original_text` only; no `mirror_text` key |
| `test_mirror_only_hides_original` | mixed batch, `arm=mirror_only` | build messages | only `mirror_text` in payload |
| `test_paired_includes_both` | mixed batch, `arm=paired` | build messages | both `original_text` and `mirror_text` present |
| `test_prompt_mentions_max_eight_features` | any arm | system prompt string | contains `8` for keep and remove caps |

**`test_schemas.py`**

| Test | Given | When | Then |
|------|-------|------|------|
| `test_batch_feature_generation_rejects_ninth_keep` | 9 `ExtractedFeature` in `keep_features` | Pydantic validation | `ValidationError` |
| `test_single_class_max_eight` | 9 features | validation | `ValidationError` |
| `test_extracted_feature_requires_evidence_span` | missing `evidence_span` | validation | `ValidationError` |

**`test_llm_client.py`** (mock `litellm.completion`; no network)

| Test | Given | When | Then |
|------|-------|------|------|
| `test_complete_structured_writes_per_call_json` | mock returns valid JSON matching schema | `complete_structured(...)` | one `*.json` in `output_dir`; file has `request`, `response`, `usage` keys |
| `test_complete_structured_appends_cost_log` | mock usage 1000 input, 200 output, 0 reasoning | one call | `cost_log.jsonl` has one line; `cumulative_cost_usd` computed correctly |
| `test_spend_cap_blocks_call` | `cost_log.jsonl` cumulative at 25.00 | `complete_structured` | raises `SpendCapExceeded`; `litellm.completion` not called |
| `test_reasoning_effort_none_passed` | any call | `complete_structured` | mock called with `reasoning_effort="none"` and `model="openai/gpt-6-luna"` |
| `test_metadata_reasoning_tokens_zero` | mock usage `reasoning_tokens=0` | call + read metadata | `usage.reasoning_tokens == 0` |

**`test_generate_features.py`** (mock `llm_client.complete_structured`)

| Test | Given | When | Then |
|------|-------|------|------|
| `test_smoke_runs_one_batch` | `--smoke --arm original_only --batch-design mixed` | main | exactly 1 LLM call; output row has `batch_design=mixed` |
| `test_production_requires_approval` | no approval file | `--production` | exits non-zero with message containing `approval_step3_production.json` |
| `test_production_runs_when_approved` | approval file present | `--production --batch-design mixed` | batch count equals `len(form_mixed_batches(...))` |
| `test_writer_row_shape_mixed` | one batch result | writer | top-level keys: `batch_id`, `arm`, `batch_design`, `message_ids`, `keep_feature_count`, `remove_feature_count`, `result` |
| `test_writer_row_shape_single_class` | single_class batch | writer | keys include `label_class`, `feature_count`, `result` |

### Phase 5 - Implementation order

1. `schemas.py` (discovery, cluster label, and post label models).
2. `batching.py` (no LLM).
3. `prompts.py` (discovery arm branches, `build_cluster_label_messages`, post-labeling prompt builder with codebook prefix).
4. `llm_client.py` (LiteLLM + cost log).
5. `generate_features.py` (CLI + writers).
6. `smoke_tests/run_smoke_discovery.py`.
7. Green all tests.

## Pass / fail criteria

### Must pass

- Discovery-only: no `post_id` from `data/post_split/test_post_ids.csv` appears in any discovery output `message_ids`.
- Mixed production (existing): retain artifacts; metadata must note `label_drift_caveat` (about 12% of original discovery posts changed union modal label).
- Mixed top-up: about 28 batches per arm for `mixed_topup` (assert `20 <= n_batches <= 35`).
- Single-class ablation: exactly 100 batches per arm (50 keep + 50 remove).
- Finished discovery spend in `cost_log.jsonl`: about $0.83 total for smoke plus production mixed (all arms), zero reasoning tokens.
- Every LLM call uses `model="openai/gpt-6-luna"` and `reasoning_effort="none"`.
- Each run's `metadata.json` has `run_metadata.reasoning_effort == "none"`.
- Smoke Phase 0 (live network, manual): LiteLLM accepts `openai/gpt-6-luna` with `reasoning_effort="none"`, and usage shows `reasoning_tokens` is 0 or absent.
- Smoke Phase 1: 1 mixed batch per arm completes, with artifacts under `outputs/<arm>/discovery/outputs/<run_timestamp>/`.
- `outputs/shared/cost_log.jsonl` exists after the first LLM call with valid JSON lines per Section 6.10.
- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batching.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_prompts.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_schemas.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_llm_client.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_features.py -q` - exit 0.

### Must fail (until implemented)

- `test_spend_cap_blocks_call` before cap logic exists.
- `test_production_requires_approval` before approval guard exists.
- `test_original_only_hides_mirror` before arm-specific prompt branching exists.

## Commands (exact)

```bash
cd /workspace

# Dependency check
PYTHONPATH=. uv run python -c "import litellm; print('litellm_ok')"

# Unit tests (mocked LiteLLM; no network)
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batching.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_prompts.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_schemas.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_llm_client.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_generate_features.py -q

# Smoke Phase 0: LiteLLM probe (live; run once before batch smoke)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client \
  --probe

# Smoke Phase 1: one mixed batch per arm
for ARM in original_only mirror_only paired; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \
    --arm "$ARM" \
    --batch-design mixed \
    --smoke \
    --seed 42
done

# Packaged smoke script (runs Phase 0 + Phase 1)
PYTHONPATH=. uv run python experiments/llm_feature_generation_phase_2_part_3_2026_09_24/smoke_tests/run_smoke_discovery.py

# STOP - human gate. User creates approval file after reviewing smoke artifacts.

# Production mixed (primary) - all discovery posts
for ARM in original_only mirror_only paired; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \
    --arm "$ARM" \
    --batch-design mixed \
    --production \
    --seed 42
done

# Top-up mixed discovery on new Part-2-only discovery posts (~550)
for ARM in original_only mirror_only paired; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \
    --arm "$ARM" \
    --batch-design mixed_topup \
    --production \
    --seed 42
done

# Ablation: single_class per arm
for ARM in original_only mirror_only paired; do
  PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \
    --arm "$ARM" \
    --batch-design single_class \
    --production \
    --seed 42
done
```

Add `llm_client.py` CLI stub for `--probe` in Phase 5. The stub sends a minimal structured completion, prints `model`, `reasoning_effort`, and `reasoning_tokens`, and exits 0.

### Expected output (representative lines)

**`--probe`:**

```
model=openai/gpt-6-luna reasoning_effort=none reasoning_tokens=0
probe_ok
```

**`--smoke`:**

```
arm=original_only batch_design=mixed batches=1 model=gpt-6-luna reasoning_effort=none
Wrote outputs/original_only/discovery/outputs/2026-09-24T12-34-56/
metadata.run_metadata.reasoning_effort=none
```

**`--production` (mixed, one arm):**

```
arm=paired batch_design=mixed batches=287 model=gpt-6-luna reasoning_effort=none
Wrote outputs/paired/discovery/outputs/2026-09-24T14-00-01/
```

**pytest:**

```
.....................
21 passed in 0.45s
```

## Artifact contract (this step's outputs)

**Discovery row JSON** - path: `outputs/<arm>/discovery/outputs/<run_timestamp>/NNNNN_<call_timestamp>.json`

Per-call file (from `llm_client`):

| Field | Type |
|-------|------|
| `request` | object with `messages` list |
| `response` | object with `raw` str and `parsed` object |
| `usage` | object: `input_tokens`, `output_tokens`, `reasoning_tokens`, optional `cached_input_tokens` |

Discovery result row (from `generate_features` writer): the writer merges its fields into the per-call file under top-level key `discovery_row` (required):

| Field | Type |
|-------|------|
| `batch_id` | int |
| `arm` | str |
| `batch_design` | str |
| `message_ids` | list[str] |
| `keep_feature_count` | int (mixed only) |
| `remove_feature_count` | int (mixed only) |
| `feature_count` | int (single_class only) |
| `result` | object (`BatchFeatureGeneration` or `SingleClassBatchFeatureGeneration`) |

**`ExtractedFeature` in `result`:**

| Field | Type |
|-------|------|
| `message_id` | str |
| `feature_name` | str (snake_case) |
| `feature_value` | str |
| `category` | enum (7 values from reference `schemas.py`) |
| `is_open_ended` | bool |
| `evidence_span` | str |
| `rationale` | str |

**`metadata.json`** in run dir - `run_metadata` must include: `model`, `reasoning_effort`, `arm`, `batch_design`, `seed`, `stage`, `max_keep_features_per_batch`, `max_remove_features_per_batch`, `litellm_model` (`openai/gpt-6-luna`), `timestamp_format` (`%Y-%m-%dT%H-%M-%S`). For the retained main mixed run, include `label_drift_caveat: true` and a short note that about 12% of discovery posts changed union modal label since the run.

**`outputs/shared/cost_log.jsonl`** - one JSON object per line per Section 6.10.

## Human gates

### Gate A - after smoke, before production

1. Run smoke commands (Phase 0 probe + 1 mixed batch per arm).
2. Check smoke `metadata.json`. Confirm `model` is `gpt-6-luna` or `openai/gpt-6-luna`, `reasoning_effort` is `none`, and usage shows `reasoning_tokens` is 0.
3. The user approves in chat and writes (or commits):

   `outputs/shared/approval_step3_production.json`

   ```json
   { "approved": true, "approved_at": "<ISO8601>", "note": "smoke reviewed" }
   ```

4. `generate_features --production` must exit with an error if this file is missing.

## Commit message template

`step3: {short description}`

Examples: `step3: scaffold batching and schemas`, `step3: add LiteLLM client with spend cap`, `step3: wire generate_features smoke and production`.

## Handoff to Step 4

Step 3 stops at discovery JSON and the shared cost log. Step 4 should not start production embedding until mixed-design runs finish for all three arms.

**Deliverables:**

- Main mixed discovery outputs per arm (existing production run retained).
- Top-up mixed outputs per arm with `batch_design=mixed_topup` under `outputs/<arm>/discovery/outputs/<run_timestamp>/`.
- Optional ablation under the same tree with `batch_design=single_class` in metadata.
- `outputs/shared/cost_log.jsonl` with cumulative spend below $25.00 (discovery about $0.83 recorded).

**Step 4 reads:**

- The latest mixed-design discovery run per arm (main mixed), plus the latest `mixed_topup` run per arm.
- `metadata.json` from each run to confirm `batch_design` for the normalize path.

Steps 4 through 7 import `prompts.py` and `schemas.py` from Step 3. They must not edit those files.
