# Study progress, September 2026 run

Snapshot 2026_09_22-21:28:05 UTC. Export 2026_09_22-21:28:02.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 4,014 |
| Finished | 3,875 |
| Saved files | 3,975 |
| Labels | 79,500 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 99.9% |
| Label progress | 102.5% |
| Missing from export | 140 |
| Missing after 20-minute grace | 140 |
| Attrition after grace | 3.5% |

Prolific has finished 3,875 of 3,879 feeds (99.9%). Prolific has assigned a larger share of Democrat slots (106.3% assigned vs 100.7% Republican). The busiest assignment hour is 2026-09-11 16:00 UTC, and assignments in the three busiest hours are 29.9% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 2,062 | 1,989 | 1,940 | 106.3% | 96.5% |
| Republican | 1,952 | 1,886 | 1,939 | 100.7% | 96.6% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 27,707 | 12,513 | 40,220 | 68.9% | 31.1% | 68.9% | 31.1% | 175 | 13 |
| Republican | 27,638 | 11,642 | 39,280 | 70.4% | 29.6% | 70.3% | 29.7% | 245 | 10 |
| All | 55,345 | 24,155 | 79,500 | 69.6% | 30.4% | 69.6% | 30.4% | 420 | 23 |

Per-user keep rate (all finished): mean 69.6%, median 70.0%, SD 21.8%.

Per-user remove rate (all finished): mean 30.4%, median 30.0%, SD 21.8%.

420 people kept every scored post. 23 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 8,400 | 14.9% |
| Democrat | Middle | 19,997 | 27.2% |
| Democrat | High | 11,823 | 49.2% |
| Republican | Low | 11,477 | 16.6% |
| Republican | Middle | 19,597 | 28.8% |
| Republican | High | 8,206 | 50.0% |

Pooled Democrat remove is 31.1% vs Republican 29.6%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 8,400 | 20.9% |
| Democrat | Middle | 19,997 | 49.7% |
| Democrat | High | 11,823 | 29.4% |
| Republican | Low | 11,477 | 29.2% |
| Republican | Middle | 19,597 | 49.9% |
| Republican | High | 8,206 | 20.9% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 23,360 | 32.1% |
| Democrat | Right | 16,860 | 29.8% |
| Republican | Left | 23,140 | 30.6% |
| Republican | Right | 16,140 | 28.3% |

## Attention

Pass rate 77.2% (2,992 passed, 883 failed).

Remove share among people who passed: 29.0%. Among people who failed: 35.0%.

354 of 420 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.0%. Democrat passers 29.9%. Republican passers 28.0%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 18,866 |
| Catalog posts | 18,899 |
| Posts with 1 label | 1,145 |
| Posts with 2 labels | 1,755 |
| Posts with 3 or more | 15,966 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 10,765 | 10,463 | 102.9% |
| 2 | Left, middle toxicity | 22,495 | 22,001 | 102.2% |
| 3 | Left, high toxicity | 13,240 | 13,096 | 101.1% |
| 4 | Right, low toxicity | 9,112 | 8,796 | 103.6% |
| 5 | Right, middle toxicity | 17,099 | 16,594 | 103.0% |
| 6 | Right, high toxicity | 6,789 | 6,630 | 102.4% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.8 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
