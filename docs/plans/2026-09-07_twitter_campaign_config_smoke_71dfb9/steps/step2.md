# Step 2: Add the campaign YAML and the one-id loader

## Scope

- **Caller:** `data_platform.generate_features.twitter_campaign_config.load_twitter_campaign_config`
- **Task:** Check in the campaign YAML and load it only for campaign id `twitter_2026_09_06_192847_llm_features_v1`.
- **Out of scope:** S3 upload, `generate_twitter_features` campaign flags, smoke, watcher, changing `FEATURE_REGISTRY`, pytest.

## Files to inspect (read-only)

- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md` (required YAML fields)
- `/workspace/data_platform/generate_features/registry.py` (do not change defaults; confirm the seven feature names)

## Files allowed to change

- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml` (new)
- `/workspace/data_platform/generate_features/twitter_campaign_config.py` (new)

## Files forbidden to change

- `/workspace/data_platform/generate_features/registry.py`
- `/workspace/data_platform/scripts/migrate_twitter_preprocessed_to_s3.py`
- `/workspace/data_platform/scripts/verify_twitter_preprocessed_s3.py`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## YAML contents (exact)

Path: `data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`

```yaml
campaign_id: twitter_2026_09_06_192847_llm_features_v1
platform: twitter
dataset_id: twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547
preprocessed_run: "2026_09_06-19:28:47"
row_count: 6374
batch_size: 2000
engine_type: openai
model_id: gpt-5.4-nano
features:
  - is_news_or_opinion
  - is_political
  - is_likely_spam
  - is_self_contained
  - is_structurally_complete
  - political_stance
  - llm_toxicity_tiered
```

Quote `preprocessed_run` so YAML keeps the timestamp as a string.

Feature order is the serial run order. Do not add Perspective or Bedrock features.

## Work

1. Write the YAML with the fields above and no extra keys.
2. Add `load_twitter_campaign_config(campaign_id: str) -> dict`.
3. If `campaign_id` is not `twitter_2026_09_06_192847_llm_features_v1`, raise `ValueError` that names the rejected id.
4. On the accepted id, read the YAML and return a dict with at least `row_count`, `engine_type`, and `features` so the check command prints `6374 openai 7`.
5. Do not call `FEATURE_REGISTRY` to rewrite defaults.

The Twitter feature generator does not load this YAML. Bluesky campaign mode also takes campaign id from the command line. The loader is the identity check for this campaign.

## Contracts (implement-from-spec Phase 3)

- Accepted campaign id: `twitter_2026_09_06_192847_llm_features_v1`
- Return type: `dict` with YAML keys
- Rejected id: `ValueError` whose message contains the bad id string

## Given / when / then (Phase 4, no pytest)

```text
given the checked-in Twitter campaign YAML
when load_twitter_campaign_config("twitter_2026_09_06_192847_llm_features_v1")
then row_count is 6374, engine_type is openai, and features has length 7

given the same loader
when load_twitter_campaign_config("bluesky_2026_09_03_235130_llm_features_v1")
then raise ValueError naming bluesky_2026_09_03_235130_llm_features_v1
and the process exit code is non-zero
```

## Must pass

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; c=load_twitter_campaign_config('twitter_2026_09_06_192847_llm_features_v1'); print(c['row_count'], c['engine_type'], len(c['features']))"
```

Expected: `6374 openai 7`

```bash
PYTHONPATH=. uv run python -c "from data_platform.generate_features.twitter_campaign_config import load_twitter_campaign_config; load_twitter_campaign_config('bluesky_2026_09_03_235130_llm_features_v1')"
```

Expected: non-zero exit and `ValueError` naming `bluesky_2026_09_03_235130_llm_features_v1`.

Copy both command outputs to `/opt/cursor/artifacts/`.

## Must fail

- Accepting any campaign id other than `twitter_2026_09_06_192847_llm_features_v1`
- Changing `FEATURE_REGISTRY` defaults
- Adding pytest files

## Done when

The YAML is checked in. The loader returns the seven features for this campaign id and rejects any other id.
