## Platform counts

| decision | Bluesky | Reddit | Twitter |
|---|---:|---:|---:|
| keep | 3123 | 9322 | 2751 |
| remove | 751 | 3582 | 471 |

## Platform proportions

| decision | Bluesky | Reddit | Twitter |
|---|---:|---:|---:|
| keep | 0.8061 | 0.7224 | 0.8538 |
| remove | 0.1939 | 0.2776 | 0.1462 |

## Platform by toxicity proportions

| decision | Bluesky low toxicity | Bluesky medium toxicity | Bluesky high toxicity | Reddit low toxicity | Reddit medium toxicity | Reddit high toxicity | Twitter low toxicity | Twitter medium toxicity | Twitter high toxicity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| keep | 0.9677 | 0.8138 | 0.4843 | 0.9332 | 0.8140 | 0.4661 | 0.9629 | 0.8021 | 0.4359 |
| remove | 0.0323 | 0.1862 | 0.5157 | 0.0668 | 0.1860 | 0.5339 | 0.0371 | 0.1979 | 0.5641 |

## Four-cell counts

| cell | count | share |
|---|---:|---:|
| unanimous_keep | 5280 | 0.2753 |
| majority_keep | 9914 | 0.5170 |
| majority_remove | 3547 | 0.1850 |
| unanimous_remove | 435 | 0.0227 |

## Vote funnel

| metric | count |
|---|---:|
| posts_after_vote_clean | 20000 |
| posts_dropped_lt_3_raters | 4 |
| posts_dropped_ties | 820 |
| posts_remaining | 19176 |

## Remove votes on posts with 5 labels

Each post in this table has exactly five cleaned labels. The count is how many of those five labels are remove.

| remove votes | posts |
|---:|---:|
| 0 | 3962 |
| 1 | 4511 |
| 2 | 3277 |
| 3 | 1881 |
| 4 | 934 |
| 5 | 319 |

![Posts with 5 labels by number of remove votes](outputs/five_label_remove_histogram.png)
