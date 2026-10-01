# Step 5: Analyze, write results, and verify

## Goal

Score the complete Jev run against the human labels on the all, unanimous, and split datasets. Write the analysis bundle to S3, generate `RESULTS.md` from it, write `README.md` and `SETUP.md`, and run the final checks for the branch.

All paths are relative to the repository root. Run every command from the repository root.

## Scope

- **Main caller:** `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py::main`
- **Main task:**
  1. Load the prepared input and the complete Jev run.
  2. Validate the join.
  3. Calculate label counts, split remove-vote counts, Jev metrics, and usage with issue 326's calculation functions.
  4. Render Markdown.
  5. Write the immutable analysis bundle.
  6. Publish `RESULTS.md`.
- **Out of scope:** changing calculations owned by issue 326, comparing Jev with the Bedrock models, and changing inference code or S3 run objects.

## Exact file tree

```text
experiments/zero_shot_jev_inference_2026_10_01/
  README.md
  SETUP.md
  RESULTS.md
  src/
    step3_analysis/
      __init__.py
      analyze.py
      render.py
```

## Files to inspect

- `docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step4.md` (pinned counts, CSV columns, metric rules)
- `docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/steps/step5.md` (documentation contracts)
- `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/constants.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/schemas.py`
- `experiments/zero_shot_jev_inference_2026_10_01/shared/storage.py`
- `shared/models/jev/constants.py`

## Files allowed to change

