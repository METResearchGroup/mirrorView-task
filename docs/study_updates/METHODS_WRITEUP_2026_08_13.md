# 1. Where we left off

Study 1 established the Linked Fate Procedure (LFP). Every political post has a mirror — the same message, topic, and argumentative structure rewritten to the opposite political stance. Participants see the post and its mirror side by side and make one joint decision: Keep Both or Remove Both. Because the two sides share a single fate, they cannot be held to different standards.

Three results:

* The procedure mechanically works. Partisan bias in moderation (P(remove | outgroup) − P(remove | ingroup)) was 0.12 under standard individual moderation and fell to 0.01–0.02 under LFP.

* It helped remove political bias. LFP increased removal of one's own side's highly toxic content (56% vs. 47%) while reducing over-removal of the other side's moderately toxic content (38% vs. 31%). People became less partisan while staying calibrated to actual toxicity.

* Participants knew it was happening. Mean influence rating 4.85/7. Open-ended responses described a shift from "Do I agree with this?" to "Would I apply the same rule if the other side said it?"

So what? If partisan asymmetry has been stripped out of the decisions, then the language that separates "kept" from "removed" content is a bottom-up, empirical operationalization of "justified political disagreement."

Below, I summarize progress on recovering that language.

# 2. Data collection

We aimed for 10k messages labeled under LFP, and recruited a nationally representative sample for rate 20 each (each message will have 3 labels so we can then take a consensus vote on keep/remove). We needed 1500 P’s for this goal.

First round of data collection: 8,791[^a] moderation decisions from 1,178 participants who did LFP (20 unique posts each).

# 3. Feature extraction goals[^b]

We have thousands of keep/remove decisions but no theory telling us what people were responding to. We need to induce the decision criteria from the data rather than impose them. This is key so we don’t import a normative definition of acceptable speech.

So we ran two independent feature-discovery pipelines, then checked both against what participants actually said they were responding to under LFP (we have their actual behavior plus self-reports of features).

# 4. Route 1: BERTopic — what are these posts about?

BERTopic first gives each post a location on a kind of map of meaning, so that posts saying similar things sit near each other even when they share no words — "the border is out of control" lands right beside "we need to secure the southern boundary." That map is then flattened to two dimensions, an algorithm finds the crowded spots on it (leaving genuine oddballs unassigned rather than forcing them into a group), and finally an LLM reads a sample from each crowd and gives it a plain-English name.

We recovered 53 topics, filtered out artifacts plus duplicates and low-quality clusters, and retained roughly 20. They are what you'd expect from US political social media: criticism of MAGA (n=210), criticism of Republicans/GOP policy (n=200), deportation and illegal immigration debate (n=179), Biden-era immigration criticism (n=145), Trump corruption allegations (n=129), taxation and wealth extraction (n=112), reproductive rights (n=106), tariffs and affordability (n=87), ICE/DHS enforcement (n=74), trans rights (n=68), and so on.

## A null result!

When we colored the two-dimensional projection by whether annotators kept or removed each post, we saw no clear separation. When we colored it by whether annotators were unanimous or split, again no clear separation.

This is a useful finding: topic is a weak predictor of moderation outcomes. Abortion posts are not removed as a category; immigration posts are not removed as a category. Whatever people are responding appears to be more about how something is said, not what it is about.

Note: A two-dimensional projection is exploratory, i.e., absence of visible separation in a compressed view does not prove absence of separable structure in the full space.

# 5. Route 2: LLM-based feature extraction — how are these posts written?

Embeddings can only tell us that two posts are semantically similar. LLMs can be asked to attend to rhetoric, tone, syntax, and pragmatics rather than subject matter. We used a pipeline adapted from recent work at Google DeepMind:

1. Hand an LLM a batch of documents at once and ask it to generate candidate features.
2. Embed each generated feature (features are short text, so they can be placed in meaning space just like posts!)[^c].
3. Cluster the feature embeddings.
4. Show an LLM a sample from each cluster and ask for a human-readable label.

The batching in step 1 is important for LLMs: a model shown ten posts simultaneously has to articulate what they have in common which forces it toward abstraction (“second-person confrontation”) rather than paraphrase (“this post is angry about ICE”).

We sampled 500 removed and 500 kept posts and generated 100 prompts, each containing 10 posts that were homogeneous in outcome (all kept or all removed), asking the model why human annotators might have made that decision.

## Results

Features characteristic of KEPT posts were largely structural and argumentative:

* Mixed-length argumentative commentary[^d]
* Conditional if/then policy claims or predictions
* Declarative claims with quantified evidence
* High-density political proper-noun referencing
* Hashtag/mention-driven political framing
* Direct second-person imperative persuasion

Features characteristic of REMOVED posts were largely interpersonal and hostile:

* Profanity and sexual slur attacks
* Derisive ridicule and mockery toward targets
* Moralized, hostile political condemnation
* Partisan voters blamed via us-vs-them framing
* Victim/persecution framing with blame
* Conspiracy-style motive and cover-up framing
* Exclamatory imperative and insult punctuation
* Brevity with direct ideological insult

Other observations:

* The feature space for removed posts is better separated than for kept posts with our current data, i.e., there appear to be many distinguishable ways to be unacceptable and comparatively few ways to be acceptable. And the acceptable/unacceptable line falls almost exactly where the rhetoric turns from “claims about the world” to “attacks on people”. Both are consistent with LFP's design intent: once you cannot punish the other side for its position, what's left to punish is conduct.
* However, there is a meaningful chunk of the data the model just has trouble predicting, and that’s likely because people are not fully sure. This happens to be the grey area arena where for example things are emotional and moralized yet majority finds it acceptable. We need more data to get a better handle on this grey area, which I find to be the most interesting.

