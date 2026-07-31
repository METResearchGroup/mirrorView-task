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

In the first phase of our study, we needed to develop and validate our flip model.

To do so, we needed:

1. A set of social media posts across a variety of providers that met our filtering requirements.
2. A choice of model that would be best at performing this mirroring task.

We manually annotated the results from a few models in [this spreadsheet](https://docs.google.com/spreadsheets/d/1gRjv38teDIjCtxkngJ3w80wYHHj8R-FaEKtTcSLcnxg/edit?gid=0#gid=0). In this spreadsheet, we tested a few AI models and reviewed the quality of the mirrored posts.

https://docs.google.com/document/d/1r_cEw5ieirkkTOE5hcOt2O64Jjt7tzkziao2jwOk6gw/edit?tab=t.0

In this Google Doc, we define the list of filters that we used to curate the posts that we selected for our pipeline.

### Filter criteria

In [this Google Doc](https://docs.google.com/document/d/1r_cEw5ieirkkTOE5hcOt2O64Jjt7tzkziao2jwOk6gw/edit?tab=t.0
), we define the list of filters that we used to curate the posts that we selected for our pipeline.

1. **Language**: Primarily written in English.
2. **Length**: Between 100–300 characters (after removing URLs, phone numbers, and extra whitespace).
3. **Political Relevance**: Tweet must clearly reference U.S. political issues, figures, laws, elections, or institutions. Exclude vague content, promotional content, politics in other countries.
4. **Opinion-based**: Must contain personal opinion, stance, or discussion, not just event reporting, headlines, news, list of facts, product promotion, or advertisements.
5. **Topical Focus**: The main issue discussed in the post must be about climate change. If climate change is mentioned but just as a marginal part or just as an example, or if climate change is not discussed at all, write no.
6. **Self-Contained**: Must be understandable on its own text content—no need for thread context, external links, or its media (e.g., image or video). The post must not contain unknown references that cannot be inferred through its own text content, such as "this project", "the 22-year-old suspect", "that dataset", "special acquisition" but no explicit reference.
7. **Complete**: Must be complete on its own text content—no abrupt stop, no obviously unfinished sentence, not being truncated, not a subset of multiple posts (e.g., [1/5] usually means this tweet is one from five tweets in total, due to word limitation of tweet).

[This link](https://docs.google.com/spreadsheets/d/1YBz95GKp5Hu9rt79OdzDca2XXopbYa1XNrAqvFwn_0Q/edit?gid=0#gid=0) contains an example manual annotation of cleaned posts against the criteria listed here.

The team went back-and-forth on what "self-contained" means and how to prompt it, so [this link](https://docs.google.com/spreadsheets/d/1t_eaJtHKqzZxzM4-uqEalmbRc3hsEHTvdp6VeLuPk0U/edit?gid=0#gid=0) contains a spreadsheet where we manually reviewed what "self-contained" means, in order to give us a better idea of our intended approach.

We've got a few more spreadsheets where we ask GPT to review posts against these criteria and then we manually reviewed the annotations.

- [Link 1](https://docs.google.com/spreadsheets/d/1GpUXqWJau8nOgVuPW9vcG8vzSxf75yfCnFT7-0dvSzo/edit?gid=0#gid=0)
- [Link 2](https://docs.google.com/spreadsheets/d/1TErD_4LCfI5HXX0WQMNP_Mb9aWsEdmsZjveqzNhj6Is/edit?gid=94957341#gid=94957341)

### Stratifying by toxicity

We also wanted to include facets on toxicity. We wanted to report how moderation decisions varied based on the perceived toxicity of the post. We created a three-tier toxicity classification scheme. We used the Google Prospective API to classify the probability of toxicity. We then reviewed those and created thresholds for toxicity.

[This link](https://docs.google.com/spreadsheets/d/1l9fZ0i7Gq0GFqj7SWbEnPTxpViRcjBpn0SxMEPRhoGY/edit?gid=1703000983#gid=1703000983) contains a sample of tweets classified by both the filter criteria as well as stratified by toxicity.

### Creating the Phase 1 study

...

[This link](https://docs.google.com/document/d/1ldWCF3PkoAEz1FaXHJtP96xpSgxageDrVMEnXjJjKRY/edit?tab=t.0) contains design assets and specs used for the Phase 1 web app.

## Study Phase 2: Implementing and Testing the Linked-Fate Moderation Procedure

### Study Part 2, Phase 1: ...

### Study Part 2, Phase 2: ...

In this phase, we ...
