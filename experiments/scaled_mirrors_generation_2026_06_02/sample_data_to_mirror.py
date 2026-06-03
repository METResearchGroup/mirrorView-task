"""Samples data to mirror.

Algorithm:

- Total of 11,000 posts
- Grabs all the Twitter data.
- For the remainder, splits 50/50 between Bluesky and Reddit.
Samples without replacement for each until the desired amount is hit.

Generates a .csv file (sampled_posts_{timestamp}.csv):

- ID of the post: `{integration}_{post_id}`
- text
- toxicity_tier
- political_stance

Also prints to stdout the following:

- pd.value_counts by integration
- pd.value_counts by integration x toxicity tier
- pd.value_counts by integration x political_stance
- pd.value_counts by toxicity tier x political_stance
"""
pass
