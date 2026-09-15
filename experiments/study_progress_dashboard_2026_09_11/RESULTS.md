# Study progress, September 2026 run

Snapshot 2026_09_15-15:20:52 UTC. Export 2026_09_15-15:20:49.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,179 |
| Finished | 3,056 |
| Saved files | 3,081 |
| Labels | 61,620 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 78.8% |
| Label progress | 79.4% |
| Missing from export | 124 |
| Missing after 20-minute grace | 123 |
| Attrition after grace | 3.9% |

Prolific has finished 3,056 of 3,879 feeds (78.8%). Prolific has assigned a larger share of Democrat slots (97.7% assigned vs 66.2% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 37.7% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,895 | 1,825 | 1,940 | 97.7% | 96.3% |
| Republican | 1,284 | 1,231 | 1,939 | 66.2% | 95.9% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 25,405 | 11,335 | 36,740 | 69.2% | 30.9% | 69.2% | 30.8% | 167 | 11 |
| Republican | 17,613 | 7,267 | 24,880 | 70.8% | 29.2% | 70.8% | 29.2% | 165 | 8 |
| All | 43,018 | 18,602 | 61,620 | 69.8% | 30.2% | 69.8% | 30.2% | 332 | 19 |

Per-user keep rate (all finished): mean 69.8%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.2%, median 30.0%, SD 21.7%.

332 people kept every scored post. 19 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,688 | 14.8% |
| Democrat | Middle | 18,713 | 27.1% |
| Democrat | High | 10,339 | 49.6% |
| Republican | Low | 7,464 | 16.2% |
| Republican | Middle | 12,440 | 28.5% |
| Republican | High | 4,976 | 50.5% |

Pooled Democrat remove is 30.9% vs Republican 29.2%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,688 | 20.9% |
| Democrat | Middle | 18,713 | 50.9% |
| Democrat | High | 10,339 | 28.1% |
| Republican | Low | 7,464 | 30.0% |
| Republican | Middle | 12,440 | 50.0% |
| Republican | High | 4,976 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 21,140 | 31.8% |
| Democrat | Right | 15,600 | 29.6% |
| Republican | Left | 12,440 | 29.4% |
| Republican | Right | 12,440 | 29.0% |

## Attention

Pass rate 78.1% (2,388 passed, 668 failed).

Remove share among people who passed: 28.8%. Among people who failed: 35.1%.

283 of 332 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.8%. Democrat passers 29.5%. Republican passers 27.6%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,862 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,280 |
| Posts with 2 labels | 3,613 |
| Posts with 3 or more | 13,969 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 7,778 | 10,463 | 74.3% |
| 2 | Left, middle toxicity | 16,849 | 22,001 | 76.6% |
| 3 | Left, high toxicity | 8,953 | 13,096 | 68.4% |
| 4 | Right, low toxicity | 7,374 | 8,796 | 83.8% |
| 5 | Right, middle toxicity | 14,304 | 16,594 | 86.2% |
| 6 | Right, high toxicity | 6,362 | 6,630 | 96.0% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.8 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
