# How to do explainability

This document will summarize my thoughts and approach towards explainability for the MirrorView project.

## Motivation

Currently, content moderation on social media platforms is done through a combination of human labelers and machine learning models. Even though platforms may have a set of policies that they claim to enforce, the requirements for what is allowable on a platform are enforced top-down at the behest of the individual annotators and reviewers.

In this project, we're investigating a bottom-up approach for this problem. We show a series of potentially contentious or politically charged social media posts, the same sort of posts that would possibly get flagged for moderation. We then ask human readers to view individual posts coupled with their ideological mirrors (posts that are the same in tone and substance to the original post, whose political stances are flipped). By removing knowledge of which version of the post would be permitted on the platform or not, we hope to disentangle political beliefs and bias from the substance of what content a user would permit to be on a platform. We hope that this allows us to overcome the traditional shortcoming of content moderation, where the decisions for moderation are in part skewed by the political leaning of both the human evaluators and also from the platforms themselves.

### Predicting human moderation choices

Given the dataset of human-annotated moderation choices, we believe we can develop a model that predicts which posts people choose to remove from a social media platform, when shown that post and its politically flipped mirrored equivalent, better than random chance. We already have some initial evidence supporting this belief. We can predict with a non-trivial accuracy whether or not a rater chooses to keep or remove a post from the platform.

### Why we need explainability

However, we also would like to know the content-level features that predict which posts get removed. This will allow us to learn more about the nature of contentious and possibly disagreeable content on social media that users, on average, would allow to exist on the platform.

For our analysis, we want to focus on the average ratings for a given post and its mirrored pair. What's out of scope of our analysis is a deeper dive on consistency of individual raters.

By uncovering explainable signals, we can turn this into a series of policies that a platform can follow. It also gives us an explainable and transparent set of rules justifying why a certain piece of content online was allowed or removed.

## Explainability for embeddings

Some ideas for explainability:

- nearest-neighbor examples
- clustering
- concept probes
- TCAV-style concept directions
- linear probes for human-readable constructs
- example-based explanations

(We should also analyze this for the subset of posts where the original user's political stance disagreed with the political stance of the original post. For that subset of posts, what is predictive of allowable disagreement?)
