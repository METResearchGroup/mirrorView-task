# How do we get posts for the stimulus dataset?

This runbook goes over how we get the posts that end up as part of our stimulus datasets.

## Overview

We have a 4-stage pipeline for getting records for the dataset.

1. **Ingestion**: Ingest records from APIs and other sources.
2. **Preprocessing**: Given the raw records, preprocess them (e.g., removing text that's too short, non-English text, etc.)
3. **Feature generation**: Given the preprocessed posts, generate features.
4. **Curation**: Given the preprocessed posts and the features, curate the subset that you want as part of your final stimulus dataset.

We use 3 separate data sources:

1. Bluesky
2. Twitter
3. Reddit (we use both `praw` as well as the Reddit PushShift dataset)

## Where does data live?

Data is stored in the following folder format:

```markdown
data_platform/data/{platform}/{dataset_id}/
  dataset.json
  raw/{timestamp}/          posts.csv or comments.csv + metadata.json
  preprocessed/{timestamp}/ same + metadata.json
  features/                 {feature}.csv + metadata.json [+ deadletter.jsonl]
  curated/{timestamp}/      mirrorview.csv + metadata.json
```

Each platform is an independent dataset under `data_platform/data/{platform}/{dataset_id}/`. `dataset_id` is `{bluesky|reddit|twitter}_{uuid}`.

## Stage 1: Ingestion

## Stage 2: Preprocessing

Once posts are ingested, they undergo preprocessing. The preprocessing code lives in`data_platform/preprocessing`.

### Preprocessing inputs

...

### Preprocessing outputs

...

### (Preprocessing) Extra details of note

...

## Stage 3: Feature generation

## Stage 4: Curation

...

(For Reddit, asterisk this by saying we've got 2 sources, `praw` and then the Reddit PushShift data).
