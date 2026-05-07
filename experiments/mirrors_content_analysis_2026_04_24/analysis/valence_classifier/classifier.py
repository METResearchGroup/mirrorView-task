from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

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



class ValenceClassification(BaseModel):
    is_positive: bool


_VALENCE_PROMPT = ChatPromptTemplate.from_messages(
    [("human", BINARY_SENTIMENT_PROMPT)]
)


def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, api_key=api_key)


def classify_post(post: str) -> ValenceClassification:
    """Classify one post via OpenAI structured output (LangChain)."""
    llm = get_llm()
    structured = llm.with_structured_output(ValenceClassification)
    chain = _VALENCE_PROMPT | structured
    return chain.invoke({"post": post})


def classify_posts(posts: list[str]) -> list[ValenceClassification]:
    """Classify each post with `classify_post`."""
    return [classify_post(p) for p in tqdm(posts, desc="Valence classification")]

if __name__ == "__main__":
    posts = [
        "I really enjoyed reading this, it made my day better!",
        "This is awful. I can't believe people think this way.",
        "Beautifully written and very inspiring.",
        "This post is misleading and frustrating to read.",
    ]
    classifications = classify_posts(posts)
    print(classifications)
