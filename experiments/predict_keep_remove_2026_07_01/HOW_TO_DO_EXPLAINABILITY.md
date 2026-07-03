# How to do explainability

This document will summarize my thoughts and approach towards explainability for the MirrorView project.

Here are some AI chat conversations that I referenced while writing this (though I wrote all of this document myself, manually asking questions and picking and choosing one-off ideas from the AI agents):

- [Claude](https://claude.ai/chat/2415d2ef-6e84-46bf-8e97-24d91fbc4aa0)
- [ChatGPT](https://chatgpt.com/c/6a46b85d-dba8-83ea-814f-fb0275d840e3)
- [Gemini](https://gemini.google.com/app/edc8f31bfd8fc48d)

## Motivation

Currently, content moderation on social media platforms is done through a combination of human labelers and machine learning models. Even though platforms may have a set of policies that they claim to enforce, the requirements for what is allowable on a platform are enforced top-down at the behest of the individual annotators and reviewers.

In this project, we're investigating a bottom-up approach for this problem. We show a series of potentially contentious or politically charged social media posts, the same sort of posts that would possibly get flagged for moderation. We then ask human readers to view individual posts coupled with their ideological mirrors (posts that are the same in tone and substance to the original post, whose political stances are flipped). By removing knowledge of which version of the post would be permitted on the platform or not, we hope to disentangle political beliefs and bias from the substance of what content a user would permit to be on a platform. We hope that this allows us to overcome the traditional shortcoming of content moderation, where the decisions for moderation are in part skewed by the political leaning of both the human evaluators and also from the platforms themselves.

### Predicting human moderation choices

Given the dataset of human-annotated moderation choices, we believe we can develop a model that predicts which posts people choose to remove from a social media platform, when shown that post and its politically flipped mirrored equivalent, better than random chance. We already have some initial evidence supporting this belief. We can predict with a non-trivial accuracy whether or not a rater chooses to keep or remove a post from the platform.

### Why we need explainability

However, we also would like to know the content-level features that predict which posts get removed. This will allow us to learn more about the nature of contentious and possibly disagreeable content on social media that users, on average, would allow to exist on the platform.

For our analysis, we want to focus on the average ratings for a given post and its mirrored pair. What's out of scope of our analysis is a deeper dive on consistency of individual raters. We also care more about global features rather than features for a specific post.

By uncovering explainable signals, we can turn this into a series of policies that a platform can follow. We then will have an explainable and transparent set of rules justifying why a certain piece of content online was allowed or removed.

## Initial hypotheses to investigate

Embeddings:

- Does the text embedding of the original post alone explain the decision to keep or remove? How does that compare to considering the text embedding of both the original and the mirrored post?
- Does the element-wise difference of the text embeddings between the original and mirrored posts explain the decision? This would tell us if the closeness of a post and its mirror has any explainable signal for the decision. It also allows us to see if our mirroring algorithm generated robust results.

Considering specific hand-crafted features:

- Can we design hand-curated features that can explain some of the predicted performance?
- Are there syntactic or semantic signals that the models are learning during training? How do these differ from our hand-crafted features?
- Can we do systematic ablations when training a model on a set of explainable features in order to know which ones have the highest importance or explainability?
- Can we use the text embeddings to train models to predict each of these hand-crafted features? If a simple linear model which takes the text embeddings as input could predict these individual features, that lends some credence to the possibility that the model may be indirectly relying on these features during its evaluations. Namely, if a simple binary linear classifier could, given these embeddings, easily linearly separate a binary class label, we could use that as part of explaining the model's performance.

Explaining a fine-tuned LLM:

- Does a fine-tuned LLM outperform a simpler model like logistic regression or a tree-based model?
- Can we use probing vectors and attention heat maps, as well as other techniques used in explainable AI research, to probe the LLM's weights?
- Can we ask the model to also explain why it chose the decisions it did?

## Explainability for embeddings

Some ideas for explainability:

- nearest-neighbor examples
- clustering
- concept probes
- TCAV-style concept directions
- linear probes for human-readable constructs
- example-based explanations

(We should also analyze this for the subset of posts where the original user's political stance disagreed with the political stance of the original post. For that subset of posts, what is predictive of allowable disagreement?)
