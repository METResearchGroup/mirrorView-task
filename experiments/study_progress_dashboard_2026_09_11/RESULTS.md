# Study progress, September 2026 run

Snapshot 2026_09_14-03:40:06 UTC. Export 2026_09_14-03:40:05.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 2,265 |
| Finished | 2,179 |
| Saved files | 2,193 |
| Labels | 43,860 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 56.2% |
| Label progress | 56.5% |
| Missing from export | 86 |
| Missing after 20-minute grace | 86 |
| Attrition after grace | 3.8% |

Prolific has finished 2,179 of 3,879 feeds (56.2%). Prolific has assigned a larger share of Democrat slots (68.4% assigned vs 48.4% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 48.7% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,326 | 1,282 | 1,940 | 68.4% | 96.7% |
| Republican | 939 | 897 | 1,939 | 48.4% | 95.5% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 17,672 | 8,068 | 25,740 | 68.7% | 31.3% | 68.7% | 31.3% | 115 | 8 |
| Republican | 12,797 | 5,323 | 18,120 | 70.6% | 29.4% | 70.6% | 29.4% | 119 | 7 |
| All | 30,469 | 13,391 | 43,860 | 69.5% | 30.5% | 69.5% | 30.5% | 234 | 15 |

Per-user keep rate (all finished): mean 69.5%, median 70.0%, SD 21.6%.

Per-user remove rate (all finished): mean 30.5%, median 30.0%, SD 21.6%.

234 people kept every scored post. 15 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 5,150 | 14.8% |
| Democrat | Middle | 12,870 | 27.2% |
| Democrat | High | 7,720 | 49.3% |
| Republican | Low | 5,436 | 16.4% |
| Republican | Middle | 9,060 | 28.8% |
| Republican | High | 3,624 | 50.2% |

Pooled Democrat remove is 31.3% vs Republican 29.4%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 5,150 | 20.0% |
| Democrat | Middle | 12,870 | 50.0% |
| Democrat | High | 7,720 | 30.0% |
| Republican | Low | 5,436 | 30.0% |
| Republican | Middle | 9,060 | 50.0% |
| Republican | High | 3,624 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 12,870 | 31.8% |
| Democrat | Right | 12,870 | 30.9% |
| Republican | Left | 9,060 | 29.8% |
| Republican | Right | 9,060 | 29.0% |

## Attention

Pass rate 78.4% (1,708 passed, 471 failed).

Remove share among people who passed: 29.2%. Among people who failed: 35.3%.

202 of 234 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.2%. Democrat passers 30.2%. Republican passers 27.7%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,816 |
| Catalog posts | 18,899 |
| Posts with 1 label | 3,110 |
| Posts with 2 labels | 9,004 |
| Posts with 3 or more | 6,702 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 5,293 | 10,463 | 50.6% |
| 2 | Left, middle toxicity | 10,965 | 22,001 | 49.8% |
| 3 | Left, high toxicity | 5,672 | 13,096 | 43.3% |
| 4 | Right, low toxicity | 5,293 | 8,796 | 60.2% |
| 5 | Right, middle toxicity | 10,965 | 16,594 | 66.1% |
| 6 | Right, high toxicity | 5,672 | 6,630 | 85.5% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
