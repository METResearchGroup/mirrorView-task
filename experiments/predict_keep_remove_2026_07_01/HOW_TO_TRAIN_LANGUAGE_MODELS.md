# How to train the language models

This contains a compilation of some thoughts I have around training language models to predict the keep/remove decisions.

We've already trained logistic regression and XGBoost-based models, across a few ablations. Now I'd like to see how language models would fare.

Some variants I'm thinking of include:

- One-shot prompting:
  - With a small model
  - With a large model
- Few-shot prompting:
  - With a small model
  - With a large model
- ModernBERT
- LoRA fine-tuning

I'll also do the prompting ones across two sets of inputs:

- Just the original post
- Original post + mirrored post

We showed users both the original post and the mirrored post as part of the linked fate procedure, and we saw a significant difference in keep/remove decisions based on whether users were in the linked fate condition or if they only saw the original post. However, when we trained our predictive models, we saw that including only the original post was just as predictive as showing both the original and mirrored posts, suggesting that it was the mere presence of the mirrored post that affected whether users chose to keep or remove. We also observed that users in our training condition (where they saw the linked fate procedure for the first half of the study, and only the original posts in the second half of the study) also matched the performance of users in the linked-fate-only condition, censoring outgroup posts less and ingroup posts more as compared to users in the control condition (i.e., only saw the original posts). All of this suggests that the key driver is the mere presence or awareness of the linked fate procedure (i.e., seeing the mirrored posts).

For completeness, we can do some initial experiments that include both the original post and the original post plus the mirrored post. However, I expect those to have non-significant results due to our previous findings suggesting that the mere presence of the mirror, rather than anything about the substance of the mirrored post itself, drove performance. If we replicate that, then we'll continue on training the ModernBERT and LoRA-tuned models with just the original text.

## Experiment 1: Prompting

For the prompting experiments, we'll do them in models/llm_api/{one_shot/few_shot}/{original/original_plus_mirror}/{small/large}/

Each will have a prompt.py and a train.py, for consistency with the other approaches.

For the models, we'll use:

- small: gpt-5.4 nano
- large: gpt-5.5

We'll run these and report the results as a table here, with columns:

- type: one-shot/few-shot
- ablation: original, original plus mirror
- model size: small, large
- model name
- split: train/test
- accuracy, other metrics...

## Experiment 2: ModernBERT

We also want to use ModernBERT...

## Experiment 3: LoRA-tuned models

...
