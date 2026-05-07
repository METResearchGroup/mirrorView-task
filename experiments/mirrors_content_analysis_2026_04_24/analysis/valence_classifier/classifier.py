from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from experiments.mirrors_content_analysis_2026_04_24.dataloader import Dataloader
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

VALENCE_CLASSIFIER_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = VALENCE_CLASSIFIER_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = VALENCE_CLASSIFIER_DIR / "labels_mirrors.csv"


def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, api_key=api_key)


def classify_post(post: str) -> ValenceClassification:
    """Classify one post via OpenAI structured output (LangChain)."""
    llm = get_llm()
    structured = llm.with_structured_output(ValenceClassification)
    chain = _VALENCE_PROMPT | structured
    return chain.invoke({"post": post})


def classify_texts(posts: list[str]) -> list[ValenceClassification]:
    """Classify each post with `classify_post`."""
    return [classify_post(p) for p in tqdm(posts, desc="Valence classification")]


def _all_mirrors_claude_path() -> Path:
    return Dataloader.PROJECT_ROOT / "img" / "all_mirrors_claude.csv"


def _build_posts_frame(raw: pd.DataFrame, text_column: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_primary_key": raw["post_primary_key"].astype(str),
            "text": raw[text_column].fillna("").astype(str),
        }
    )


def _label_posts_dataframe(posts: pd.DataFrame) -> pd.DataFrame:
    texts = posts["text"].tolist()
    classifications = classify_texts(texts)
    return pd.DataFrame(
        {
            "post_primary_key": posts["post_primary_key"].tolist(),
            "is_positive": [c.is_positive for c in classifications],
        }
    )


def classify_posts() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load Claude mirrors CSV, classify both text columns, and write label CSVs."""
    path = _all_mirrors_claude_path()
    raw = pd.read_csv(path)
    for col in ("post_primary_key", "original_text", "claude_mirror"):
        if col not in raw.columns:
            raise KeyError(f"Expected column {col!r} in {path}")

    original_posts = _build_posts_frame(raw, "original_text")
    mirrored_posts = _build_posts_frame(raw, "claude_mirror")

    labels_original = _label_posts_dataframe(original_posts)
    labels_mirrors = _label_posts_dataframe(mirrored_posts)

    labels_original.to_csv(LABELS_ORIGINAL_PATH, index=False)
    labels_mirrors.to_csv(LABELS_MIRRORS_PATH, index=False)
    return labels_original, labels_mirrors

if __name__ == "__main__":
    classify_posts()
