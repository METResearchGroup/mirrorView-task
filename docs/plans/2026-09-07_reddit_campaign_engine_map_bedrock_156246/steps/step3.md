# Step 3: Run offline smoke and confirm unused production prefixes

## Scope

- **Caller:** the offline commands below, run from `/workspace` after Steps 1 and 2.
- **Task:** Prove the engine map, Reddit feature paths, Reddit campaign CLI flags, unchanged registry engines, and six parquet metadata columns. Print a disposable prefix helper. Confirm the pinned campaign batches prefix is empty. Optional tiny live Bedrock proof uses only the disposable smoke prefix and must be deleted before merge.
- **Out of scope:** Full 400,000 row labeling, pytest, new smoke modules, GitHub posting, changelog (after the pull request).

Do not add files under `tests/`. Do not write production `batches/` under the pinned campaign prefix.

## Files to inspect

Read only. No product edits unless a prior step failed and the fix stays in the allowed set from Steps 1 and 2.

## Files allowed to change

None, unless a correctness bug found by these commands requires a fix in the allowed product files from Steps 1 and 2.

## Files forbidden to change

- Any file under `tests/`
- `data_platform/generate_features/registry.py`
- `data_platform/utils/storage.py`
- Pinned campaign objects under `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/`

## Commands

Export lab AWS keys as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` before any `aws` command. Never print secrets.

### Engine map

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.campaign_engine_map import campaign_engine_type
assert campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', 'is_news_or_opinion') == 'openai'
assert campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', 'is_political') == 'openai'
assert campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', 'is_likely_spam') == 'bedrock'
assert campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', 'political_stance') == 'openai'
assert campaign_engine_type('bluesky_2026_09_03_235130_llm_features_v1', 'is_political') == 'openai'
print('campaign_engine_map OK')
"
```

Expected: `campaign_engine_map OK`

### Reddit FeaturePaths

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.s3_feature_campaign import FeaturePaths
p = FeaturePaths.for_campaign(
    'reddit_2026_09_03_233928_llm_features_v1',
    'is_political',
    platform='reddit',
    dataset_id='reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079',
)
assert '/reddit/reddit_3d8a2c41' in p.prefix
assert p.prefix.endswith('features/reddit_2026_09_03_233928_llm_features_v1/is_political/')
print('reddit FeaturePaths OK')
"
```

Expected: `reddit FeaturePaths OK`

### Disposable prefix helper print

Do not write pinned campaign batches.

```bash
DISPOSABLE_PREFIX=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/

PYTHONPATH=. uv run python -c "
from data_platform.generate_features.s3_feature_campaign import FeaturePaths
from data_platform.generate_features.campaign_engine_map import campaign_engine_type
feature = 'is_likely_spam'
assert campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', feature) == 'bedrock'
paths = FeaturePaths.from_root_uri('s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/', feature)
print('disposable_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/')
print('bedrock_feature=' + feature)
print('active_bedrock_job_key=' + paths.prefix + 'active_bedrock_job.json')
"
```

Expected stdout includes `disposable_prefix=`, `bedrock_feature=is_likely_spam`, and `active_bedrock_job_key=` ending in `active_bedrock_job.json`.

Optional tiny live proof: at most ten rows, `max_concurrency=8`, one part, only under that disposable prefix. Then delete it.

### Pinned campaign batches untouched

```bash
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_political/batches/ 2>&1 || true
```

Expected: `NoSuchKey` or empty listing. No `part-*.parquet` from this pull request.

### Reddit campaign CLI

```bash
PYTHONPATH=. uv run python data_platform/generate_features/generate_reddit_features.py --help
```

Expected: help text includes `--campaign-id` and `--preprocessed-run`.

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.generate_reddit_features import generate_reddit_features
import inspect
assert 'campaign_id' in inspect.signature(generate_reddit_features).parameters
assert 'preprocessed_run' in inspect.signature(generate_reddit_features).parameters
print('generate_reddit_features campaign API OK')
"
```

Expected: `generate_reddit_features campaign API OK`

### Registry engine values unchanged

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.registry import FEATURE_REGISTRY
expected = {
    'is_news_or_opinion': 'openai',
    'is_political': 'openai',
    'is_likely_spam': 'openai',
    'is_self_contained': 'openai',
    'is_structurally_complete': 'openai',
    'is_toxic_tiered': 'thread_pool',
    'llm_toxicity_tiered': 'openai',
    'political_stance': 'openai',
}
got = {name: spec.engine_type for name, spec in FEATURE_REGISTRY.items()}
assert got == expected, got
print('FEATURE_REGISTRY engine_type unchanged')
"
```

Expected: `FEATURE_REGISTRY engine_type unchanged`

### No parquet engine type column

```bash
PYTHONPATH=. uv run python -c "
from data_platform.generate_features.models import LabelRowMetadataModel
assert 'engine_type' not in LabelRowMetadataModel.model_fields
print('LabelRowMetadataModel has no engine_type')
"
```

Expected: `LabelRowMetadataModel has no engine_type`

### Disposable prefix cleanup before merge, if live proof ran

```bash
aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/ --recursive
aws s3 ls s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/reddit_step2_bedrock/ --recursive
```

Expected: `aws s3 ls` prints no lines.

## Must fail

- Live proof or any other write under the pinned campaign `batches/` prefix.
- Leaving objects under the disposable smoke prefix if live proof ran.
- Running pytest.
- Running the 400,000 row production job.
