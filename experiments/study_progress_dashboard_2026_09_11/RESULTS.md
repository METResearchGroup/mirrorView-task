# Study progress, September 2026 run

Snapshot 2026_09_11-12:34:17 UTC. Export 2026_09_11-12:32:20.

See `SETUP.md` for how to refresh. The HTML dashboard is `index.html`.

## Progress

| Metric | Value |
| ------ | ----: |
| Assigned (valid) | 1,129 |
| Finished | 1,074 |
| Saved files | 1,076 |
| Labels | 21,520 |
| Target feeds | 3,879 |
| Target labels | 77,580 |
| User progress | 27.7% |
| Label progress | 27.7% |
| Missing from export | 55 |
| Missing after 20-minute grace | 53 |
| Attrition after grace | 4.7% |

Prolific has finished 1,074 of 3,879 feeds (27.7%). Prolific has assigned a larger share of Democrat slots (34.0% assigned vs 24.2% Republican). The busiest assignment hour is 2026-09-10 18:00 UTC, and assignments in the three busiest hours are 79.5% of assigned people.

## Party

| Party | Assigned | Finished | Target feeds | Assigned / target | Finished / assigned |
| ----- | -------: | -------: | -----------: | ----------------: | ------------------: |
| Democrat | 659 | 631 | 1,940 | 34.0% | 95.8% |
| Republican | 470 | 443 | 1,939 | 24.2% | 94.3% |

## Keep and remove

| Party | Keep | Remove | Trials | Trial keep | Trial remove | User mean keep | User mean remove | Always keep | Always remove |
| ----- | ---: | -----: | -----: | ---------: | -----------: | -------------: | ---------------: | ----------: | ------------: |
| Democrat | 8,594 | 4,026 | 12,620 | 68.1% | 31.9% | 68.1% | 31.9% | 53 | 3 |
| Republican | 6,316 | 2,584 | 8,900 | 71.0% | 29.0% | 71.0% | 29.0% | 58 | 4 |
| All | 14,910 | 6,610 | 21,520 | 69.3% | 30.7% | 69.3% | 30.7% | 111 | 7 |

Per-user keep rate (all finished): mean 69.3%, median 70.0%, SD 21.8%.

Per-user remove rate (all finished): mean 30.7%, median 30.0%, SD 21.8%.

111 people kept every scored post. 7 people removed every scored post.

## Toxicity

| Party | Toxicity | Trials | Remove share |
| ----- | -------- | -----: | -----------: |
| Democrat | Low | 2,524 | 14.8% |
| Democrat | Middle | 6,310 | 28.0% |
| Democrat | High | 3,786 | 49.8% |
| Republican | Low | 2,670 | 16.9% |
| Republican | Middle | 4,450 | 27.9% |
| Republican | High | 1,780 | 50.2% |

Pooled Democrat remove is 31.9% vs Republican 29.0%. Within a toxicity band the rates sit close together. Democrat feeds have a larger high-toxicity share.

| Party | Toxicity | Trials | Share of party trials |
| ----- | -------- | -----: | --------------------: |
| Democrat | Low | 2,524 | 20.0% |
| Democrat | Middle | 6,310 | 50.0% |
| Democrat | High | 3,786 | 30.0% |
| Republican | Low | 2,670 | 30.0% |
| Republican | Middle | 4,450 | 50.0% |
| Republican | High | 1,780 | 20.0% |

## Stance

| Party | Original stance | Trials | Remove share |
| ----- | --------------- | -----: | -----------: |
| Democrat | Left | 6,310 | 32.4% |
| Democrat | Right | 6,310 | 31.4% |
| Republican | Left | 4,450 | 29.2% |
| Republican | Right | 4,450 | 28.9% |

## Attention

Pass rate 78.6% (844 passed, 230 failed).

Remove share among people who passed: 29.4%. Among people who failed: 35.5%.

95 of 111 always-keep finishers passed the attention check.

User-mean remove among people who passed: 29.4%. Democrat passers 30.5%. Republican passers 27.6%.

## Post coverage

| Metric | Value |
| ------ | ----: |
| Unique posts labeled | 17,468 |
| Catalog posts | 18,899 |
| Posts with 1 label | 13,656 |
| Posts with 2 labels | 3,573 |
| Posts with 3 or more | 239 |

| Cell | Mix | Labels now | Assignment slots | Progress |
| ---- | --- | ---------: | ---------------: | -------: |
| 1 | Left, low toxicity | 2,597 | 10,463 | 24.8% |
| 2 | Left, middle toxicity | 5,380 | 22,001 | 24.4% |
| 3 | Left, high toxicity | 2,783 | 13,096 | 21.2% |
| 4 | Right, low toxicity | 2,597 | 8,796 | 29.5% |
| 5 | Right, middle toxicity | 5,380 | 16,594 | 32.4% |
| 6 | Right, high toxicity | 2,783 | 6,630 | 42.0% |

Every current finisher is on a 10 left / 10 right feed. Left-only feeds start at original user 3203 and have not been handed out yet.

## Influence and time

Influence mean 4.6 on a 1 to 7 scale. Median session 10.7 minutes.

## Outputs

* `index.html`
* `public/study-progress.html`
* `outputs/dashboard_payload.json`
