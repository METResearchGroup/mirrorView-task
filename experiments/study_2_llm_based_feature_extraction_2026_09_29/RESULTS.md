# Study 2 LLM-based feature extraction

## Step 1: cohort and batches

| Metric | Count |
| --- | --- |
| Five-label pairs | 15,113 |
| Modal keep | 11,910 |
| Modal remove | 3,203 |
| Mining batches | 320 |
| Keep pairs not in any batch | 8,710 |
| Remove pairs not in any batch | 3 |

## Step 2: mine candidate features

| Value | Low | Median | High |
| --- | --- | --- | --- |
| Runtime (minutes) | 12.3 | 15.4 | 18.4 |
| Input tokens | 647,936 | 809,920 | 971,904 |
| Output tokens | 180,992 | 226,240 | 271,488 |
| Price (USD) | $3.47 | $4.33 | $5.20 |

The runtime median scales the smoke wall time by the number of groups of 8 requests (40 groups for 320 requests versus 1 group for the 5-request smoke).

Full run: `mined_batches=320 candidate_features=20573`

| Side / category | Count |
| --- | --- |
| features_from_kept_posts | 10,145 |
| features_from_removed_posts | 10,428 |
| lexical | 3,414 |
| topic_subject | 3,529 |
| semantic_content | 3,498 |
| pragmatics | 3,418 |
| target | 3,192 |
| structure | 3,522 |
| **Total** | **20,573** |

## Step 3: deduplicated features

`candidate_records=20573 distinct_features=19536 titan_tokens=209004 titan_cost_usd=0.00418008`

| Category | Distinct features |
| --- | --- |
| lexical | 3,126 |
| topic_subject | 3,453 |
| semantic_content | 3,466 |
| pragmatics | 3,126 |
| target | 3,130 |
| structure | 3,235 |
| **Total** | **19,536** |

## Step 4: cluster features

## Step 5: name clusters

## Step 6: Jev labels

## Step 7: analyses
