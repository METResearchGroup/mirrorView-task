# Creating feature generation training sets

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

The shape of the dataset, for each classifier, should look something like:

- uri
- label_timestamp
- text
- {label(s)}

Steps:

- Initialize folders, `training_data/{is_likely_spam,is_news_or_opinion,is_political,is_self_contained,is_structurally_complete,is_toxic_tiered,political_stance}` (matching the generated features from `data_platform/generate_features/`).
- Iterate through `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data` (this is the full path, not the relative path, as this is in a separate local folder).
- For each platform (bluesky,twitter,reddit), go through its subfolders (these are the dataset IDs).
- For each dataset ID, you'll see raw, preprocessed, features, and curated.
- For each feature: open the corresponding `{feature}.csv` file and then the preprocessed records and create a hydrated view that matches the shape of the intended dataset above.
- Write it as `training_data/{category}/{dataset_id}_{timestamp}.parquet`.
- Do this to completion, across all of `/Users/mark/Documents/work/lab_data_integrations_interface/data_platform/data`.
- Then upload to S3. Details are bucket = `met-ml-training `, s3 prefix = `mirrorview/create_feature_generation_training_sets_2026_09_04/`. Within that prefix, upload as `{category}/{dataset_id}_{timestamp}.parquet`, for each file.

Report back when done.
