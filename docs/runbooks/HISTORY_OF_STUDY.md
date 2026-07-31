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

### Asking users to write their own mirrors

We built a web app to ask users to write their own mirrors.

[This link](https://docs.google.com/document/d/1ldWCF3PkoAEz1FaXHJtP96xpSgxageDrVMEnXjJjKRY/edit?tab=t.0) contains design assets and specs used for the Phase 1 web app.

The final dataset of posts we used is [in this link](https://drive.google.com/drive/u/0/folders/1g9LhSh_1in7IlFJUmXGGWg6_GP-5sWRh).

We tracked the mirrors that users wrote as well as their justifications:

- [This link](https://docs.google.com/spreadsheets/d/123cNumEcgo1gz6E_9xs3iDZjvbXdZQTz/edit?gid=731205239#gid=731205239) is for the pilot.
- [This link](https://docs.google.com/spreadsheets/d/1OohPoZB8oI_GRlJuRQev-yUKBP-0zALU/edit?gid=1276757676#gid=1276757676) contains the writings for the actual data collection round.

Next, we took the human-generated mirrors and passed them into an LLM to evaluate against our criteria. That data is in [this link](https://docs.google.com/spreadsheets/d/1qmN4jFOXwwZ7gHihdaRqYhKZyXV6hMnd-B71_mkje58/edit?gid=0#gid=0). [This link](https://docs.google.com/spreadsheets/d/1kCuv9KfphnWq9L-eOMhBxdE1QLQmXb2FeUMPw0ZchME/edit?gid=484999625#gid=484999625) contains the same rows, filtered for just the human-generated flips marked by the LLM as valid and passing all the filters.

### Asking an LLM to generate the flips and look at what features they used

We also asked an LLM to generate flips for a given set of posts. We then asked the LLM what factors it considered when doing so. That work is in [this dataset](https://docs.google.com/spreadsheets/d/1WU77_rpEozPxH7CrQPapGDLM-NYAaS0139pEwx0q4OM/edit?gid=1886738121#gid=1886738121).

## Study Phase 2: Implementing and Testing the Linked-Fate Moderation Procedure

### Study Phase 2, Part 1: Trialing the linked-fate procedure

The first phase of our study confirms that the linked-fate procedure works.

Our proposed plan was defined in [this Google Doc](https://docs.google.com/document/d/1A9kAlsCKgjk2qOlcJf_mriC7V9dbhn8VTT3Qb7HgDLc/edit?tab=t.0). This Google Doc discusses the stimuli randomization procedure as well as the design assets used in the UI.

The breakdown per condition was something like:

| Condition           | Phase 1 (10 posts)        | Phase 2 (10 posts)                      |
|---------------------|--------------------------|-----------------------------------------|
| control             | Single evaluations       | Single evaluations                      |
| Training + assisted | Linked fate procedure    | Mirrored messages, but single evaluation|

But then we eventually swapped to add a third condition. Therefore, our final dataset has data with the following 3 conditions:

| Condition | Training Phase (10 posts)       | Target Phase (10 posts)                       |
|-----------|---------------------------------|-----------------------------------------------|
| Control   | Individual evaluations (no mirror) | Individual evaluations (no mirror)            |
| Training  | Linked fate procedure (mirror shown) | Individual evaluations (no mirror)            |
| Assisted  | Linked fate procedure (mirror shown) | Individual evaluations (mirror shown)         |

The data for this phase is in [this folder](shared/data/raw/study_phase_2_part_1).

#### Phase 2, Part 1 Findings

Here, we confirmed that our linked fate procedure does work. We wrote up Study Phase 2, Part 1's results in [this Google doc](https://docs.google.com/document/d/1owljHygH0KqP4PtNf_fsUg3Cm1pBOEZ1mcaX-4vCfbY/edit?tab=t.0#heading=h.eg1xlekxf7vb). It says "Study 1" but "Study 1" refers to our linked-fate procedure, which was Phase 2 in our intended plan.

##### LLM-generated summary of the writeup

The study shows that the Linked Fate Procedure (LFP) with mirrored posts can almost eliminate partisan bias in content moderation while preserving democratic, bottom‑up judgments, and that participants experience it as making them fairer, more speech‑protective, and more focused on harm and civility rather than political alignment.

Core quantitative results: Under standard individual moderation, participants showed clear partisan bias (bias score ≈ 0.12), whereas LFP reduced this to about 0.02–0.01, effectively erasing bias as a manipulation check.

LFP changes how decisions track toxicity: it increases removal of one’s own side’s highly toxic posts (56% vs. 47% in control), while decreasing over‑removal of the other side’s moderately toxic posts (31% vs. 38% in control).

In other words, decisions become more even‑handed and more calibrated to toxicity rather than political group.

Mechanism: counterfactual mirroring
Every post is paired with a “mirror” that expresses the same message and structure from the opposite political stance; LFP forces a joint “Keep Both or Remove Both” decision, so participants cannot apply different standards to ingroup vs. outgroup.

This setup makes the relevant counterfactual explicit: people must ask, “Would I make the same decision if the opposing side said this?” shifting moderation from partisan agreement to rule‑based consistency.

Reported subjective impact: Participants reported that LFP meaningfully influenced how they moderated, with an average self‑reported influence of 4.85/7 and median 5.

Open‑ended responses (summarized via an LLM over ≈1200 LFP participants) indicate that LFP made partisan double standards more salient and encouraged participants to adopt general principles rather than react to agreement/disagreement.

Emergent decision principles" From the open‑ended data, several themes emerge about what standards people actually use under LFP:

- Fairness and consistency: About 20% explicitly mentioned fairness, neutrality, or applying the same standard to both sides, indicating that participants consciously aimed for symmetric treatment.
- Speech over position: Roughly 33% referenced free speech, open debate, and allowing political expression, emphasizing that disagreement and strong opinions should generally be allowed if expressed civilly.
- Red lines around harm and hate: Around 23% focused on threats, violence, hate, racism, safety, and similar criteria as reasons to remove content.
- Tone and civility: About 29% highlighted profanity, insults, aggression, personal attacks, and inflammatory language as core factors.
- Productive discussion: Approximately 15% mentioned constructiveness, logic, evidence, or contribution to the conversation as important to their decisions.
- A smaller group (≈8%) explicitly said the mirror comparison changed their perspective or made them more aware of their own potential bias, likely underestimating the total effect because many described the same mechanism indirectly via fairness language.

Conceptual contribution: The procedure operationalizes a notion of “justified political disagreement”: the set of posts that survive even‑handed scrutiny when people must apply the same rule to both sides.

Crucially, this boundary is learned bottom‑up from participants’ own choices under LFP, not from top‑down platform rules, preserving democratic legitimacy while stripping out partisan asymmetry.

Why simple averaging does not suffice: A naive alternative—training a model on average decisions from a balanced partisan sample without LFP—would yield noisy, contradictory labels, especially on contested content where each side makes opposite decisions.

The resulting “midpoint” label encodes a judgment no actual moderator holds, whereas LFP produces coherent, principled labels that reflect real, consistent decisions under a shared standard.

Planned next steps: Scale up: collect ≈10,000 mirrored post pairs with ~3 LFP judgments each from a nationally representative sample to build a large corpus of debiased keep/remove decisions.

Model the language boundary: use a generative model to surface linguistic features that distinguish kept vs. removed content under LFP, treating this as a data‑driven boundary for “justified political disagreement.”

Behavioral validation: deploy a model trained on these decisions in a political discussion forum and compare outcomes (comfort, enjoyment, heterogeneity of views, propensity for dissent, etc.) against a chronological baseline.

### Study Phase 2, Part 2: Scaling up the linked-fate procedure

Now that we've proven that the linked-fate procedure (LFP) works, we want to gather more data samples.

We scaled up our approach and collected 10,000 more posts, across Twitter, Reddit, and Bluesky.

The data collection logic is in [this repo](https://github.com/METResearchGroup/lab_data_integrations_interface/tree/main/data_platform) (future work plans to move that code into this repo for consistency). The logic to assign users to experimental conditions (here, just 1) is in [this repo](https://github.com/METResearchGroup/study_participant_assignment_interface) (again, should be moved here for consistency).

We then update the web app, in `webapp/`, to reflect the new study design. Also, unlike the previous study version, we only have 1 phase, rather than 2, and we ask users to classify 20 posts in that 1 phase. We do this just to scale up the number of labels per post using the LFP (since Phase 2, Part 1 confirmed that the LFP procedure does work).

The data for this phase is in [this folder](shared/data/raw/study_phase_2_part_2). The flips shown to users are in [this path](shared/data/raw/study_phase_2_part_2/flips.csv) and the subsequent user data is in [this path](shared/data/raw/study_phase_2_part_2/mirrorview_data_jspsych-mirror-view-4_2026_06_23-12:27:41.csv)

## Latest work

(2026-07-31) Our latest work is now trying to find trends in what people choose to remove.

