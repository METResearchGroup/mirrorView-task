#!/usr/bin/env python3
"""
Merge human and LLM mirror data into a single CSV.

Selects the BEST human mirror per post based on criteria priority:
1. Priority 1: Passes all 6 criteria (LLM_labels_valid_check = TRUE)
2. Priority 2: Passes 5 criteria (relax Self-contained)
3. Priority 3: Passes 4 criteria (relax Self-contained + Stance)
4. Priority 4: For remaining posts, select mirror with MOST criteria passing

If multiple mirrors pass the same priority level, one is randomly selected.

Output columns:
- post_primary_key: unique identifier for the original post
- post_number: easier to reference (1-3 digit number)
- human_mirror_id: unique identifier for the selected human mirror row
- original_text: the original post text
- human_mirror: the human-written mirror (one per post)
- selection_tier: which priority tier the mirror was selected from
- llama_mirror: mirror from openrouter-llama-3.3-70b
- qwen_mirror: mirror from openrouter-qwen3-32b
- claude_mirror: mirror from claude-4.5-haiku
- gpt4o_mirror: mirror from gpt-4o-mini
"""

import pandas as pd
import re
import random

# Paths
LLM_CSV = "public/img/llm_mirrors.csv"
HUMAN_CSV = "public/img/human_mirrors_original.csv"
OUTPUT_CSV = "public/img/all_mirrors.csv"

# Valid values for criteria
VALID_TOPICS = {'abortion', 'climate-change', 'immigration', 'gun-control'}
VALID_STANCES = {'left', 'right'}
VALID_STANCES_RELAXED = {'left', 'right', 'neutral', 'unclear'}