- `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/__init__.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/analyze.py`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step3_analysis/render.py`
- `experiments/zero_shot_jev_inference_2026_10_01/README.md`
- `experiments/zero_shot_jev_inference_2026_10_01/SETUP.md`
- `experiments/zero_shot_jev_inference_2026_10_01/RESULTS.md`

## Files forbidden to change

- `experiments/zero_shot_jev_inference_2026_10_01/shared/**`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step1_setup/**`
- `experiments/zero_shot_jev_inference_2026_10_01/src/step2_inference/**`
- `experiments/zero_shot_llm_inference_2026_09_30/**`
- `shared/**`
- `data_platform/**`
- `pyproject.toml`
- `uv.lock`

## Confirmed contracts

### Reuse

Import from `experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py` the public functions that implement issue 326 Step 4's Phase 4 units:

- unit 1, dataset selection
- unit 2, label counts
- unit 3, split remove-vote counts
- unit 4, one model and dataset's confusion counts and metrics

Do not copy them. If any of them is private or hardcodes the four Bedrock model folders, stop and return to plan review.

### Pinned counts

The counts come from issue 326 Step 4, and the analysis must reproduce them exactly:

| Dataset | Rows | Keep | Remove |
| --- | ---: | ---: | ---: |
| all | 13,992 | 11,024 | 2,968 |
| unanimous | 4,051 | 3,743 | 308 |
| split | 9,941 | 7,281 | 2,660 |

Split remove votes 1 through 4: 4,244, 3,037, 1,777, and 883.

### Outputs

Write under `s3://mirrorview-experimental-artifacts/experiments/zero_shot_jev_inference_2026_10_01/analysis/RUN_ID/` with `put_new`:

| File | Contents |
| --- | --- |
| `label_counts.csv` | Issue 326 Step 4 columns and row order |
| `split_remove_vote_counts.csv` | Issue 326 Step 4 columns and row order |
| `model_metrics.csv` | Issue 326 Step 4 columns. Three rows in order `all`, `unanimous`, `split`, each with `model=jev_1_13_0` |
| `usage.csv` | Columns `model`, `predictions`, `input_tokens`, `output_tokens`, `usd`. One row. `usd = input_tokens * JEV_USD_PER_MILLION_INPUT / 1e6 + output_tokens * JEV_USD_PER_MILLION_OUTPUT / 1e6` |
| `results_fragment.md` | Headings `## Human label distribution`, `## Split remove-vote distribution`, `## Model metrics`, `### All five-labeler posts`, `### Unanimous posts`, `### Split posts`, `## Jev usage`, in that order |
| `analysis_manifest.json` | Run ID, input SHA-256, final run manifest key, the SHA-256 of each other file, and row counts. No wall-clock timestamp |

Metrics use remove as the positive class and the stored Boolean label. Do not apply the threshold to `p_remove` again. Render proportions and metrics to six decimals, and render `usd` to four. A second run against unchanged inputs must find byte-identical existing objects and exit 0. Any mismatch exits nonzero and names the key.

The analysis rejects the run before writing when the latest `JevRunManifest` is not `complete`, when any prepared ID lacks exactly one valid prediction, or when any pinned count differs.

### Documentation

- `README.md`: one title line and one line linking [SETUP.md](SETUP.md) and [RESULTS.md](RESULTS.md).
- `SETUP.md`: data requirements only. Name issue 326's prepared input and its byte copy under this experiment's `inputs/study_2_five_labeler/`, the required complete run ID, the `jev_1_13_0` folder, the requirement for 13,992 unique valid predictions with no unresolved failures, and the analysis prefix. State that generated artifacts stay in S3. Do not include environment setup.
- `RESULTS.md`: `# Zero-shot Jev keep or remove inference for Study 2`, then `## Run record` with the run ID, the analysis S3 prefix, and the Step 4 smoke usage line, then `results_fragment.md` unchanged.

## Caller-first implementation phases

### Phase 1: Scaffold

Create the three Python files with stubs, then commit.

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze import main; from experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.render import render_results_fragment; print('step5-imports-ok')"
```

Expected output:

```text
step5-imports-ok
```

### Phase 2: Confirm contracts

Record the exact issue 326 function names being imported. Add typed signatures for loading, validation, the usage table, rendering, and writing. Commit. Stop for plan review before Phase 3 unless this step file was approved without revisions.

### Phase 3: Direct checks to satisfy

1. Given a hand-built input of 6 rows and predictions with known true and false positives and negatives, when metrics are calculated, then they match hand-calculated values.
2. Given predictions missing one prepared ID, duplicating one, or containing an unknown ID, when validation runs, then it raises before any write.
3. Given an `incomplete` latest manifest, when the run loads, then it raises before any write.
4. Given rows with 1,000 and 2,000 input tokens and 0 output tokens, when usage is calculated, then `input_tokens=3000` and `usd=0.000126`.
5. Given the same tables rendered twice, when the bytes are compared, then they are identical.

### Phase 4: Implement one unit at a time

Implement in this order, committing each unit separately: loading and validation, metric table, usage table, renderer, bundle writes, `main`.

### Phase 5: Run, publish, and verify

```bash
RUN_ID=study2-jev-zero-shot-2026-10-01
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --run-id "$RUN_ID"
PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step3_analysis.analyze --run-id "$RUN_ID"
```

Both commands should exit 0 and print the analysis prefix with `input_rows=13992 unanimous_rows=4051 split_rows=9941 models=1 metric_rows=3 artifacts=6`. The second command writes nothing new.

Download `results_fragment.md` from the analysis prefix and write `RESULTS.md` from it as the documentation contract describes. Then write `README.md` and `SETUP.md`.

```bash
git diff --name-only origin/main...HEAD | PYTHONPATH=. uv run python -c 'import sys; paths=[line.strip() for line in sys.stdin if line.strip()]; allowed=("shared/models/jev/", "experiments/zero_shot_jev_inference_2026_10_01/", "docs/plans/2026-10-01_study_2_zero_shot_jev_inference_41eb9f/"); bad=[p for p in paths if not (p in {"pyproject.toml", "uv.lock", "shared/models/__init__.py"} or (p.startswith(allowed) and p.endswith((".py", ".md"))))]; assert not bad, bad; print(f"verified {len(paths)} changed files")'
git diff --stat origin/main...HEAD -- experiments/study_2_llm_based_feature_extraction_2026_09_29 experiments/zero_shot_llm_inference_2026_09_30
```

The first command should print `verified N changed files`, and the second command should print nothing.

## Pass

- The analysis bundle holds exactly six files, and a rerun is byte-identical.
- The label and remove-vote counts match the pinned tables.
- `model_metrics.csv` has three rows, with metrics in [0, 1] and no `NaN`.
- `RESULTS.md` is generated from `results_fragment.md` with no edits by hand.
- The branch changes only the paths allowed by the final check, and the Study 2 and issue 326 experiments are unchanged.

## Fail

- Analysis runs on an incomplete run or applies the threshold to `p_remove` again.
- Any pinned count differs.
- `RESULTS.md` contains a value that is not in the analysis bundle or the Step 4 smoke usage line.
- Generated data is tracked in Git.
- Any forbidden file changes.
