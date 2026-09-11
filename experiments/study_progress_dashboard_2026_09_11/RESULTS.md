# Study progress, September 2026 run

Snapshot 2026_09_11-12:26:10 UTC. Export 2026_09_11-12:26:09.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 1,128 |
| Finished | 1,072 |
| Saved files | 1,074 |
| Labels | 21,480 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 27.6% |
| Label progress | 27.7% |
| Missing from export | 56 |
| Missing after 20-minute grace | 53 |
| Attrition after grace | 4.7% |

Prolific has finished 1,072 of 3,879 feeds (27.6%). Prolific has assigned a larger share of Democrat slots (34.0% assigned vs 24.2% Republican). The busiest assignment hour is 2026-09-10 18:00 UTC, and assignments in the three busiest hours are 79.6% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 659 | 630 | 1,940 | 34.0% | 95.6% |
| Republican | 469 | 442 | 1,939 | 24.2% | 94.2% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 8,581 | 4,019 | 12,600 | 68.1% | 31.9% | 68.1% | 31.9% | 53 | 3 |
| Republican | 6,296 | 2,584 | 8,880 | 70.9% | 29.1% | 70.9% | 29.1% | 57 | 4 |
| All | 14,877 | 6,603 | 21,480 | 69.3% | 30.7% | 69.3% | 30.7% | 110 | 7 |

Per-user keep rate (all finished): mean 69.3%, median 70.0%, SD 21.8%.

Per-user remove rate (all finished): mean 30.7%, median 30.0%, SD 21.8%.

110 people kept every scored post. 7 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 2,520 | 14.8% |
| Democrat | Middle | 6,300 | 28.0% |
| Democrat | High | 3,780 | 49.8% |
| Republican | Low | 2,664 | 16.9% |
| Republican | Middle | 4,440 | 27.9% |
| Republican | High | 1,776 | 50.3% |

Pooled Democrat remove is 31.9% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 2,520 | 20.0% |
| Democrat | Middle | 6,300 | 50.0% |
| Democrat | High | 3,780 | 30.0% |
| Republican | Low | 2,664 | 30.0% |
| Republican | Middle | 4,440 | 50.0% |
| Republican | High | 1,776 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 6,300 | 32.4% |
| Democrat | Right | 6,300 | 31.4% |
| Republican | Left | 4,440 | 29.2% |
| Republican | Right | 4,440 | 29.0% |

## Attention

Pass rate 78.5% (842 passed, 230 failed).

Remove share among people who passed: 29.4%. Among people who failed: 35.5%.

94 of 110 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.4%. Democrat passers 30.5%. Republican passers 27.7%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 17,457 |
| Catalog posts | 18,899 |
| Posts with 1 label | 13,671 |
| Posts with 2 labels | 3,550 |
| Posts with 3 or more | 236 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 2,592 | 10,463 | 24.8% |
| 2 | Left, middle toxicity | 5,370 | 22,001 | 24.4% |
| 3 | Left, high toxicity | 2,778 | 13,096 | 21.2% |
| 4 | Right, low toxicity | 2,592 | 8,796 | 29.5% |
| 5 | Right, middle toxicity | 5,370 | 16,594 | 32.4% |
| 6 | Right, high toxicity | 2,778 | 6,630 | 41.9% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `outputs/dashboard_payload.json`
