# Step 6: Label all posts and run self-consistency check

Step 6 labels all 20,000 posts with the approved shared codebook. Each post gets two labels, one for original text and one for mirrored text, so production labeling submits 40,000 OpenAI Batch requests (20,000 posts times 2 text surfaces). Production labeling uses the OpenAI Batch API (`v1/batch`), not one-at-a-time chat calls. Each request marks every codebook feature present or absent. Step 3 `prompts.py` turns the codebook into a fixed, cacheable prompt prefix. Batch code lives in `src/batch_client.py` (Step 6 owner). `llm_client.py` stays unchanged and is used only for the 20-text smoke. Because labeling is resumable, the runner skips `post_id` + `text_surface` pairs already written. The step writes label shards to `outputs/shared/label/<run_timestamp>/labels.jsonl` (keyed by `post_id` and `text_surface`) and assembles `outputs/shared/label_matrix.parquet` (one row per `post_id` x `text_surface`; one column per codebook `feature_id`, e.g. `cb_001`, not `cb_cb_001`). Before Batch submission, estimate cost from the JSONL token count and refuse to submit if the projection exceeds the remaining budget under the $25 cap. After completion, write actual usage into `outputs/shared/cost_log.jsonl` at Batch prices (50% of standard). The 200-text self-consistency re-label also goes through Batch. After labeling, report per-feature agreement and flag features below 90% in `outputs/shared/self_consistency/` without removing them from the codebook.

## Scope

- **Caller / entrypoint:** `label_posts` CLI, `self_consistency` CLI, and `batch_client` helpers (`if __name__ == "__main__"` where applicable).
- **In scope:** Check the approval gate. Run 20-text smoke via `llm_client`. Build Batch JSONL, upload, create batch (24h completion window), poll, download output and error files, parse into label shards, resubmit failed or missing `custom_id` values only. Split into multiple batch input files if needed to stay under OpenAI per-batch request and file size limits (confirm current limits in OpenAI docs before submit; do not hard-code undocumented caps). Full labeling with resume. Self-consistency via Batch. Enforce spend cap. Write tests with mocked Batch API and mocked smoke LLM.
- **Out of scope:** Human validation or kappa (deferred), held-out analysis (Step 7), codebook edits after approval, and Part 2 theme mapping (Step 7).

## Files to inspect (read-only)

- `docs/plans/2026-09-24_llm_feature_generation_phase_2_part_3_2f71ad/plan.md`: Step 6, cost estimate, provisional-label caveat.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/llm_client.py`: `complete_structured`, cost log, `SpendCapExceeded` (Step 3 owner; smoke only).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/schemas.py`: `PostLabelResult` and per-text present/absent schema (Step 3 owner; import only).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/prompts.py`: `build_labeling_prompt(codebook, text, text_surface)` (Step 3 owner; import only).
- OpenAI Batch API docs: `v1/batch`, JSONL request format, completion window, output and error file layout, Batch pricing (50% of standard).
- `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`: input codebook (Step 5).
- `outputs/shared/codebook/approved_<run_timestamp>/approval.json`: required gate file.
- `outputs/<arm>/cohort/<run_timestamp>/cohort.parquet`: post texts, `split`, `modal_decision`.
- `data/post_split/discovery_post_ids.csv`, `data/post_split/test_post_ids.csv`: split membership.

## Files allowed to change

- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/batch_client.py`: create (Batch JSONL builder, upload, create batch, poll, download, parse, resubmit failures).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/label_posts.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/src/self_consistency.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batch_client.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py`: create.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/label/<run_timestamp>/`: label shards (`labels.jsonl`, batch job metadata, resume index).
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/label_matrix.parquet`: assembled matrix.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/self_consistency/`: relabel run and scores.
- `experiments/llm_feature_generation_phase_2_part_3_2026_09_24/outputs/shared/cost_log.jsonl`: append lines at Batch prices after Batch jobs complete (smoke lines use standard prices from `llm_client`).

## Files forbidden to change

- `shared/`, other `experiments/*`.
- `docs/plans/.../plan.md`, sibling step files.
- `src/build_codebook.py`, `prompts.py`, `schemas.py`, `map_part2_themes.py`, `analyze.py`, `write_results.py`.
- `data/post_split/*`, `data/feature_synonyms.csv`.
- `src/llm_client.py` (Step 3 owner; call for smoke only, do not edit).

## Batch request contract

Each JSONL line is one Batch request:

| Field | Value |
|-------|--------|
| `custom_id` | `{post_id}__{text_surface}` (stable for resume and resubmit) |
| `method` | `POST` |
| `url` | `/v1/chat/completions` (or current OpenAI Batch doc path) |
| `body.model` | `gpt-6-luna` |
| `body.reasoning_effort` | `none` |
| `body.messages` | Fixed codebook prefix from `build_labeling_prompt` plus user post text |
| `body.response_format` | Structured JSON schema matching `PostLabelResult` |

Workflow:

