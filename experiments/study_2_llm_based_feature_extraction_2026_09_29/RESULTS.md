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

Full run: `labeled_pairs=20000 features=30 requests=20000 deadletters=0`

## Step 7: analyses

Jev labeled all 20,000 pairs on the 30 named features. A feature counts as present when its probability is at least 0.7. Counts are not compared across groups, because the groups differ in size. The page is `public/study-2-features.html`, served at `/study-2-features`. The toxicity section and the remove-votes section also include a line chart of every feature as a proportion of that group. Grey lines are the unlabeled features. Blue lines are the policy and institution features. Red lines are the hostility features. The y-axis is that proportion, shown to three decimal places.

For lean, both left and right pairs are led by Political Actor and Institution Criticism, then Political and Institutional Targets. For toxicity, low and medium pairs are also led by that institutional criticism, while high-toxicity pairs are led by Escalatory Partisan Hostility and Hostile Outrage Venting. For remove votes, pairs with 0, 1, or 2 remove votes are led by institutional criticism, and pairs with 3, 4, or 5 remove votes are led by Escalatory Partisan Hostility.

S3 keys:

- `analyses/top_features_by_lean.csv`
- `analyses/top_features_by_toxicity.csv`
- `analyses/top_features_by_remove_votes.csv`

### Lean

Left pairs (11,550) and right pairs (8,450) share the same top three features: Political Actor and Institution Criticism, Political and Institutional Targets, and Specific Political and Institutional References.

| Rank | Left (11,550 pairs) | Pairs | Right (8,450 pairs) | Pairs |
| ---: | --- | ---: | --- | ---: |
| 1 | Political Actor and Institution Criticism | 9,810 | Political Actor and Institution Criticism | 6,542 |
| 2 | Political and Institutional Targets | 9,252 | Political and Institutional Targets | 6,317 |
| 3 | Specific Political and Institutional References | 8,665 | Specific Political and Institutional References | 6,277 |
| 4 | Escalatory Partisan Hostility | 8,581 | Escalatory Partisan Hostility | 5,438 |
| 5 | Hostile Outrage Venting | 7,225 | Substantive Policy and Institutional Claims | 4,473 |
| 6 | Sweeping Unsubstantiated Political Accusations | 6,563 | Partisan Mockery and Taunting | 4,445 |
| 7 | Partisan Mockery and Taunting | 6,317 | Hostile Outrage Venting | 4,273 |
| 8 | Substantive Policy and Institutional Claims | 5,970 | Broad Partisan Out-Group Targeting | 3,545 |
| 9 | Derogatory Labels and Epithets | 5,039 | Sweeping Unsubstantiated Political Accusations | 3,477 |
| 10 | Partisan Collective Blame | 4,990 | Quoted Slogans and Emphatic Framing | 3,242 |

### Toxicity

Low and medium toxicity are led by criticism of political actors. High toxicity is led by escalatory hostility and outrage.

| Rank | Low (5,000) | Pairs | Medium (10,000) | Pairs | High (5,000) | Pairs |
| ---: | --- | ---: | --- | ---: | --- | ---: |
| 1 | Political Actor and Institution Criticism | 3,490 | Political Actor and Institution Criticism | 8,355 | Escalatory Partisan Hostility | 4,695 |
| 2 | Specific Political and Institutional References | 3,482 | Political and Institutional Targets | 7,882 | Hostile Outrage Venting | 4,635 |
| 3 | Substantive Policy and Institutional Claims | 3,321 | Escalatory Partisan Hostility | 7,485 | Political Actor and Institution Criticism | 4,507 |
| 4 | Political and Institutional Targets | 3,292 | Specific Political and Institutional References | 7,433 | Political and Institutional Targets | 4,395 |
| 5 | Policy Advocacy and Tradeoff Arguments | 2,382 | Hostile Outrage Venting | 6,035 | Specific Political and Institutional References | 4,027 |
| 6 | Policy Consequence Warnings and Civic Mobilization | 1,870 | Sweeping Unsubstantiated Political Accusations | 5,575 | Partisan Mockery and Taunting | 3,935 |
| 7 | Escalatory Partisan Hostility | 1,839 | Partisan Mockery and Taunting | 5,538 | Derogatory Labels and Epithets | 3,649 |
| 8 | Quoted Slogans and Emphatic Framing | 1,689 | Substantive Policy and Institutional Claims | 5,535 | Sweeping Unsubstantiated Political Accusations | 3,229 |
| 9 | Culture-War Policy Issues | 1,649 | Broad Partisan Out-Group Targeting | 4,551 | Blanket Demonization of Political Opponents | 2,927 |
| 10 | Explicit Contrastive Framing | 1,485 | Partisan Collective Blame | 4,387 | Broad Partisan Out-Group Targeting | 2,600 |

