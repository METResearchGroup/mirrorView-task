# Connecting participant explanations to participant behavior

We have participant reflection text and influence ratings from Phase 2, Part 2 of our study. We did some preliminary analysis of that data in [this experiment](../mine_free_response_for_features_2026_08_03/). But, we can test whether the explanations agree with what participants actually did.

The top 5 reasons that participants mentioned for removing posts were
(from the high-influence Likert group in
[`mine_free_response_for_features_2026_08_03`](../mine_free_response_for_features_2026_08_03/),
ranked by human-annotated participant count):

1. Threats and toxicity (vulgar, slanderous, or otherwise toxic/inflammatory language) — n=319
2. Violence / intent to harm (free-speech default with carve-outs for threats, harm, or violence) — n=118
3. Inflammatory, trolling, or disrespectful language/intent — n=12
4. Misinformation / unverifiable or false claims — n=10
5. Not conducive to healthy debate (low substance, nonsense, or poor argument quality) — n=10

For each reason, we collected the participants who had cited that reason for their moderation decisions, and we compared their moderation decisions against users who had not mentioned those reasons.

We compare specifically for the following:

- Do they remove more/fewer posts?
- Are they more consistent?

(We need something here to link a post to a reason - maybe something like "if the post would have been removed by that policy?". Unsure)

Key difficulty is: what makes two posts similar? The easiest approach is embedding similarity. But two posts can be similar in embedding distance and yet not have the topical similarities that we care about? We also didn't control for showing posts that had similarity. A simple v1 could just be embedding distance, while another could be assigning features to each post, somehow (BERTopic or LLM-generated) and then reviewing how consistent participants were when they saw two posts that had the same features. This approach could require us just labeling posts with features. We already have features for toxicity, intergroup, positive, PRIME, etc. and we can imagine using either just using those or also adding other labeled features as well (e.g., "is_{whatever other features we found}").
