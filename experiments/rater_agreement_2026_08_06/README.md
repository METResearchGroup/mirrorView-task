# Reviewing rater agreement

A post with a unanimous approval and a post with disagreement can receive the same label, even if there's something distinctly different between each.

We did some light analysis of this in [this experiment](../bertopic_modeling_2026_08_05/) and [this experiment](../create_llm_features_2026_08_05/), seeing if we could learn some decision boundary in the lower-dimensional space that would distinguish posts that users unanimously rated as keep/remove vs. posts that users disagreed.

We want to do a deeper dive here to compare high agreement posts with low agreement posts. Some things we want to examine include:

- Toxicity: does toxicity affect whether users tend to unanimously keep/remove a post?
- Topic
- Language features

We're looking to see if we, for example, can find a clear set of posts that most participants remove, and then identify traits that may be shared by those posts and not other posts. We also want to see if we can find patterns in posts where users disagreed as to whether they should be kept or removed.
