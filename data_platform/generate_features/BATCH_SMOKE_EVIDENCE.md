# Step 5 batch writer smoke evidence (temporary, deleted before merge)

Commit under test: `7037ee6`. Date: 2026-09-06 (UTC). Region `us-east-2`, bucket `mirrorview-experimental-artifacts`.
All writes and deletes were under `data_platform/data/_smoke/step5_batch_writer/`. No OpenAI call was made.

## Offline path helper check

```text
feature_prefix OK
run_id OK
```

## Live one-batch write check (first run)

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/
batch_key=s3://mirrorview-experimental-artifacts/data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/batches/part-00000.parquet
batch_sha256=5e6bae8ce24d906e71aefd2889cd9d1bcb2bb5e01a4583df1ebb646f0e4b3c9c
manifest_updated=true
progress_appended=true
intermediate_tag=true
canonical_batches_prefix_touched=false
```

Independent read-back of the written objects:

```text
data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/batches/part-00000.parquet 5477 [{'Key': 'intermediate-artifact', 'Value': 'true'}]
data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/manifest.json 851 []
data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/progress.jsonl 423 []
recomputed_sha256= 5e6bae8ce24d906e71aefd2889cd9d1bcb2bb5e01a4583df1ebb646f0e4b3c9c
columns= ['source_record_id', 'run_id', 'batch_id', 'request_id', 'attempt_count', 'label_timestamp', 'category']
rows= 10
```

## Resume-without-rewrite check (second run, same command)

```text
batch_rewrite_refused=true
next_part_index=1
canonical_batches_prefix_touched=false
```

## Disposable prefix cleanup

```text
delete: data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/batches/part-00000.parquet
delete: data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/manifest.json
delete: data_platform/data/_smoke/step5_batch_writer/is_news_or_opinion/progress.jsonl
remaining_under_disposable_prefix= 0
canonical_batches_key_count= 0
canonical_campaign_features_key_count= 0
smoke_root_key_count= 0
```

`data_platform/scripts/verify_bluesky_s3_migration.py`: `OK: 53/53 objects present with matching sha256`.
