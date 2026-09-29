# Study 2 Writeup

## BERTopic on the original posts

We focus the BERTopic analysis on the original posts. The mirroring operation did change some of the topics from the original post. We try to keep the same stance and political intensity, but there are different topics that are triggers for left-leaning and right-leaning groups. We add a follow-up set of analyses later on reviewing how the mirroring approach changed the topics. We also use all keep/remove decisions per post, rather than taking a majority vote. For convention's sake, we measure the overall keep rate, rather than the remove rate.

We see more well-defined BERTopic results from the larger combined Study 2 dataset than we did in the first run given our larger dataset and the increased number of labels per post.

### Which topics most commonly appear?


| Topic                    | Posts | Keep rate |
| ------------------------ | ----- | --------- |
| Climate and fossil fuels | 1,122 | 81.8%     |
| Border and immigration   | 862   | 75.8%     |
| MAGA and institutions    | 851   | 59.1%     |
| Abortion access          | 690   | 75.2%     |
| Trump media and lying    | 636   | 59.3%     |
| Criticism of Democrats   | 598   | 69.3%     |
| Criticism of Republicans | 566   | 59.0%     |
| Biden and Trump blame    | 358   | 67.6%     |
| Billionaires and taxes   | 326   | 76.6%     |
| Abolish ICE              | 259   | 62.1%     |

### Which topics are more common in left leaning posts, and which in right leaning posts?

![Topics by Left/Right-Leaning](static/study_2_writeup/topics_by_left_right_leaning.png)

### Which topics are more common at low, medium, and high toxicity?

Low toxicity posts are more often about climate, abortion, and billionaires and taxes. Climate alone is 20.5% of low toxicity grouped posts and 1.6% of high toxicity grouped posts. High toxicity posts are more often attacks on Trump, MAGA and institutions, and criticism of Republicans. Criticism of Trump's media behavior is 13.9% of high toxicity grouped posts and 1.1% of low toxicity grouped posts. Anti Trump harassment is almost entirely in the high toxicity sample (140 of 144 posts).

| Topic                    | Low         | Medium     | High        |
| ------------------------ | ----------- | ---------- | ----------- |
| Climate and fossil fuels | 20.5% (604) | 8.5% (471) | 1.6% (47)   |
| Abortion access          | 8.2% (240)  | 7.0% (389) | 2.1% (61)   |
| Billionaires and taxes   | 4.8% (141)  | 2.1% (117) | 2.4% (68)   |
| Trump media and lying    | 1.1% (33)   | 3.6% (200) | 13.9% (403) |
| Anti Trump harassment    | 0% (0)      | 0.1% (4)   | 4.8% (140)  |
| MAGA and institutions    | 3.3% (98)   | 7.9% (439) | 10.9% (314) |
| Criticism of Republicans | 2.2% (66)   | 4.9% (272) | 7.9% (228)  |

### Do some topics get removed more often?

Among the 23 topics with at least 100 posts, the keep rate runs from 31.7% to 81.8%. The topics most commonly removed include anti-Trump harassment and anti-fascism messaging, while the topics most commonly kept include climate change and sanctuary cities.

![Keep Rate by Topic](static/study_2_writeup/keep_rate_topics.png)

### Which topics did Democratic/Republican raters keep, and which did they remove?

Democratic raters kept 69.4% of 52,864 votes. Republican raters kept 70.0% of 48,970 votes. The topics they were most likely to remove, and the topics they were most likely to keep, are almost the same list. Both groups removed anti Trump harassment most often, at about 32%. Both groups kept climate and fossil fuels most often among large topics, at about 82%.

Where the two groups differ, the gap is generally small. Across 26 topics with at least 200 votes from each group, the typical gap is under 2 points. The largest gaps are:

- Open carry laws: Democratic raters kept 75.8% of 289 votes, and Republican raters kept 68.3% of 249 votes.
- Supreme Court: Republican raters kept Supreme Court posts at 77.6% (308 votes), and Democratic raters kept them at 71.5% (330 votes).

