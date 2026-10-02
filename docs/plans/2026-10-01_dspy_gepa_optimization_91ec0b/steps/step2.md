# Step 2: Build and verify the experiment dataset

## Outcome

This step creates the experiment documentation, resolves the 10 prompt examples to post IDs once, and writes four deterministic splits to S3. The final source contains an `EXCLUDELIST_POST_IDS` constant. The temporary matching script must be deleted before the step passes.

## Caller and happy path

The caller is `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py` without `--contract-only`.

The command validates the registered dataset and removes the prompt examples before it selects the 405-row pilot cohort. It writes the split artifacts and manifest, then downloads the manifest for a read-after-write check. The final output contains the S3 URI and hashes.

## Files

### Inspect

- `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/registry.py`
- `/Users/mark/src/work/mirrorview-wt/lib/aws/s3.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`

### Allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/SETUP.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/RESULTS.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/config.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/data.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/shared/artifacts.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py`
- One temporary script under the experiment directory, only while resolving the prompt example IDs

### Forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/shared/prompts.py`
- Dataset registry entries and source datasets
- Step 1's confirmed model and telemetry contracts
- Any test file or test directory
- Optimization, selection, development, or test results

## Data contracts

1. Load `STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS` through `shared.data.dataloader.load_dataset` with `low_memory=False`.
2. Require 4,051 unique source rows, with 3,743 keep labels and 308 remove labels. Require five agreeing raters per row.
3. Resolve each of the 10 prompt examples by normalized `original_text` and `mirror_text`. Require exactly one dataset match per example and 10 distinct post IDs.
4. Copy the resolved IDs into `EXCLUDELIST_POST_IDS`, delete the temporary script, and exclude the constant before any experiment sampling.
5. Require 4,041 eligible rows after exclusion, with 3,738 keep labels and 303 remove labels.
6. Use seed `20261001` and stable post ID ordering for every tie. Stratify the 405-row cohort and each split by `keep_remove_label` and `sampled_stance`.
7. Produce 222 optimization rows, 61 GEPA validation rows, 61 development rows, and 61 test rows. Require remove counts of 17, 5, 5, and 5.
8. No post ID may occur in two splits. No excluded post ID may occur in the cohort or a split.
9. The manifest must contain the dataset registry name and resolved source path, source and eligible counts, exclusion IDs, seed, sampling method, ordered post IDs, per-split label and stance counts, and SHA-256 hashes.
10. Upload generated data only under `s3://mirrorview-experimental-artifacts/experiments/dspy_gepa_optimization_2026_09_30/inputs/`.

## Implementation sequence

1. Create `README.md` with the experiment title and links to `SETUP.md` and `RESULTS.md`.
2. Describe required data, credentials, allowed trace contents, and commands in `SETUP.md`. Initialize `RESULTS.md` with empty, clearly labeled sections for the split audit and later results.
3. Write the temporary matcher and run it once against the registered dataset. Inspect its 10 distinct post IDs, then copy them into `EXCLUDELIST_POST_IDS`.
4. Delete the matcher before continuing. Do not retain fuzzy matching or a recurring leakage check in production code.
5. Add dataset schema checks before filtering. Fail with the observed and expected counts when a check differs.
6. Select the deterministic cohort and splits. Use explicit quotas so the four split sizes and remove counts do not depend on library rounding.
7. Serialize each split as Parquet in its stable row order. Compute each hash from the exact uploaded bytes.
8. Upload the four Parquet objects and `split_manifest.json` through `lib.aws.s3.S3`.
9. Download the manifest and each object header. Recompute the manifest hash, confirm object sizes, and confirm that a second setup run produces the same IDs and hashes.

## Smoke verification

```bash
PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py
```

Expected output. The command reports 4,051 source rows, 10 exclusions, 4,041 eligible rows, and 405 cohort rows. It reports split sizes of 222, 61, 61, and 61, with remove counts of 17, 5, 5, and 5. The final lines contain the manifest URI and hashes.

```bash
find experiments/dspy_gepa_optimization_2026_09_30 -type f \( -iname '*exclude*' -o -iname '*match*prompt*' \)
```

Expected output. The command prints nothing because the one-off matcher has been deleted.

Run the setup command a second time.

Expected output. Every ordered post ID and SHA-256 hash matches the first run. The command reports that the existing S3 objects have the expected contents.

## Pass and stop conditions

Pass only when the exact source and eligible counts match, all 10 prompt examples have unique IDs in the constant, all split quotas match, every disjointness check passes, all hashes survive an S3 read-after-write check, and the temporary script is absent.

Stop if a prompt example has zero or multiple matches, a source count changes, a schema check fails, a quota cannot be met, an excluded ID remains, two splits overlap, a repeated run changes a hash, or an S3 check fails. Do not adjust expected counts silently.

## Commit

Suggested commit message. `experiment: add deterministic DSPy pilot splits`