def normalize_text(text):
    """Normalize text for matching across datasets."""
    if pd.isna(text):
        return ""
    text = str(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def topic_is_valid(topic_str):
    """Check if topic contains only valid topics (can be multiple)."""
    if pd.isna(topic_str):
        return False
    topic_str = str(topic_str).strip().lower()
    if not topic_str or topic_str == 'no':
        return False
    topics = [t.strip() for t in topic_str.split(',')]
    return all(t in VALID_TOPICS for t in topics) and len(topics) > 0


def calculate_criteria_score(row):
    """
    Calculate how many criteria pass for a mirror.
    Returns (priority_tier, criteria_count, criteria_details)
    
    Priority tiers:
    1 = All 6 criteria pass (LLM_labels_valid_check = TRUE)
    2 = 5 criteria pass (relax Self-contained)
    3 = 4 criteria pass (relax Self-contained + Stance)
    4 = Fewer than 4 criteria pass (fallback)
    """
    # Check LLM_labels_valid_check first (this is the gold standard)
    llm_valid = str(row.get('LLM_labels_valid_check', '')).strip().upper() == 'TRUE'
    
    # Individual criteria
    political = str(row.get('Political', '')).strip().upper() == 'TRUE'
    news_opinion = str(row.get('News(0)_Opinion(1)', '')).strip().upper() == 'TRUE'
    complete = str(row.get('Complete', '')).strip().upper() == 'TRUE'
    self_contained = str(row.get('Self-contained', '')).strip().upper() == 'TRUE'
    topic_valid = topic_is_valid(row.get('Topic', ''))
    stance = str(row.get('Political Stance', '')).strip().lower()
    stance_strict = stance in VALID_STANCES
    stance_relaxed = stance in VALID_STANCES_RELAXED
    
    # Count criteria passed
    criteria_passed = {
        'Political': political,
        'News_Opinion': news_opinion,
        'Complete': complete,
        'Self_contained': self_contained,
        'Topic': topic_valid,
        'Stance_strict': stance_strict,
        'Stance_relaxed': stance_relaxed
    }
    
    # Determine priority tier
    if llm_valid:
        # Tier 1: All 6 criteria pass
        return (1, 6, criteria_passed)
    elif political and news_opinion and complete and topic_valid and stance_strict:
        # Tier 2: 5 criteria pass (relax Self-contained)
        return (2, 5, criteria_passed)
    elif political and news_opinion and complete and topic_valid and stance_relaxed:
        # Tier 3: 4 criteria pass (relax Self-contained + Stance to include neutral/unclear)
        return (3, 4, criteria_passed)
    else:
        # Tier 4: Fallback - count how many of the 4 core criteria pass
        core_count = sum([political, news_opinion, complete, topic_valid])
        return (4, core_count, criteria_passed)


def find_header_line(filepath):
    """Find the line number where the actual CSV header starts."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.startswith('id,user_id,'):
                return line_num
    raise ValueError(f"Could not find header row in {filepath}")


def load_human_mirrors_with_metadata(filepath):
    """Load human mirrors CSV, skipping metadata rows."""
    header_line = find_header_line(filepath)
    
    # Read the file, skipping metadata
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in range(header_line - 1):
            next(f)
        df = pd.read_csv(f, encoding='utf-8')
    
    return df


def main():
    random.seed(42)  # For reproducibility
    
    # Load human mirrors with metadata handling
    print("Loading human mirrors...")
    human_df = load_human_mirrors_with_metadata(HUMAN_CSV)
    print(f"  Human data: {len(human_df)} rows")
    print(f"  Unique posts: {human_df['post_number'].nunique()}")
    
    # Calculate criteria score for each mirror
    print("\nCalculating criteria scores for each mirror...")
    scores = human_df.apply(calculate_criteria_score, axis=1)
    human_df['priority_tier'] = [s[0] for s in scores]
    human_df['criteria_count'] = [s[1] for s in scores]
    
    # Count mirrors by tier
    tier_counts = human_df.groupby('priority_tier').size()
    print("\n--- Mirrors by priority tier ---")
    tier_names = {1: 'All 6 criteria', 2: 'Relax Self-contained', 
                  3: 'Relax Self-contained + Stance', 4: 'Fallback'}
    for tier in sorted(tier_counts.index):
        print(f"  Tier {tier} ({tier_names.get(tier, 'Unknown')}): {tier_counts[tier]} mirrors")
    
    # Select best mirror per post
    print("\nSelecting best mirror per post...")
    
    selected_mirrors = []
    # Filter out NaN post_numbers
    valid_posts = human_df[human_df['post_number'].notna()].copy()
    post_numbers = valid_posts['post_number'].unique()
    
    tier_selection_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for post_num in post_numbers:
        post_mirrors = valid_posts[valid_posts['post_number'] == post_num].copy()
        
        # Sort by priority tier (lower is better), then by criteria count (higher is better)
        post_mirrors = post_mirrors.sort_values(
            by=['priority_tier', 'criteria_count'],
            ascending=[True, False]
        )
        
        # Get the best tier available for this post
        best_tier = post_mirrors['priority_tier'].min()
        
        # Get all mirrors at the best tier
        best_mirrors = post_mirrors[post_mirrors['priority_tier'] == best_tier]
        
        # Randomly select one if multiple
        selected = best_mirrors.sample(1, random_state=int(post_num) + 42).iloc[0]
        selected_mirrors.append(selected)
        tier_selection_counts[best_tier] += 1
    
    selected_df = pd.DataFrame(selected_mirrors)
    
    print("\n--- Posts selected by tier ---")
    for tier in sorted(tier_selection_counts.keys()):
        print(f"  Tier {tier} ({tier_names.get(tier, 'Unknown')}): {tier_selection_counts[tier]} posts")
    print(f"  TOTAL: {sum(tier_selection_counts.values())} posts")
    
    # Load LLM mirrors
    print("\nLoading LLM mirrors...")
    llm_df = pd.read_csv(LLM_CSV)
    print(f"  LLM data: {len(llm_df)} rows")
    
    # Normalize text for matching
    print("\nNormalizing text for matching...")
    llm_df['text_normalized'] = llm_df['post_text'].apply(normalize_text)
    selected_df['text_normalized'] = selected_df['original_text'].apply(normalize_text)
    
    # Pivot LLM data
    llm_pivot = llm_df.pivot_table(
        index=['post_primary_key', 'post_text', 'text_normalized'],
        columns='model_id',
        values='mirrored_text',
        aggfunc='first'
    ).reset_index()
    llm_pivot.columns.name = None
    
    model_mapping = {
        'openrouter-llama-3.3-70b': 'llama_mirror',
        'openrouter-qwen3-32b': 'qwen_mirror',
        'claude-4.5-haiku': 'claude_mirror',
        'openai-gpt-4o-mini': 'gpt4o_mirror'
    }
    llm_pivot = llm_pivot.rename(columns=model_mapping)
    llm_pivot = llm_pivot.rename(columns={'post_text': 'original_text'})
    
    print(f"  LLM pivoted data: {len(llm_pivot)} unique posts")
    
    # Prepare human data for merge
    human_prepared = selected_df[['id', 'post_number', 'text_normalized', 'Cleaned Text', 'priority_tier']].copy()
    human_prepared = human_prepared.rename(columns={
        'id': 'human_mirror_id',
        'Cleaned Text': 'human_mirror',
        'priority_tier': 'selection_tier'
    })
    
    # Remove empty
    human_prepared = human_prepared[human_prepared['text_normalized'] != '']
    human_prepared = human_prepared[human_prepared['human_mirror'].notna()]
    human_prepared = human_prepared[human_prepared['human_mirror'].str.strip() != '']
    
    # Merge with LLM data
    merged = human_prepared.merge(
        llm_pivot,
        on='text_normalized',
        how='inner'
    )
    
    merged = merged.drop(columns=['text_normalized'])
    merged['post_number'] = merged['post_number'].astype(int)
    
    print(f"\n--- Final merged data ---")
    print(f"  Total rows (one per post): {len(merged)}")
    
    # Report on selection tiers in final output
    tier_final = merged['selection_tier'].value_counts().sort_index()
    print("\n--- Final selection tier breakdown ---")
    for tier, count in tier_final.items():
        print(f"  Tier {tier} ({tier_names.get(tier, 'Unknown')}): {count} posts")
    
    # Check for missing LLM mirrors
    for col in ['human_mirror', 'llama_mirror', 'qwen_mirror', 'claude_mirror', 'gpt4o_mirror']:
        if col in merged.columns:
            missing = merged[col].isna().sum()
            if missing > 0:
                print(f"  Rows missing {col}: {missing}")
    
    # Reorder columns
    final_columns = [
        'post_primary_key',
        'post_number',
        'human_mirror_id',
        'selection_tier',
        'original_text',
        'human_mirror',
        'llama_mirror',
        'qwen_mirror', 
        'claude_mirror',
        'gpt4o_mirror'
    ]
    final_columns = [c for c in final_columns if c in merged.columns]
    merged = merged[final_columns]
    
    # Sort by post_number
    merged = merged.sort_values('post_number').reset_index(drop=True)
    
    # Save
    merged.to_csv(OUTPUT_CSV, index=False)
    print(f"\n Saved merged data to {OUTPUT_CSV}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total posts in human_mirrors_original.csv: {len(post_numbers)}")
    print(f"Total posts in final all_mirrors.csv: {len(merged)}")
    print(f"Posts not matched (missing LLM mirrors): {len(post_numbers) - len(merged)}")


if __name__ == "__main__":
    main()
