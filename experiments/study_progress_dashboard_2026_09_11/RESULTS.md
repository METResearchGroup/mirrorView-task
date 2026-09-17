# Study progress, September 2026 run

Snapshot 2026_09_17-14:51:56 UTC. Export 2026_09_17-14:51:53.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 3,404 |
| Finished | 3,275 |
| Saved files | 3,341 |
| Labels | 66,820 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 84.4% |
| Label progress | 86.1% |
| Missing from export | 130 |
| Missing after 20-minute grace | 126 |
| Attrition after grace | 3.7% |

Prolific has finished 3,275 of 3,879 feeds (84.4%). Prolific has assigned a larger share of Democrat slots (101.6% assigned vs 73.9% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 35.2% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 1,972 | 1,898 | 1,940 | 101.6% | 96.2% |
| Republican | 1,432 | 1,377 | 1,939 | 73.9% | 96.2% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 26,406 | 11,974 | 38,380 | 68.8% | 31.2% | 68.8% | 31.2% | 170 | 13 |
| Republican | 20,071 | 8,369 | 28,440 | 70.6% | 29.4% | 70.7% | 29.3% | 182 | 8 |
| All | 46,477 | 20,343 | 66,820 | 69.6% | 30.4% | 69.6% | 30.4% | 352 | 21 |

Per-user keep rate (all finished): mean 69.6%, median 70.0%, SD 21.8%.

Per-user remove rate (all finished): mean 30.4%, median 30.0%, SD 21.8%.

352 people kept every scored post. 21 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 7,920 | 15.0% |
| Democrat | Middle | 19,072 | 27.2% |
| Democrat | High | 11,388 | 49.1% |
| Republican | Low | 8,738 | 16.9% |
| Republican | Middle | 14,220 | 29.0% |
| Republican | High | 5,482 | 50.6% |

Pooled Democrat remove is 31.2% vs Republican 29.4%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 7,920 | 20.6% |
| Democrat | Middle | 19,072 | 49.7% |
| Democrat | High | 11,388 | 29.7% |
| Republican | Low | 8,738 | 30.7% |
| Republican | Middle | 14,220 | 50.0% |
| Republican | High | 5,482 | 19.3% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 22,440 | 32.2% |
| Democrat | Right | 15,940 | 29.8% |
| Republican | Left | 14,220 | 29.8% |
| Republican | Right | 14,220 | 29.1% |

## Attention

Pass rate 78.0% (2,555 passed, 720 failed).

Remove share among people who passed: 29.0%. Among people who failed: 35.5%.

300 of 352 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.0%. Democrat passers 29.9%. Republican passers 27.6%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,863 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,210 |
| Posts with 2 labels | 2,587 |
| Posts with 3 or more | 15,066 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 8,432 | 10,463 | 80.6% |
| 2 | Left, middle toxicity | 17,923 | 22,001 | 81.5% |
| 3 | Left, high toxicity | 10,305 | 13,096 | 78.7% |
| 4 | Right, low toxicity | 8,226 | 8,796 | 93.5% |
| 5 | Right, middle toxicity | 15,369 | 16,594 | 92.6% |
| 6 | Right, high toxicity | 6,565 | 6,630 | 99.0% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.9 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