#### Keep/remove behavior for Democrats

Here are the topics Democratic raters were most likely to remove, among topics with at least 200 of their votes.

| Topic                    | Keep rate | Votes |
| ------------------------ | --------- | ----- |
| Anti Trump harassment    | 31.5%     | 444   |
| MAGA and institutions    | 57.6%     | 2,308 |
| Criticism of Republicans | 59.1%     | 1,500 |
| Trump media and lying    | 59.4%     | 1,788 |
| Anti fascism messaging   | 59.7%     | 571   |

Here are the topics Democrat raters were most likely to keep:

| Topic                    | Keep rate | Votes |
| ------------------------ | --------- | ----- |
| Gun policy debate        | 82.4%     | 262   |
| Climate and fossil fuels | 82.2%     | 2,872 |
| Gun laws in schools      | 79.5%     | 410   |
| Sanctuary cities         | 78.6%     | 266   |
| Gun rights               | 77.6%     | 602   |

#### Keep/remove behavior for Republicans

Here are the topics Republican raters were most likely to remove, among topics with at least 200 of their votes.

| Topic                    | Keep rate | Votes |
| ------------------------ | --------- | ----- |
| Anti Trump harassment    | 31.9%     | 282   |
| Anti fascism messaging   | 57.7%     | 478   |
| Criticism of Republicans | 59.1%     | 1,377 |
| Trump media and lying    | 59.2%     | 1,473 |
| MAGA and institutions    | 60.8%     | 2,059 |

Here are the topics Republican raters were most likely to keep:

| Topic                    | Keep rate | Votes |
| ------------------------ | --------- | ----- |
| Climate and fossil fuels | 81.5%     | 2,893 |
| Sanctuary cities         | 80.6%     | 289   |
| Gun policy debate        | 80.2%     | 242   |
| Gun laws in schools      | 79.1%     | 369   |
| Mail and elections       | 78.2%     | 257   |

#### Does the stance of the post affect the keep/remove rate?

The stance of the post barely moves the overall keep rate. Left leaning posts are kept at 69.0% (11,386 posts). Right leaning posts are kept at 70.9% (8,377 posts). Inside a topic, the gap is usually a few points. There are a few topics that show a nontrivial gap (see below).

(TODO: Insert visualizations here, once I analyze the 2-d distribution)

#### Does the toxicity of the post affect the keep/remove rate?

Toxicity moves the keep rate much more than stance does. Low toxicity posts are kept at 84.7% (4,892 posts). Medium toxicity posts are kept at 72.6% (9,888 posts). High toxicity posts are kept at 49.8% (4,983 posts).

![Keep Rate by Toxicity](static/study_2_writeup/keep_rate_by_toxicity.png)

This trend is generally true across topics as well:

![Keep Rate by Toxicity and Topic](static/study_2_writeup/keep_rate_by_toxicity_topic.png)

### BERTopic on the original and the mirrored posts

...

### LLM-based feature generation

(Write about the procedure and how it works)

(Write results)

## Model training



### Zero-shot results



### Prompt-tuned results



### LLM fine-tuning results



## Training a calibrated classifier

One of the shortcomings of building a binary classifier is that it imposes a discrete label on an inherently uncertain task. In a non-trivial amount of tasks, people themselves were uncertain of what the label should have been. I propose two approaches for this:

1. An ensemble approach.
2. A calibrated classifier that returns a probability, and we can then set an arbitrary threshold. This would be inspired by how the Perspective API was built.



### Prompt-tuning a calibrated classifier

One of the shortcomings of building a binary classifier is that it imposes a discrete label on an inherently uncertain task. In a non-trivial amount of tasks, people themselves were uncertain of what the label should have been. There's not much clarity on this

Jev + DSPy + GEPA.

### Fine-tuning a calibrated classifier

Qwen.

### Calibrated classifier fine-tuning results

...