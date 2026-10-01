# Step 4: Calculate descriptive statistics and model metrics

## Scope

- **Main caller:** `experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze:main`
- **Task:** load one complete four-model run and its prepared input from S3, validate the join, calculate descriptive tables and classification metrics, render deterministic Markdown, and write the analysis bundle to S3.
- **Happy path:** load and validate inputs, join predictions by post ID, calculate fixed tables, render Markdown from those tables, then write one immutable bundle.
- **Out of scope:** invoking Bedrock, repairing inference, changing registered datasets, choosing alternate metrics, editing `RESULTS.md`, and interpreting findings.

## Proposed file tree

```text
/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/
  src/
    step3_analysis/
      __init__.py
      analyze.py
      render.py
```

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_zero_shot_llm_inference_3187fc/plan.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/constants.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/prepare.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/run.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/__init__.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/pyproject.toml`
- `/Users/mark/src/work/mirrorview-wt/uv.lock`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step1_setup/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step2_inference/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/RESULTS.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/REPORT.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/probe_bedrock_models.py`

## Fixed data contract

The prepared input contains one row per post with its ID, human remove label, keep and remove vote counts, labeler count, unanimity flag, and Step 1 input identity. Load that input and the four complete model folders from the same `RUN_ID`. Do not reload a newer registered dataset in place of the input used for inference.

Treat remove as positive. Calculate metrics from the Boolean model label. Do not threshold the stored probability again. The inference schema already requires the Boolean label to agree with the probability at `0.5`.

The current registered five-labeler data pins these invariants:

| Dataset | Rows | Keep | Remove | Keep proportion | Remove proportion |
|---|---:|---:|---:|---:|---:|
| All five-labeler posts | 13,992 | 11,024 | 2,968 | 0.787879 | 0.212121 |
| Unanimous posts | 4,051 | 3,743 | 308 | 0.923969 | 0.076031 |
| Split posts | 9,941 | 7,281 | 2,660 | 0.732421 | 0.267579 |

The split subset has this remove-vote distribution:

| Remove votes | Count | Proportion |
|---:|---:|---:|
| 1 | 4,244 | 0.426919 |
| 2 | 3,037 | 0.305502 |
| 3 | 1,777 | 0.178755 |
| 4 | 883 | 0.088824 |

Counts are exact. Render proportions and metrics to six decimal places. Machine-readable files retain unrounded numeric values.

## Fixed output contract

Write under `s3://mirrorview-experimental-artifacts/experiments/zero_shot_llm_inference_2026_09_30/analysis/RUN_ID/`:

```text
analysis_manifest.json
label_counts.csv
split_remove_vote_counts.csv
model_metrics.csv
results_fragment.md
```

`label_counts.csv` has one row per dataset and human label. Dataset order is `all`, `unanimous`, `split`. Label order is `keep`, `remove`. Columns are `dataset`, `label`, `count`, `dataset_total`, and `proportion`.

`split_remove_vote_counts.csv` has one row for each remove-vote count in order 1, 2, 3, 4. Columns are `remove_votes`, `count`, `split_total`, and `proportion`.

`model_metrics.csv` has 12 rows. Dataset order is `all`, `unanimous`, `split`. Model order is `amazon_nova_micro`, `qwen3_32b`, `openai_gpt_5_6_terra`, `claude_sonnet_5_5`. Columns are `dataset`, `model`, `sample_count`, `true_positive`, `false_positive`, `true_negative`, `false_negative`, `f1`, `accuracy`, `recall`, and `precision`. Use zero for precision, recall, or F1 when its denominator is zero. Never emit `NaN`.

`results_fragment.md` is derived only from the three CSV tables and fixed display names. It uses these headings:

```text
## Human label distribution
## Split remove-vote distribution
## Model metrics
### All five-labeler posts
### Unanimous posts
### Split posts
```

Each model table has `Model`, `N`, `F1`, `Accuracy`, `Recall`, and `Precision` columns. Step 5 copies or embeds this fragment into `RESULTS.md`. Step 4 does not edit repository documentation.

`analysis_manifest.json` records the run ID, prepared-input identity, four model IDs and manifest identities, exact input and output S3 keys, row counts, and analysis schema version. It records the SHA-256 values of the three CSV files and `results_fragment.md`. It lists its own key without trying to record a hash of its own bytes. Do not put a wall-clock timestamp in table data or Markdown because it prevents byte-for-byte reproduction.

## Caller-first implementation phases

### Phase 0: Confirm the task

Name `analyze:main` as the only entry point. Its path is apply the Step 1 credential adapter, load, validate, calculate, render, and write. S3 reads use the existing experiment storage boundary. `render.py` receives completed tables and has no S3 access.

**Pass:** the file tree, one caller, fixed inputs, fixed outputs, and excluded work are explicit.

**Fail:** analysis has multiple CLI entry points, reads data that may differ from the inference input, or requires Step 5 to calculate a table.

### Phase 1: Scaffold caller-first

Create the three allowed files. Add imports and typed stubs only. Make `main` show the full path through the stubs without implementing calculations, rendering, S3 reads, or writes.

```bash
PYTHONPATH=. uv run python -c "from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import main; from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.render import render_results_fragment"
```

**Expected output:** no output and exit zero.

**Pass:** all files exist, imports resolve, and the caller exposes load, validate, calculate, render, and write in order with stub bodies.

**Fail:** an import fails, a planned file is orphaned, or scaffold code calculates a real value.

