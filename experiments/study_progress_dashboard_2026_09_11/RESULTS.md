# Study progress, September 2026 run

Snapshot 2026_09_14-17:11:27 UTC. Export 2026_09_14-17:11:25.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 2,891 |
| Finished | 2,772 |
| Saved files | 2,789 |
| Labels | 55,780 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 71.5% |
| Label progress | 71.9% |
| Missing from export | 120 |
| Missing after 20-minute grace | 112 |
| Attrition after grace | 3.9% |

Prolific has finished 2,772 of 3,879 feeds (71.5%). Prolific has assigned a larger share of Democrat slots (89.2% assigned vs 59.8% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 41.5% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,731 | 1,665 | 1,940 | 89.2% | 96.2% |
| Republican | 1,160 | 1,107 | 1,939 | 59.8% | 95.4% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 23,131 | 10,289 | 33,420 | 69.2% | 30.8% | 69.2% | 30.8% | 156 | 11 |
| Republican | 15,868 | 6,492 | 22,360 | 71.0% | 29.0% | 71.0% | 29.0% | 147 | 7 |
| All | 38,999 | 16,781 | 55,780 | 69.9% | 30.1% | 69.9% | 30.1% | 303 | 18 |

Per-user keep rate (all finished): mean 69.9%, median 70.0%, SD 21.7%.

Per-user remove rate (all finished): mean 30.1%, median 30.0%, SD 21.7%.

303 people kept every scored post. 18 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,206 | 14.8% |
| Democrat | Middle | 16,994 | 27.3% |
| Democrat | High | 9,220 | 49.6% |
| Republican | Low | 6,708 | 16.0% |
| Republican | Middle | 11,180 | 28.4% |
| Republican | High | 4,472 | 50.1% |

Pooled Democrat remove is 30.8% vs Republican 29.0%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,206 | 21.6% |
| Democrat | Middle | 16,994 | 50.8% |
| Democrat | High | 9,220 | 27.6% |
| Republican | Low | 6,708 | 30.0% |
| Republican | Middle | 11,180 | 50.0% |
| Republican | High | 4,472 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 17,830 | 31.8% |
| Democrat | Right | 15,590 | 29.6% |
| Republican | Left | 11,180 | 29.3% |
| Republican | Right | 11,180 | 28.7% |

## Attention

Pass rate 78.4% (2,173 passed, 599 failed).

Remove share among people who passed: 28.6%. Among people who failed: 35.5%.

262 of 303 always-keep finishers passed the attention check.

User-mean remove among people who passed: 28.6%. Democrat passers 29.3%. Republican passers 27.4%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,858 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,490 |
| Posts with 2 labels | 5,158 |
| Posts with 3 or more | 12,210 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 6,921 | 10,463 | 66.1% |
| 2 | Left, middle toxicity | 14,505 | 22,001 | 65.9% |
| 3 | Left, high toxicity | 7,584 | 13,096 | 57.9% |
| 4 | Right, low toxicity | 6,993 | 8,796 | 79.5% |
| 5 | Right, middle toxicity | 13,669 | 16,594 | 82.4% |
| 6 | Right, high toxicity | 6,108 | 6,630 | 92.1% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
