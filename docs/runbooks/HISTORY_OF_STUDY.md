# History of the study

A lot of the old data is kept in [this Google Drive folder](https://drive.google.com/drive/u/0/folders/14WhlBGT1b_nylMbCipm-BN0j1fNW39EG).

## Planning

Important docs here:

- https://docs.google.com/document/d/1yRC4Cw9lo4ijcbkwMQxc3p4GVGVmYv_3mbFx_rUY-ZQ/edit?tab=t.0
- 

## Intented plan

We had intended for the study to have 3 phases. By and large, we've stuck close to it, changing a few details here and there.

### (Planned) Phase 1: Developing and Validating the MirrorView Counterfactual Model

1. Corpus construction. We scraped 1000 short-form political messages (balanced by
ideology and toxicity) from Reddit, Bluesky, and X/Twitter.

2. Prompt engineering and model benchmarking. Multiple LLM back-ends (GPT-4o,
Llama-3-70B, Mixtral-8x22B) will be tasked with producing a stylistically matched
message that takes the opposite stance of each source post. Crowd-sourced annotators
(n = 1000) will rate success of generated mirror texts; we will iteratively refine prompts
and temperature settings.

3. Model selection and pipeline build-out. The best-performing model (>90 % stance flip
accuracy, >0.75 style-similarity) will be wrapped in a scalable inference service that
outputs pairs (post, counterfactual twin) for downstream experiments.

### (Planned) Phase 2: Implementing and Testing the Linked-Fate Moderation Procedure

1. Experimental design. Participants (N = 2,000) will view tweet-pairs consisting of an
original message and its MirrorView twin; order is randomized and their provenance is
concealed.
2. Linked-fate rule. In the treatment arm, participants decide whether both posts should
remain in a political-discussion feed or neither (forced symmetry). The control arm rates
identical messages individually, mirroring standard moderation practice.
3. Bias assessment. We compare the ideological composition of “allowed” vs. “removed”
content across arms. Success criterion: the linked-fate condition yields a significantly
lower partisan skew in removals.
4. Behavioral follow-up. After moderating, participants compose a response to a
disagreeable post, allowing us to test whether the procedure reduces hostile reply tone.

### (Planned) Phase 3: Training a Feed-Ranking Algorithm for Justified Disagreement

1. Label generation. Decisions from Phase 2 provide stance-invariant legitimacy labels;
these train a gradient-boosted text classifier that predicts “justified disagreement” from
linguistic features.
2. Ranking rule. A prototype feed ranks new posts up or down based on the classifier’s
score, favouring content likely to foster justified disagreement.
3. Online-lab experiment. Communities are randomly assigned to the new ranking or to a
chronological (or engagement-based) feed. Conversation health is assessed via toxicity
growth, reply diversity, and user retention.
4. Simulation extension. Parallel LLM 10,000-agent simulations with different user profiles
(trained on our Bluesky data) will stress-test the ranking rule at scale to simulate live field
deployment.

## Study Phase 1: Developing and Validating the MirrorView Counterfactual Model


...

## Study Phase 2: Implementing and Testing the Linked-Fate Moderation Procedure

### Study Part 2, Phase 1: ...

### Study Part 2, Phase 2: ...

In this phase, we ...
