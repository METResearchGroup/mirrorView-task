# Preprocessing

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Once we get raw posts, we need to filter and preprocess them.

1. Pass in the `dataset_id`.
2. Collect the raw runs for that `dataset_id`.
3. Add standardized columns.
4. Filter out duplicate (a) records that have been preprocessed already, (b) duplicate records, or (c) records which have been already been used as stimuli.
5. Do integration-specific preprocessing.
6. Filter out records based on integration-specific validators.

The flow looks something like this:

```mermaid
flowchart TD
  step1["1. Pass in the dataset_id"]
  step2["2. Collect the raw runs for that dataset_id"]
  step3["3. Add standardized columns"]
  step4["4. Filter out duplicate records"]
  step4a["(a) already preprocessed"]
  step4b["(b) duplicate records"]
  step4c["(c) already used as stimuli"]
  step5["5. Do integration-specific preprocessing"]
  step6["6. Filter out records based on integration-specific validators."]

  step1 --> step2 --> step3 --> step4
  step4 --> step4a
  step4 --> step4b
  step4 --> step4c
  step4a --> step5
  step4b --> step5
  step4c --> step5
  step5 --> step6
```
