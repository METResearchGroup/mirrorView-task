# Reddit data dump

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

In `experiments/fetch_reddit_pushshift_dump_2026_06_15`, we grabbed some files from the Reddit PushShift dataset.

We'll now use that dataset again as part of our data collection.

Unlike in that previous experiment (where we specifically curated high-toxicity posts), here we'll keep most comments and downstream callers will manage filtering and cleanup.

Our datasets, `RC_2025-05.zst` and `RC_2025-06.zst`, contain Reddit comments across 6 political subreddits. This dataset is specifically for comments, not posts. Generally, for our project we care mostly about the comments anyways, as posts tend to be less interesting to analyze (the "action" on Reddit happens in the comments section).

Here is what one example comment looks like:

```json
{
  "id": "mvbyos2",
  "author": "momamil",
  "link_id": "t3_1l09l1b",
  "parent_id": "t3_1l09l1b",
  "subreddit": "politics",
  "body": "I want to throw tacos on the lawn of the nimrod who’s had the giant Trump No More Bullshit sign on his lawn for the last 10 years.",
  "score": 1,
  "created_utc": 1748736018,
  "permalink": "/r/politics/comments/1l09l1b/trumps_hated_taco_nickname_is_catching_on/mvbyos2/"
}
```

We have two types of comments:

1. Top-level comments: a direct reply to a post. The aforementioned example is a top-level comment (the `link_id` and `parent_id` are the same).
2. Nested comments: a comment of a comment.

Here is an example of a nested comment:

```json
{
  "id": "mvbyn04",
  "author": "Impossible-Scene-416",
  "link_id": "t3_1l09l1b",
  "parent_id": "t1_mvbyhla",
  "subreddit": "politics",
  "body": "lol yes but tacos always fold",
  "score": 7,
  "created_utc": 1748736000,
  "permalink": "/r/politics/comments/1l09l1b/trumps_hated_taco_nickname_is_catching_on/mvbyn04/"
}
```

For our use case, we only care about `id` and `body`.

We also filter out posts that have been deleted or removed. For these, we look for either `post["author"] == "[deleted]"` or `post["body"] == "[deleted]"`. Here's an example:

```json
{
  "id": "mvbynz6",
  "author": "[deleted]",
  "link_id": "t3_1l07f6o",
  "parent_id": "t3_1l07f6o",
  "subreddit": "Conservative",
  "body": "[removed]",
  "score": 1,
  "created_utc": 1748736010,
  "permalink": "/r/Conservative/comments/1l07f6o/be_warned_rosie_odonnell_vows_to_return_to_the_us/mvbynz6/"
}
```

What we do here is:

1. Process each of the two `.zst` files separately.
2. Filter out comments that have been deleted or removed.
3. Represent each comment using the same Pydantic model that we use for other Reddit data.
4. Sample a random sample of 500,000 posts from each file.
5. Store as `.parquet` files (`filtered/RC_2025-{05/06}.parquet`).
