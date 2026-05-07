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

INTERGROUP_EXAMPLES = """
## Examples

Post: "Customers are upset because the management changed the return policy."
Answer: 1

Post: "She was frustrated after missing her bus."
Answer: 0

Post: "People in City A say City B always cheats during football tournaments."
Answer: 1

Post: "Members of my hiking club disagreed on where to set up camp."
Answer: 0

Post: "Why do older employees ignore what the younger staff suggest?"
Answer: 1

Post: "A new bakery opened across from the old one."
Answer: 0

Post: "Several men argued loudly outside the bar."
Answer: 0
"""

INTERGROUP_SYSTEM_PROMPT = f"""
You are a helpful assistant. Your job is to analyze a single social media post and answer a binary classification question

## Task

Decide whether the post involves intergroup discussion. In social psychology, intergroup refers to interactions or situations that involve two or more groups that define themselves—or are defined by others—as distinct based on characteristics such as identity, beliefs, status, affiliation, or other boundaries.

- If you judge that the post describes, reports, or implies intergroup discussion, respond with: "1"
- If the post is unrelated, speaks only about individuals, is ambiguous, or describes within-group matters, respond with: "0"

Only output your label. ONLY output 0 or 1.

{INTERGROUP_EXAMPLES}
"""

INTERGROUP_PROMPT = f"""

{INTERGROUP_SYSTEM_PROMPT}

Post: {{prompt_input}}
Answer:
"""


class IntergroupClassification(BaseModel):
    is_intergroup: bool


_INTERGROUP_PROMPT = ChatPromptTemplate.from_messages(
    [("human", INTERGROUP_PROMPT)]
)

INTERGROUP_CLASSIFIER_DIR = Path(__file__).resolve().parent
LABELS_ORIGINAL_PATH = INTERGROUP_CLASSIFIER_DIR / "labels_original_text.csv"
LABELS_MIRRORS_PATH = INTERGROUP_CLASSIFIER_DIR / "labels_mirrors.csv"


def get_llm(model: str = DEFAULT_LLM_MODEL) -> ChatOpenAI:
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    return ChatOpenAI(model=model, api_key=api_key)


def classify_post(post: str) -> IntergroupClassification:
    """Classify one post via OpenAI structured output (LangChain)."""
    llm = get_llm()
    structured = llm.with_structured_output(IntergroupClassification)
    chain = _INTERGROUP_PROMPT | structured
    return chain.invoke({"prompt_input": post})


def classify_texts(posts: list[str]) -> list[IntergroupClassification]:
    """Classify each post with `classify_post`."""
    return [classify_post(p) for p in tqdm(posts, desc="Intergroup classification")]


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
            "is_intergroup": [c.is_intergroup for c in classifications],
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
