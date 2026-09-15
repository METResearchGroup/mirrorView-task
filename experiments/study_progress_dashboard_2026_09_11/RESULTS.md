# Study progress, September 2026 run

Snapshot 2026_09_15-13:58:44 UTC. Export 2026_09_15-13:58:42.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,171 |
| Finished | 3,049 |
| Saved files | 3,074 |
| Labels | 61,480 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 78.6% |
| Label progress | 79.2% |
| Missing from export | 123 |
| Missing after 20-minute grace | 123 |
| Attrition after grace | 3.9% |

Prolific has finished 3,049 of 3,879 feeds (78.6%). Prolific has assigned a larger share of Democrat slots (97.4% assigned vs 66.1% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 37.8% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,889 | 1,820 | 1,940 | 97.4% | 96.3% |
| Republican | 1,282 | 1,229 | 1,939 | 66.1% | 95.9% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 25,329 | 11,311 | 36,640 | 69.1% | 30.9% | 69.2% | 30.9% | 167 | 11 |
| Republican | 17,573 | 7,267 | 24,840 | 70.7% | 29.3% | 70.8% | 29.2% | 163 | 8 |
| All | 42,902 | 18,578 | 61,480 | 69.8% | 30.2% | 69.8% | 30.2% | 330 | 19 |

Per-user keep rate (all finished): mean 69.8%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.2%, median 30.0%, SD 21.7%.

330 people kept every scored post. 19 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,688 | 14.8% |
| Democrat | Middle | 18,713 | 27.1% |
| Democrat | High | 10,239 | 49.8% |
| Republican | Low | 7,452 | 16.2% |
| Republican | Middle | 12,420 | 28.5% |
| Republican | High | 4,968 | 50.6% |

Pooled Democrat remove is 30.9% vs Republican 29.3%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,688 | 21.0% |
| Democrat | Middle | 18,713 | 51.1% |
| Democrat | High | 10,239 | 27.9% |
| Republican | Low | 7,452 | 30.0% |
| Republican | Middle | 12,420 | 50.0% |
| Republican | High | 4,968 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 21,040 | 31.8% |
| Democrat | Right | 15,600 | 29.6% |
| Republican | Left | 12,420 | 29.4% |
| Republican | Right | 12,420 | 29.1% |

## Attention

Pass rate 78.1% (2,382 passed, 667 failed).

Remove share among people who passed: 28.8%. Among people who failed: 35.1%.

281 of 330 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.8%. Democrat passers 29.5%. Republican passers 27.6%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,862 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,287 |
| Posts with 2 labels | 3,661 |
| Posts with 3 or more | 13,914 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 7,772 | 10,463 | 74.3% |
| 2 | Left, middle toxicity | 16,839 | 22,001 | 76.5% |
| 3 | Left, high toxicity | 8,849 | 13,096 | 67.6% |
| 4 | Right, low toxicity | 7,368 | 8,796 | 83.8% |
| 5 | Right, middle toxicity | 14,294 | 16,594 | 86.1% |
| 6 | Right, high toxicity | 6,358 | 6,630 | 95.9% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.8 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
