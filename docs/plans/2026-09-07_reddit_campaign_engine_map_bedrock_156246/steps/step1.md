# Step 1: Add the campaign engine map, feature paths, and Reddit campaign flags

## Scope

- **Caller:** `data_platform/generate_features/generate_reddit_features.py` `generate_reddit_features` in campaign mode, which calls `generate_platform_campaign_feature`, which calls `generate_campaign_feature`.
- **Task:** Add a campaign only engine map for `reddit_2026_09_03_233928_llm_features_v1`, restore `FeaturePaths.canonical` as a forwarder to `FeaturePaths.for_campaign`, record `engine_type` on manifests and local campaign metadata, accept OpenAI or Bedrock in campaign validation, and add campaign flags to the Reddit Python API.
- **Out of scope:** Bedrock Converse prompt and content filter changes, Bedrock part writer, content filter OpenAI retry, live S3 writes, pytest, watcher platform flags, Reddit smoke modules, registry engine defaults.

Phase 4 for this package is the offline `python -c` smoke in Step 3, not pytest. Do not add files under `tests/`. Run unattended. Skip Phase 3 approval.

## Files to inspect

- `data_platform/generate_features/generate_features.py`
- `data_platform/generate_features/platform_cli.py`
- `data_platform/generate_features/s3_feature_campaign.py`
- `data_platform/generate_features/generate_reddit_features.py`
- `data_platform/generate_features/generate_bluesky_features.py`
- `data_platform/generate_features/metadata.py`
- `data_platform/generate_features/models.py` (read only)
- `data_platform/generate_features/registry.py` (read only)
- `data_platform/generate_features/feature_progress_watcher.py`
- `data_platform/generate_features/smoke_bluesky_campaign.py`
- `data_platform/curate/consolidate_bluesky_llm_campaign.py`
- `lib/constants.py`

## Files allowed to change

- `data_platform/generate_features/campaign_engine_map.py` (new)
- `data_platform/generate_features/generate_features.py`
- `data_platform/generate_features/platform_cli.py`
- `data_platform/generate_features/s3_feature_campaign.py`
- `data_platform/generate_features/generate_reddit_features.py`
- `data_platform/generate_features/metadata.py`
- `data_platform/generate_features/feature_progress_watcher.py` (FeaturePaths fix only)
- `data_platform/generate_features/smoke_bluesky_campaign.py` (FeaturePaths fix only)
- `data_platform/curate/consolidate_bluesky_llm_campaign.py` (FeaturePaths fix only)

## Files forbidden to change

- `data_platform/utils/storage.py`
- `data_platform/generate_features/registry.py`
- `data_platform/generate_features/models.py`
- `data_platform/generate_features/engines/bedrock_engine.py` (Step 2)
- `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py`
- Any file under `tests/`
- `data_platform/data/bluesky/**`
- Feature prompt modules under `data_platform/generate_features/*/generate_feature.py`
- `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/**`
- `CHANGELOG.md`

## Locked identities

| Field | Value |
| ----- | ----- |
| Reddit campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Bluesky campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Platform | `reddit` |
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| OpenAI engine string | `openai` |
| Bedrock engine string | `bedrock` |

Engine map for the Reddit campaign only:

| Feature | Engine |
| ------- | ------ |
| `is_news_or_opinion` | `openai` |
| `is_political` | `openai` |
| `political_stance` | `openai` |
| `llm_toxicity_tiered` | `openai` |
| `is_likely_spam` | `bedrock` |
| `is_self_contained` | `bedrock` |
| `is_structurally_complete` | `bedrock` |

Any other campaign id, including the Bluesky campaign, resolves to `openai`. A Reddit campaign feature that is missing from the map raises `ValueError`. Thread pool features stay rejected.

## Contracts

`campaign_engine_type(campaign_id: str, feature: str) -> str` in `campaign_engine_map.py` is the resolver. `generate_campaign_feature` uses it instead of comparing `spec.engine_type` to the hardcoded `CAMPAIGN_ENGINE_TYPE` string. Keep `CAMPAIGN_ENGINE_TYPE = "openai"` because Bluesky smoke still imports it.

`FeaturePaths.canonical` is a classmethod alias that forwards to `FeaturePaths.for_campaign` with the same arguments, including optional `platform` and `dataset_id`. Default platform and dataset id stay the existing Bluesky values. Reddit campaign generation already calls `for_campaign` with `campaign.platform` and `campaign.dataset_id`. Watcher, Bluesky smoke, and Bluesky consolidate must compile. Prefer `for_campaign` at call sites that already have a dataset id, and pass `platform="bluesky"` there so a Reddit campaign id cannot silently inherit Bluesky defaults from copied call sites.

`new_manifest` includes `engine_type`. `MANIFEST_IDENTITY_FIELDS` includes `engine_type`. On resume, a missing `engine_type` on an existing manifest compares as `openai` so current Bluesky campaigns still resume. `model_id` on a Bedrock campaign manifest is `lib.constants.DEFAULT_BEDROCK_NOVA_MICRO`. `model_id` on an OpenAI campaign manifest stays `model_id_for_spec`.

Local campaign metadata is a `metadata.json` under the local campaign run directory. Record `engine_type` on the feature entry. Do not edit `models.py`. Do not add `engine_type` to parquet.

`platform_cli` campaign validation accepts map values `openai` or `bedrock`. It still rejects `is_toxic_tiered`.

`generate_reddit_features` matches `generate_bluesky_features`: optional `campaign_id` and `preprocessed_run`, campaign mode returns `{feature_name: prefix_uri}`.

Keep functions under 20 lines. Named constants. Numpy docstrings. Module docstrings include a `uv run python ...` command when the file is a script.

## Ordered units of work

1. `campaign_engine_map.py` constants and `campaign_engine_type`.
2. `FeaturePaths.canonical` alias plus `active_bedrock_state_key`.
3. Feature path call sites in watcher, Bluesky smoke, and Bluesky consolidate.
4. `model_id_for_campaign_engine` and `write_campaign_local_metadata` in `metadata.py`.
5. `new_manifest` and identity check for `engine_type`.
6. `generate_campaign_feature` resolves the campaign engine and writes local metadata. OpenAI path stays as today. Bedrock path may raise `NotImplementedError` until Step 2.
7. `platform_cli` campaign validation uses the map.
8. Reddit Python API and module docstring campaign example.

## Must pass

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

Expected stdout: `campaign_engine_map OK`

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
alias = FeaturePaths.canonical(
    'reddit_2026_09_03_233928_llm_features_v1',
    'is_political',
    platform='reddit',
    dataset_id='reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079',
)
assert alias.prefix == p.prefix
print('reddit FeaturePaths OK')
"
```

Expected stdout: `reddit FeaturePaths OK`

## Must fail

- Changing `FEATURE_REGISTRY` default `engine_type` values.
- Reddit campaign generation that omits platform or dataset id and inherits Bluesky defaults.
- Campaign mode that still requires `spec.engine_type == "openai"` from the registry.
- An `engine_type` field on `LabelRowMetadataModel`.
- Watcher code that posts to GitHub.
- Any file under `tests/`.
