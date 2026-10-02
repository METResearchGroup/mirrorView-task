# Step 4: Add and verify the few-shot analysis caller

## Proposal sections implemented

- Cross-cutting concerns: Prompt identity and demonstration overlap
- Cross-cutting concerns: Stored artifact identity
- Schema and key interfaces
- Step 5: Analyze and report the run

## Scope

- **Caller:** `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step3_analysis/main.py` `main`
- **Task:** Parameterize analysis by experiment, add metric-only demonstration exclusions and stored identity, and add the thin few-shot caller.
- **Out of scope:** The complete model run, final `RESULTS.md`, changes to rendering, and unit tests.

## Files to inspect

- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-10-01_study_2_few_shot_llm_inference_1e0d2d/proposal.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/schemas.py`, only to remove temporary variant defaults after all callers are explicit
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/shared/storage.py`, only to remove temporary variant defaults after all callers are explicit
- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/analyze.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step3_analysis/__init__.py` (new)
- `/Users/mark/src/work/mirrorview-wt/experiments/few_shot_llm_inference_2026_09_30/src/step3_analysis/main.py` (new)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/zero_shot_llm_inference_2026_09_30/src/step3_analysis/render.py`
- All experiment documentation in this step
- Every `tests/` directory and every new test file

## Analysis contract

Expose `run_analysis_cli(variant)`. Keep the zero-shot `main` as a wrapper around `ZERO_SHOT_VARIANT`. The few-shot `main` passes `FEW_SHOT_VARIANT` and contains no analysis logic.

Pass the active variant through prepared-input loading, model-folder loading, manifest selection and validation, analysis key construction, artifact writes, and analysis manifest construction. Extend `AnalysisManifest` with `experiment_name`, `prompt_name`, `prompt_sha256`, and `metric_exclusion_post_ids`. Older zero-shot analysis manifests load with zero-shot identity defaults. New manifests supply active values explicitly.

After the setup, inference, and analysis callers all pass an explicit variant, remove any temporary zero-shot default from root-dependent storage and validation functions. Keep compatibility aliases for imported zero-shot constants, but do not allow a shared path function to choose an experiment implicitly.

Validate that all five configured exclusion IDs are unique, present in the input, and unanimous. Remove them only from the rows sent to model-metric calculation. Human-label counts and split-vote counts continue to use all 13,992 rows. Keep the original partition checks at 13,992 all, 4,051 unanimous, and 9,941 split. Add metric partition checks at 13,987 all, 4,046 unanimous, and 9,941 split.

Add `build_metric_partitions(partitions, variant)` as the single exclusion boundary. It returns the same partition type used by the existing analysis functions. It validates the configured IDs before filtering, so callers cannot apply only part of the approved exclusion set.

The exclusions are exactly:

1. `bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7`
2. `bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c`
3. `bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48`
4. `bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b`
5. `bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206`

Continue to use the existing renderer unchanged. Analysis still writes exactly five artifacts.

## Smoke contract

Do not create a test file. Run this command against the verified copied input:

```bash
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${LAB_AWS_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${LAB_AWS_ACCESS_KEY_SECRET:-}}"
export AWS_DEFAULT_REGION=us-east-2
test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY"
PYTHONPATH=. uv run python - <<'PY'
from dataclasses import replace

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import load_verified_prepared_input
from experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze import (
    build_label_counts,
    build_metric_partitions,
    build_split_remove_vote_counts,
    partition_prepared_records,
)

store = CampaignObjectStore(FEW_SHOT_VARIANT.s3_bucket, region_name="us-east-2")
_, records = load_verified_prepared_input(store, FEW_SHOT_VARIANT)
full = partition_prepared_records(records)
labels_before = build_label_counts(full)
votes_before = build_split_remove_vote_counts(full.split_rows)
metric = build_metric_partitions(full, FEW_SHOT_VARIANT)
assert (len(metric.all_rows), len(metric.unanimous_rows), len(metric.split_rows)) == (13_987, 4_046, 9_941)
assert build_label_counts(full) == labels_before
assert build_split_remove_vote_counts(full.split_rows) == votes_before

configured = FEW_SHOT_VARIANT.metric_exclusion_post_ids
split_id = next(record.post_id for record in records if not record.is_unanimous)
invalid_sets = (
    configured[:-1],
    configured + (configured[0],),
    configured[:-1] + ("unknown-post-id",),
    configured[:-1] + (split_id,),
)
for invalid in invalid_sets:
    try:
        build_metric_partitions(full, replace(FEW_SHOT_VARIANT, metric_exclusion_post_ids=invalid))
    except ValueError:
        pass
    else:
        raise AssertionError(f"accepted invalid exclusions: {invalid}")
print("analysis-contract-ok all=13987 unanimous=4046 split=9941 exclusions=5")
PY
```

Expected stdout is exactly:

```text
analysis-contract-ok all=13987 unanimous=4046 split=9941 exclusions=5
```

Also run:

```bash
PYTHONPATH=. uv run python -m experiments.few_shot_llm_inference_2026_09_30.src.step3_analysis.main --help >/dev/null
PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step3_analysis.analyze --help >/dev/null
```

Both commands exit 0 without AWS access.

## Must pass

- Few-shot analysis reads only few-shot run folders and writes only below the few-shot analysis prefix.
- Descriptive tables use every input row, while model metrics use the three approved metric partition sizes.
- Analysis manifest identity and exclusions are complete and deterministic.
- Existing zero-shot analysis behavior remains compatible.

## Must fail

- An incomplete model folder, unresolved failure, duplicate or unknown prediction, wrong input digest, or identity mismatch.
- A missing, duplicate, unknown, or non-unanimous exclusion ID.
- Any attempt to write a sixth analysis artifact or change the existing renderer.

## Commit

Commit only the allowed files with a message such as `feat: add few-shot Study 2 analysis caller`.