```bash
git add experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/__init__.py experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py
git commit -m "Scaffold zero-shot analysis"
```

**Expected output:** one commit containing only the three allowed files.

### Phase 2: Confirm contracts

Define typed, behavior-free contracts for:

- loading the prepared input, four completed model manifests, and prediction rows for one run ID;
- rejecting incomplete, duplicate, extra, or missing post IDs before calculation;
- building label counts, split remove-vote counts, confusion counts, and metrics;
- rendering Markdown from completed tables;
- serializing the fixed analysis bundle and manifest through the existing experiment storage layer.

Reuse Step 1 and Step 2 schema types where they express these records. Add analysis-only immutable record types in `analyze.py` only when a table needs a type that does not exist. Do not introduce a generic framework or edit shared schemas.

`render_results_fragment` accepts completed tables and returns one string. It does not load data, recalculate statistics, read environment variables, or write files.

**Pass:** signatures cover every fixed input and output, `main` wires them in dependency order, and bodies remain stubs.

**Fail:** behavior is implemented during contract work, a shared contract changes, or the renderer owns calculations.

The approved parent plan authorizes implementation through Phase 5. If an implementation detail conflicts with a fixed Step 1 or Step 2 contract, stop and revise this plan before implementing behavior.

### Phase 3: Implement calculations and validation

Implement behavior that satisfies these scenarios:

1. Given the prepared input, when label counts are calculated, then all, unanimous, and split equal the pinned counts and each dataset's counts and proportions sum to its total and one.
2. Given the 9,941 split rows, when remove-vote counts are calculated, then votes 1 through 4 have counts 4,244, 3,037, 1,777, and 883, with no vote 0 or 5 row.
3. Given a hand-calculated fixture, when metrics are calculated, then remove is positive and F1, accuracy, recall, and precision match the fixture.
4. Given no predicted positives or no actual positives, when metrics are calculated, then undefined precision, recall, and F1 values are zero.
5. Given full predictions, when datasets are evaluated, then all uses every row, unanimous uses only 0 or 5 remove votes, and split uses only 1 through 4.
6. Given four complete model outputs, when the run is validated, then each model joins to exactly 13,992 rows without changing prepared-input order.
7. Given a duplicate, missing, or unknown prediction ID, when validation runs, then it raises before calculating or writing.
8. Given fewer than four complete manifests or an unresolved failure, when the run loads, then it raises before calculating or writing.
9. Given completed tables outside the standardized order, when Markdown is rendered twice, then both byte strings match and use the fixed order.
10. Given a valid in-memory run and fake store, when the caller completes, then it writes exactly five fixed keys with matching identities and hashes.

### Phase 4: Implement one unit at a time

Implement in dependency order:

1. Validate and select all, unanimous, and split prepared-input rows.
2. Build human label counts and proportions.
3. Build split remove-vote counts and proportions.
4. Build one model and dataset's confusion counts and metrics with remove positive.
5. Build the standardized 12-row metric table.
6. Load and validate all four completed S3 model outputs against the prepared-input identity and post IDs.
7. Render deterministic Markdown from completed tables.
8. Serialize tables and manifest, write five immutable S3 objects, and close `main`.

After each unit, run a focused read-only Python command against the completed public function. Use small in-memory inputs for calculations and rendering. Do not access live S3 until the complete caller is ready for Phase 5.

After each unit, make a focused commit:

```bash
git add experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis
git commit -m "Implement ANALYSIS_UNIT"
```

Replace the placeholder with the completed unit.

**Pass per unit:** one path segment advances, its focused check passes, and no forbidden file changes.

**Fail per unit:** an edit implements unrelated units, changes a confirmed contract, adds a dependency, reaches into private state when a public fake is available, or changes a forbidden file.

### Phase 5: Verify the caller and reproduce from S3

After Step 3 verifies all four models, run:

```bash
RUN_ID=study2-zero-shot-2026-10-01
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --run-id "$RUN_ID"
```

**Expected output:** exit zero and print the analysis prefix plus `input_rows=13992`, `unanimous_rows=4051`, `split_rows=9941`, `models=4`, `metric_rows=12`, and `artifacts=5`.

Run the same command again.

**Expected output:** exit zero after verifying that existing artifacts have the expected hashes. It must not replace an object with different bytes. A mismatch exits nonzero and names the conflicting key.

**Pass:** S3 contains exactly five fixed artifacts; descriptive counts match the pinned tables; each model has three metric rows with the correct sample count; rendering is byte deterministic; and the second run verifies the existing bytes without changing them.

**Fail:** analysis starts for an incomplete model, any join loses or duplicates a post, a count differs, a metric uses keep as positive, output contains `NaN`, Markdown order changes, a rerun overwrites different bytes, or a generated artifact appears in the repository.

## What done looks like

1. The caller rejects incomplete or mismatched inference before writing.
2. Machine-readable artifacts report exact label counts and proportions for 13,992 all, 4,051 unanimous, and 9,941 split posts.
3. Split remove-vote counts are 4,244, 3,037, 1,777, and 883 for one through four votes.
4. The metric table has 12 rows in the standardized order and calculates F1, accuracy, recall, and precision with remove positive.
5. `results_fragment.md` is deterministic and contains every table Step 5 needs without editing `RESULTS.md`.
6. The immutable analysis bundle is reproducible from the stored run and written only to S3.
7. Only the three allowed repository files change.