1. Write JSONL locally under `outputs/shared/label/<run_timestamp>/batch_inputs/`.
2. Estimate tokens from JSONL; compute projected Batch cost (50% of standard input/output rates from constants). If `cumulative_cost + projected > SPEND_CAP_USD`, exit before upload.
3. Upload file(s), create batch with 24h completion window, store `batch_id` in metadata.
4. Poll until terminal status; download output and error files.
5. Parse successful lines into `labels.jsonl`; collect failed or missing `custom_id` values and resubmit in a new batch file.
6. After all batches complete, append actual usage to `cost_log.jsonl` using Batch pricing.

## Implementation phases (TDD: mandatory order)

| Phase | Goal | Gate |
|-------|------|------|
| 1: Scope | Name callers, file tree, out-of-scope | Callers + tree listed |
| 2: Scaffold | Create modules; stubs only | Imports resolve |
| 3: Contracts | Label schemas, CLI flags, Batch JSONL | Stubs only |
| 4: Test design | Failing tests below | Fail for right reason |
| 5: Implement | One unit per commit | Targeted tests green |
| 6: Done | Step pytest + smoke CLI on fixtures | Pass/fail criteria met |

### Phase 4: Named tests and assertions

| Test name | Given | When | Assert |
|-----------|-------|------|--------|
| `test_label_posts_requires_approval_marker` | Codebook path without `approved_*/approval.json` | `label_posts.main(...)` | Raises `ApprovalRequiredError` |
| `test_build_prompt_prefix_stable_across_calls` | Fixed codebook JSON | Two calls to `build_labeling_prompt` | Codebook block byte-identical; only post text differs |
| `test_batch_jsonl_custom_id_format` | Two posts, two surfaces | `build_batch_jsonl` | 4 lines; `custom_id` matches `post_id__surface` |
| `test_batch_jsonl_body_has_model_and_schema` | One request line | parse JSONL | `body.model==gpt-6-luna`, `reasoning_effort==none`, response schema present |
| `test_smoke_labels_twenty_posts_via_llm_client` | Cohort fixture with 25 posts | `label_posts --smoke --limit 20` | Exactly 40 direct `llm_client` calls (not Batch); catches prompt bugs |
| `test_projected_batch_cost_under_cap_before_submit` | JSONL fixture + mock cost log | `estimate_batch_cost` | If projected total `>= 25.00`, CLI exits non-zero before Batch create |
| `test_batch_client_parses_output_to_labels` | Mock output JSONL | `parse_batch_output` | Writes shard rows with `post_id`, `text_surface`, `labels` |
| `test_batch_resubmit_only_failed_custom_ids` | Output missing one `custom_id` | `resubmit_missing` | Second batch JSONL contains only missing ids |
| `test_resume_skips_labeled_post_ids` | Existing shard with `post_id` A labeled | `label_posts` rerun | No second request for post A |
| `test_assemble_label_matrix_wide_format` | Shards for original + mirror | `assemble_label_matrix(...)` | Parquet has columns `post_id`, `text_surface`, `split`, `modal_decision`, and one column per `feature_id`; 20,000 x 2 rows |
| `test_self_consistency_uses_batch_api` | Labeled matrix fixture | `self_consistency --seed 42` | Batch client called for 200 pairs (not 200 direct LLM calls) |
| `test_self_consistency_sample_size_200_seed_42` | Labeled matrix fixture | `self_consistency --seed 42` | Sample size 200; reproducible post ids |
| `test_cost_log_uses_batch_prices_after_batch` | Mock batch usage | append helper | `cost_usd` uses 50% of standard rates |

### Phase 5: Implementation units (dependency order)

1. `require_approved_codebook(codebook_path)`: glob `outputs/shared/codebook/approved_*/approval.json`.
2. `batch_client.build_batch_jsonl`, `estimate_batch_cost`, `submit_batch`, `poll_batch`, `download_results`, `parse_batch_output`, `resubmit_missing`.
3. Import `build_labeling_prompt` from Step 3 `prompts.py`.
4. `label_posts --smoke`: 20 posts x 2 surfaces via `llm_client.complete_structured` only.
5. `label_posts --production`: 40,000 Batch requests with resume and spend gate.
6. `assemble_label_matrix` to `outputs/shared/label_matrix.parquet`.
7. `self_consistency`: sample 200 pairs at seed 42; relabel via Batch; write `scores.json`.

## Pass / fail criteria

### Must pass

- `PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batch_client.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py -q` exits 0.
- Smoke: 20 posts x 2 surfaces = 40 direct `llm_client` calls; cost projection printed; Batch production blocked if projected total `>= $25.00`.
- Full run: 40,000 Batch requests (or fewer on resume after partial run).
- `outputs/shared/label_matrix.parquet` has 40,000 rows and one column per codebook `feature_id`.
- `outputs/shared/self_consistency/<run_timestamp>/scores.json` exists with `sample_size=200`.
- Features with agreement `< 0.90` listed in `features_below_threshold`; none removed from codebook.
- Batch completion appends cost lines at Batch prices to `outputs/shared/cost_log.jsonl`.
- Resume: re-running production does not relabel existing `post_id` + `text_surface` pairs.

