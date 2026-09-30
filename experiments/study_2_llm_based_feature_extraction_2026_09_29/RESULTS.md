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

## Step 4: clusters

`features=19536 keep_features=9534 remove_features=10019 clusters=30 noise=0`

K-means, seed 1, 15 clusters for features mined from kept posts and 15 for features mined from removed posts. Vectors were not scaled. Seventeen features mined from both sides are in both fits. Within each side, `000` is the largest group. The phrase is the feature nearest the group center.

| Cluster | Features | Nearest phrase |
| --- | ---: | --- |
| kept_000 | 1,446 | Concern about armed extremists, authoritarian government, or corporate influence |
| kept_001 | 1,031 | Criticism aimed at parties, politicians, ideologies, or institutions |
| kept_002 | 853 | Policy prescriptions or arguments about government action |
| kept_003 | 837 | Predictions about elections or partisan behavior |
| kept_004 | 686 | Substantive factual or quasi-factual claims about policy, law, or institutions |
| kept_005 | 678 | Occasional italicized emphasis and slogan-like phrasing |
| kept_006 | 648 | Rhetorical challenges to an opposing position |
| kept_007 | 551 | Abortion rights, gun control, and immigration policy |
| kept_008 | 524 | Longer explanatory passages and multi-sentence arguments |
| kept_009 | 498 | Political leaders, parties, institutions, and policies as targets |
| kept_010 | 448 | Contrastive framing with “but,” “while,” and “instead” |
| kept_011 | 406 | Named politicians, institutions, and policy terms |
| kept_012 | 361 | Occasional profanity embedded in argument rather than sustained insult |
| kept_013 | 318 | Elite-versus-public framing involving bureaucrats, billionaires, or party establishments |
| kept_014 | 249 | Persuasion through explanation and political argument |
| removed_000 | 1,124 | Mobilizing partisan hostility through alarmist framing |
| removed_001 | 1,092 | Culture-war claims about policing, transgender sports, abortion, and border enforcement |
| removed_002 | 1,011 | Provocative mockery intended to demean an opposing side |
| removed_003 | 917 | Opponents portrayed as stupid, fanatical, corrupt, or dangerous |
| removed_004 | 868 | All-caps commands, slogans, and repeated emphasis |
| removed_005 | 817 | Sweeping accusations of lying, corruption, criminality, or authoritarian takeover |
| removed_006 | 805 | Calls for exclusion, punishment, or removal of opponents |
| removed_007 | 590 | Broad partisan out-groups such as Republicans, Democrats, liberals, and MAGA supporters |
| removed_008 | 577 | Derogatory labels such as 'moron,' 'thugs,' and 'pigs' |
| removed_009 | 488 | Direct attacks on named politicians and their supporters |
| removed_010 | 482 | Short, slogan-like statements and blunt insults |
| removed_011 | 378 | Heavy profanity and vulgar insults |
| removed_012 | 355 | Direct second-person address with insults |
| removed_013 | 310 | Collective blame assigned to voters or broad partisan populations |
| removed_014 | 205 | Hostile venting and outrage |

## Step 5: named features

Smoke named `kept_000` through `kept_004`. The table scales that run to all 30 clusters. The runtime scales the smoke wall time by the number of groups of 8 requests.

| Value | Low | Median | High |
| --- | --- | --- | --- |
| Runtime (minutes) | 0.2 | 0.2 | 0.2 |
| Input tokens | 19,008 | 23,760 | 28,512 |
| Output tokens | 1,296 | 1,620 | 1,944 |
| Price (USD) | $0.05 | $0.07 | $0.08 |

| Cluster | Smoke name |
| --- | --- |
| kept_000 | Policy Consequence Warnings and Civic Appeals |
| kept_001 | Political Actor and Institution Criticism |
| kept_002 | Substantive Policy Advocacy and Tradeoffs |
| kept_003 | Political Strategy and Electoral Consequences |
| kept_004 | Substantive Policy and Institutional Claims |

## Step 6: Jev labels

Smoke labeled the first 5 stimulus pairs, one request each, with all 30 features. The table scales that sample to 20,000 pairs. The runtime median is the 1,000-request-per-minute cap, which is 20 minutes.

| Value | Low | Median | High |
| --- | --- | --- | --- |
| Runtime (minutes) | 16.0 | 20.0 | 24.0 |
| Input tokens | 73,856,000 | 92,320,000 | 110,784,000 |
| Output tokens | 12,848,000 | 16,060,000 | 19,272,000 |
| Price (USD) | $3.10 | $3.88 | $4.65 |

`smoke_pairs=5 features=30 requests_per_pair=1`

## Step 7: analyses

## Step 7: analyses
