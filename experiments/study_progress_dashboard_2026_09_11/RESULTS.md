# Study progress, September 2026 run

Snapshot 2026_09_14-19:20:30 UTC. Export 2026_09_14-19:20:27.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 2,966 |
| Finished | 2,846 |
| Saved files | 2,863 |
| Labels | 57,260 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 73.4% |
| Label progress | 73.8% |
| Missing from export | 121 |
| Missing after 20-minute grace | 113 |
| Attrition after grace | 3.8% |

Prolific has finished 2,846 of 3,879 feeds (73.4%). Prolific has assigned a larger share of Democrat slots (91.6% assigned vs 61.3% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 40.4% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,777 | 1,708 | 1,940 | 91.6% | 96.1% |
| Republican | 1,189 | 1,138 | 1,939 | 61.3% | 95.7% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 23,716 | 10,564 | 34,280 | 69.2% | 30.8% | 69.2% | 30.8% | 160 | 11 |
| Republican | 16,296 | 6,684 | 22,980 | 70.9% | 29.1% | 70.9% | 29.1% | 150 | 7 |
| All | 40,012 | 17,248 | 57,260 | 69.9% | 30.1% | 69.9% | 30.1% | 310 | 18 |

Per-user keep rate (all finished): mean 69.9%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.1%, median 30.0%, SD 21.7%.

310 people kept every scored post. 18 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,378 | 14.9% |
| Democrat | Middle | 17,424 | 27.3% |
| Democrat | High | 9,478 | 49.6% |
| Republican | Low | 6,894 | 16.1% |
| Republican | Middle | 11,490 | 28.4% |
| Republican | High | 4,596 | 50.3% |

Pooled Democrat remove is 30.8% vs Republican 29.1%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,378 | 21.5% |
| Democrat | Middle | 17,424 | 50.8% |
| Democrat | High | 9,478 | 27.7% |
| Republican | Low | 6,894 | 30.0% |
| Republican | Middle | 11,490 | 50.0% |
| Republican | High | 4,596 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 18,690 | 31.8% |
| Democrat | Right | 15,590 | 29.6% |
| Republican | Left | 11,490 | 29.4% |
| Republican | Right | 11,490 | 28.8% |

## Attention

Pass rate 78.4% (2,231 passed, 615 failed).

Remove share among people who passed: 28.7%. Among people who failed: 35.4%.

267 of 310 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.7%. Democrat passers 29.4%. Republican passers 27.5%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,860 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,430 |
| Posts with 2 labels | 4,695 |
| Posts with 3 or more | 12,735 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 7,186 | 10,463 | 68.7% |
| 2 | Left, middle toxicity | 15,090 | 22,001 | 68.6% |
| 3 | Left, high toxicity | 7,904 | 13,096 | 60.4% |
| 4 | Right, low toxicity | 7,086 | 8,796 | 80.6% |
| 5 | Right, middle toxicity | 13,824 | 16,594 | 83.3% |
| 6 | Right, high toxicity | 6,170 | 6,630 | 93.1% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