# 6. Route 3: what participants said they were doing

Both pipelines above are inferences about participants. We also asked participants directly, then applied the same machinery to their free-text reflections: an LLM extracted decision rules from each response, we embedded those rules, and clustered them with HDBSCAN. Because free text is heterogeneous, a large share fell out as noise; we report only the coherent themes.

First, we can split by self-reported influence of the LFP (1–7 Likert):

**Low influence (< 4, n = 255).** These participants claimed they didn’t really use the LFP to make their decisions. These participants were dominated by a single theme: harm/toxicity thresholds within free speech (n=130). Roughly: anything goes until it does damage. Smaller themes included explicitly ignoring the pair (n=24), discomfort about one's own moral standing to judge (n=7), and prioritizing profanity cues over politics (n=5).

**High influence (≥ 4, n = 922)** — These were the participants who said LFP influenced their decision (most people!)

* Remove for threats and toxicity (n=320)
* Apply the same standard to both sides (n=118)
* Free speech with violence/threat exceptions (n=59)
* Avoidance of inflammatory/trolling language (n=12)
* Factuality and misinformation control (n=10)[^e]
* Conduciveness to healthy debate (n=10)
* Pair-as-a-unit and pair-level argument-quality constraints (n=17 combined)
* Other, incl. constructiveness, partisan irritation, and explicit "no clear basis" (n=187)

Summary: A first pass analysis demonstrates that participants' reported features (e.g., harm, threat, profanity, partisan symmetry) generally line up with the rhetorical clusters the LLM independently mined from removed posts (i.e., their behavior). This analysis pipeline is looking like good convergent validity and will be validated further, as well as made more precise with data.

# 7. Using features to test classification performance

The whole point of the features is for our interest (descriptive account of free speech standards, etc) but also for prediction (can the model use the features to predict accurately what people will allow vs. remove). We set up an ablation procedure:

* Control arm: an LLM receives exactly the stimuli and instructions our human participants received.
* Prompt-tuned arm: identical, plus the mined keep/remove criteria from the BERTopic and LLM feature work.
* 1,000 posts, balanced (500 kept, 500 removed by humans). Model: Qwen 3.6, chosen so the pipeline is open-source and reproducible.
* Task: predict whether human annotators removed the post.

| Arm | Accuracy | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| Control | 0.660 | 0.693 | 0.574 | 0.628 |
| Prompt-tuned | 0.649 | 0.611 | 0.818 | 0.700 |

Adding the mined criteria raised recall by 42.5% relative (0.574 vs. 0.818) and F1 by 11% (0.628 vs. 0.700), at a real cost in precision (0.693 vs. 0.611) and no gain in raw accuracy.

High-level summary if you’re not familiar with NLP metrics: the features did teach the model what removal-worthy language looks like: it went from missing 43% of the removals to missing 18%. But it also became more willing to remove, and on this balanced set the 122 additional correct catches came alongside 133 additional false alarms.

# 8. Putting 0.70 F1 in context

An F1 of 0.70 is already impressive for this literature, and we have a lot we can do to improve this result already (mainly collecting more data so that we can get a better handle of these ambiguous cases in between obvious kees and obvious removes).

Brady et al. (2021), Science Advances: my Digital Outrage Classifier, a supervised neural net trained on 26,000 outrage-labeled tweets, reports F1 = 0.71 (75% accuracy). We are at 0.70 with no training at all, from prompt content alone.

Hoover et al. (2020), SPPS: the Moral Foundations Twitter Corpus (35,108 tweets, three trained annotators each). Performance swings by foundation and topic, from ~0.8 on the pooled corpus down to 0.14 on the hardest sub-corpus. Recent transformer models on individual foundations typically sit at 0.3–0.5 in-domain and fall further across domains.

# 9. What we take from this, and what's next

Substantive: the boundary of justified political disagreement, as our participants are drawing so far, runs along the shift from arguing about the world to attacking people. Things like profanity and slurs, mockery, us-vs-them blame attribution, conspiratorial motive attribution, second-person confrontation. Conditional reasoning, quantified claims, and even quite extreme positions are surviving.

Methodological: we now have a working pipeline for mining decision criteria from behavior, validating them against self-report, and testing them predictively and evidence that the criteria carry real signal.

Next:

1. Scale the corpus — Current features come from 1,000 posts we were trialing the new methods on. We can scale up to the data we already have, but ultimately Mark and I agree we should double our data collection to get 20k and see what extra precision that gets us, especially for ambiguous category of posts.
2. Establish the ceiling — human-human agreement on the classification set, so 0.70 can be read against what's achievable rather than against 1.0.
3. Move from prompting to fitting — weight and threshold the criteria rather than handing over a simple list of features in order to recover the lost precision.
4. Test generalization — do criteria mined from these topics hold on unseen political topics?

---

[^a]: We aimed for 10k labels and 1500 participants but due to the representative sample demands + missing data currently have this many

[^b]: For everything that follows, I tried to summarize it in digestible terms, but there is a ton of engineering under the hood that Mark has been optimizing!

[^c]: This is an interesting insight from this method from DeepMind that Mark discovered

[^d]: These are LLM-generated, we can do some better labeling as we continue

[^e]: need to look into this one more due to the question/concern that keeps coming up