### Must fail (until implemented)

- `label_posts` without approval marker.
- Batch submission when projected cost exceeds remaining budget.
- `llm_client` production labeling path for full corpus (production must use Batch).

## Commands (exact)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

CODEBOOK=outputs/shared/codebook/approved_<run_timestamp>/codebook.json

# Smoke: 20 posts via llm_client (direct), cost projection for Batch full run
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --text-surfaces original mirror \
  --smoke \
  --limit 20 \
  --seed 42

# Review stdout: projected_batch_total_usd=... (expect about $5 to $6 at Batch prices; must stay under $25 cap)
# Review outputs/shared/cost_log.jsonl cumulative line

# Production labeling via OpenAI Batch API (resumable)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --text-surfaces original mirror \
  --production

# Assemble shared matrix (idempotent)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \
  --codebook "$CODEBOOK" \
  --assemble-matrix

# Self-consistency on 200 texts via Batch (seed 42)
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency \
  --codebook "$CODEBOOK" \
  --label-matrix outputs/shared/label_matrix.parquet \
  --sample-size 200 \
  --seed 42

# Upload labeling artifacts
PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \
  --paths outputs/shared/label outputs/shared/label_matrix.parquet outputs/shared/self_consistency outputs/shared/cost_log.jsonl

# Tests
PYTHONPATH=. uv run pytest experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_batch_client.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_label_posts.py \
  experiments/llm_feature_generation_phase_2_part_3_2026_09_24/tests/test_self_consistency.py -q
```

### Expected output (representative lines)

```
approval=outputs/shared/codebook/approved_2026-09-24T12-40-00/approval.json
smoke_posts=20 surfaces=original,mirror direct_llm_calls=40
projected_batch_total_usd=5.80 cap_usd=25.00
# production:
batch_requests=40000 batch_jobs=2
resumed_skipped=0
Wrote outputs/shared/label_matrix.parquet rows=40000 features=...
Wrote outputs/shared/label/2026-09-24T14-00-00/labels.jsonl
self_consistency sample_size=200 seed=42 batch_requests=200 mean_agreement=0.94
features_below_90pct=['cb_042', 'cb_107']
Wrote outputs/shared/self_consistency/2026-09-24T15-00-00/scores.json
```

## Artifact contract (this step's outputs)

### Label shards (`outputs/shared/label/<run_timestamp>/`)

| File | Schema |
|------|--------|
| `labels.jsonl` | One JSON per line: `post_id`, `text_surface` (`original` \| `mirror`), `labels` map `{ "cb_001": true, ... }`, `labeled_at` |
| `labeled_ids.json` | `{ "labeled": [{"post_id": "...", "text_surface": "original"}, ...] }` for resume |
| `batch_inputs/*.jsonl` | OpenAI Batch request files |
| `batch_jobs.json` | `batch_id`, status, input file ids, output file ids |
| `metadata.json` | `model`, `reasoning_effort`, `codebook_version`, `n_requests`, `stage`, `pricing_mode` (`batch`), `built_at` |

### Shared label matrix (`outputs/shared/label_matrix.parquet`)

| Column | Type |
|--------|------|
| `post_id` | str |
| `text_surface` | str (`original` \| `mirror`) |
| `split` | str (`discovery` \| `test`) |
| `modal_decision` | str |
| `<feature_id>` | int 0/1 (one column per codebook feature; column name equals `feature_id`, e.g. `cb_001`, not `cb_cb_001`) |

### Self-consistency (`outputs/shared/self_consistency/<run_timestamp>/scores.json`)

```json
{
  "sample_size": 200,
  "seed": 42,
  "per_feature": {
    "cb_001": {"agreement_rate": 0.95, "n_pairs": 200}
  },
  "features_below_threshold": ["cb_042"]
}
```

Also write `relabeled.jsonl` with both labeling passes for audit.

### Cost log (`outputs/shared/cost_log.jsonl`)

Each line: `timestamp`, `stage` (`label`, `label_batch`, or `self_consistency_batch`), `arm`, `model`, `input_tokens`, `output_tokens`, `reasoning_tokens`, `cost_usd` (Batch jobs at 50% of standard rates), `cumulative_cost_usd`.

## Human gates (if any)

This step has no human gates, but Step 5 Gate B must be satisfied before `label_posts` runs.

**Spend gate (automated):** Estimate Batch cost from JSONL before submit; refuse submit if projection exceeds remaining budget. After jobs finish, record actual Batch usage in `cost_log.jsonl`.

## Commit message template

`step6: batch label all posts with smoke cost check and self-consistency`

## Handoff to Step 7

- `outputs/shared/label_matrix.parquet` (40,000 rows; Step 7 reads this file only, not shard JSONL)
- `outputs/shared/codebook/approved_<run_timestamp>/codebook.json`
- `outputs/shared/self_consistency/<run_timestamp>/scores.json`
- Discovery-half matrix rows: descriptive tables for feature description and Part 2 catalog overlap only
- Test-half matrix rows (`split == test`): sole input for Q1 to Q7 hypothesis tests in Step 7
