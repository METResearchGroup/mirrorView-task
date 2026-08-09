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
