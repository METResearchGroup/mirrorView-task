from pydantic import BaseModel

BINARY_SENTIMENT_PROMPT = """
You are a sentiment analysis expert. Your task is to determine whether the overall valence of the following social media post is positive.

Instructions:
- If the post expresses a favorable attitude, optimism, praise, or generally good feelings, classify as true.
- If the post expresses criticism, disapproval, pessimism, anger, or generally bad feelings, classify as false.
- Consider the overall tone, affect, and language of the post.
- If there is a mix of positive and negative language, use the dominant sentiment.
- Ignore sarcasm unless it is obvious.
- Do NOT classify as "neutral". Every post should be labeled as true (positive) or false (not positive).

Few-shot Examples:

Example 1:
Post: "I really enjoyed reading this, it made my day better!"
is_positive: true

Example 2:
Post: "This is awful. I can't believe people think this way."
is_positive: false

Example 3:
Post: "Beautifully written and very inspiring."
is_positive: true

Example 4:
Post: "This post is misleading and frustrating to read."
is_positive: false

Now, given the following post, reply strictly in this JSON format:

{{
  "is_positive": <true|false>
}}

Post:
\"\"\"{post}\"\"\"
"""

class SentimentClassification(BaseModel):
    is_positive: bool
