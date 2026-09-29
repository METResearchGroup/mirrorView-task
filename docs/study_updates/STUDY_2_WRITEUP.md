# Study 2 Writeup



## Feature generation

### BERTopic on the original posts

Here, we focus the BERTopic analysis on the original posts. The mirroring operation did change some of the topics from the original post. We try to keep the same stance and political intensity, but there are different topics that are triggers for left-leaning and right-leaning groups. We add a follow-up set of analyses later on reviewing how the mirroring approach changed the topics.

#### Which topics are more common in left leaning posts, and which in right leaning posts?

#### Which topics are more common at low, medium, and high toxicity?

...

#### Do some topics get removed more often?

![Keep Rate by Topic](static/study_2_writeup/keep_rate_topics.png)

2. Do we see certain topics have higher rates of keep/remove? And how does this vary, if at all, by if the post was left/right leaning and low/medium/high toxicity?
3. What topics tended to come up more for left-leaning posts? Right-leaning posts?
4. What topics tended to come up more often for low/medium/high toxicity?
5. For users who identified as left-leaning, which topics were they most likely to keep? To remove? And how about for right-leaning users?

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