### Remove votes

Among the 15,113 five-label pairs, 0 to 2 remove votes are led by institutional criticism. 3 to 5 remove votes are led by Escalatory Partisan Hostility. At 5 remove votes, Hostile Outrage Venting is second, on 307 of 324 pairs.

| Rank | 0 (3,986) | 1 (4,592) | 2 (3,332) | 3 (1,929) | 4 (950) | 5 (324) |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Political Actor and Institution Criticism (2,951) | Political Actor and Institution Criticism (3,707) | Political Actor and Institution Criticism (2,862) | Escalatory Partisan Hostility (1,723) | Escalatory Partisan Hostility (888) | Escalatory Partisan Hostility (313) |
| 2 | Specific Political and Institutional References (2,751) | Political and Institutional Targets (3,496) | Political and Institutional Targets (2,712) | Political Actor and Institution Criticism (1,709) | Hostile Outrage Venting (860) | Hostile Outrage Venting (307) |
| 3 | Political and Institutional Targets (2,747) | Specific Political and Institutional References (3,401) | Escalatory Partisan Hostility (2,654) | Political and Institutional Targets (1,658) | Political and Institutional Targets (838) | Political and Institutional Targets (293) |
| 4 | Substantive Policy and Institutional Claims (2,581) | Escalatory Partisan Hostility (2,974) | Specific Political and Institutional References (2,567) | Hostile Outrage Venting (1,569) | Political Actor and Institution Criticism (828) | Political Actor and Institution Criticism (292) |
| 5 | Escalatory Partisan Hostility (1,978) | Substantive Policy and Institutional Claims (2,674) | Hostile Outrage Venting (2,246) | Specific Political and Institutional References (1,557) | Specific Political and Institutional References (756) | Specific Political and Institutional References (256) |
| 6 | Policy Advocacy and Tradeoff Arguments (1,780) | Partisan Mockery and Taunting (2,249) | Partisan Mockery and Taunting (2,060) | Partisan Mockery and Taunting (1,434) | Partisan Mockery and Taunting (745) | Derogatory Labels and Epithets (254) |
| 7 | Policy Consequence Warnings and Civic Mobilization (1,490) | Hostile Outrage Venting (2,248) | Sweeping Unsubstantiated Political Accusations (1,908) | Sweeping Unsubstantiated Political Accusations (1,222) | Derogatory Labels and Epithets (686) | Partisan Mockery and Taunting (246) |
| 8 | Sweeping Unsubstantiated Political Accusations (1,456) | Sweeping Unsubstantiated Political Accusations (2,178) | Substantive Policy and Institutional Claims (1,641) | Derogatory Labels and Epithets (1,180) | Sweeping Unsubstantiated Political Accusations (599) | Blanket Demonization of Political Opponents (206) |
| 9 | Quoted Slogans and Emphatic Framing (1,383) | Broad Partisan Out-Group Targeting (1,766) | Derogatory Labels and Epithets (1,565) | Broad Partisan Out-Group Targeting (1,014) | Blanket Demonization of Political Opponents (583) | Brief Slogan-Like Insult Attacks (202) |
| 10 | Culture-War Policy Issues (1,355) | Quoted Slogans and Emphatic Framing (1,710) | Broad Partisan Out-Group Targeting (1,560) | Blanket Demonization of Political Opponents (986) | Broad Partisan Out-Group Targeting (518) | Sweeping Unsubstantiated Political Accusations (198) |
