# What is MirrorView?

In the Mirrorview project, our goal is to use counterfactual mirrors to mitigate partisan bias in
online content moderation.

## Project overview

Political debate increasingly unfolds online, yet the rules for what political speech should
be moderated remains fiercely contested. Nearly three-quarters of U.S. adults, and 85% of
Republicans, say social-media companies censor political views, and barely one-quarter trust
platforms to enforce rules fairly (Pew Research Center, 2020). Audits show Reddit moderators
disproportionately remove ideologically dissonant posts, reinforcing echo chambers (Huang et
al., 2024). Well-intentioned efforts to “bridge divides” by showing users opposing tweets often
backfire, deepening affective polarization (Bail et al., 2018). Regulators on both sides of the
Atlantic now warn that opaque algorithmic filters threaten free expression and democratic
legitimacy (European Parliament, 2020). In short, content moderation still lacks a shared,
stance-neutral standard for justified disagreement. This has created a legitimacy vacuum at the
heart of content moderation and deliberative democracy in online spaces, leading to users
self-selecting into different platforms and engaging in toxic disagreement when they are on the
same platforms.

How can online platforms promote justified disagreement without reproducing partisan
bias? We introduce MirrorView, an AI tool that draws upon a Rawls-inspired “veil-of-ignorance”
framework to help humans judge political speech by its form rather than its ideological content.
MirrorView is a fine-tuned language model that transforms any political post into a stylistically
identical counterfactual twin that argues the opposite political position on the same topic. These
counterfactual twins are then used for a procedure that asks human raters to moderate under a
linked-fate rule: either both messages are acceptable or neither is. This forced symmetry
operationalises counterfactual perspective-taking, a process shown to foster intellectual humility
and reduce dogmatism (Leary et al., 2019). Pilot data will test whether the MirrorView
significantly reduces partisan-biased content moderation decisions.

The project delivers a hybrid human–AI pipeline with two unique pay-offs. First, it
cultivates intellectual humility in real time: raters are forced into counterfactual
perspective-taking, seeing how the strong statement they would endorse from their own
ideology would look if it were stated in equal terms from the opposite ideological stance.
Second, the symmetric decisions yield a training set whose labels are invariant to political
stance, enabling a machine-learning model to capture the “pure form” of legitimate
disagreement as voted on by a large number of human raters.

## Project phases

### Phase 1: Developing and Validating the MirrorView Counterfactual Model

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

This was done in a separate repo, and we have the best-performing model already (Claude Sonnet 4.6) that we use for generating flips.

### Phase 2: Implementing and Testing the Linked-Fate Moderation Procedure

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

We implement this in our app in this repo.

### Phase 3: Training a Feed-Ranking Algorithm for Justified Disagreement

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

Of note: there are several ways that Phase 3 could look, of which a feed-ranking algorithm is one way.

What we really care about is figuring out the "substance" of justified disagreement. This can take the form of:

- Doing content analysis.
- Training a model to learn and predict what keep/remove decisions would be made.
- Using the trained model and the content analysis as inputs to the feed-ranking algorithm.
