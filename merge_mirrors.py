#!/usr/bin/env python3
"""
Merge human and LLM mirror data into a single CSV.

Output columns:
- post_primary_key: unique identifier for the original post
- original_text: the original post text
- human_mirror: the human-written mirror
- llama_mirror: mirror from openrouter-llama-3.3-70b
- qwen_mirror: mirror from openrouter-qwen3-32b
- claude_mirror: mirror from claude-4.5-haiku
- gpt4o_mirror: mirror from gpt-4o-mini
"""

import pandas as pd
import re
from io import StringIO

# Paths
LLM_CSV = "public/img/llm_mirrors.csv"
HUMAN_CSV = "public/img/human_mirrors.csv"
OUTPUT_CSV = "public/img/all_mirrors.csv"


def normalize_text(text):
    """Normalize text for matching across datasets."""
    if pd.isna(text):
        return ""
    text = str(text)
    # Normalize line endings (Windows \r\n -> Unix \n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Normalize HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    # Normalize whitespace (collapse multiple spaces/newlines to single space)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def load_human_csv(filepath):
    """Load human mirrors CSV, skipping metadata at the top."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find the header line (starts with "id,user_id")
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('id,user_id,original_post_id'):
            header_idx = i
            break
    
    if header_idx is None:
        raise ValueError("Could not find header row in human mirrors CSV")
    
    data = ''.join(lines[header_idx:])
    return pd.read_csv(StringIO(data))


def main():
    # Load LLM mirrors
    print("Loading LLM mirrors...")
    llm_df = pd.read_csv(LLM_CSV)
    print(f"  LLM data: {len(llm_df)} rows")
    print(f"  Models: {llm_df['model_id'].unique().tolist()}")
    
    # Load human mirrors
    print("\nLoading human mirrors...")
    human_df = load_human_csv(HUMAN_CSV)
    print(f"  Human data: {len(human_df)} rows")
    
    # Create normalized text columns for matching
    print("\nNormalizing text for matching...")
    llm_df['text_normalized'] = llm_df['post_text'].apply(normalize_text)
    human_df['text_normalized'] = human_df['original_text'].apply(normalize_text)
    
    # Check overlap BEFORE normalization (for comparison)
    llm_originals_raw = set(llm_df['post_text'].unique())
    human_originals_raw = set(human_df['original_text'].dropna().unique())
    overlap_raw = len(llm_originals_raw.intersection(human_originals_raw))
    
    # Check overlap AFTER normalization
    llm_originals_norm = set(llm_df['text_normalized'].unique())
    human_originals_norm = set(human_df['text_normalized'].dropna().unique())
    # Remove empty strings
    human_originals_norm.discard('')
    overlap_norm = len(llm_originals_norm.intersection(human_originals_norm))
    
    print(f"\n--- Matching improvement ---")
    print(f"  Before normalization: {overlap_raw} matching posts")
    print(f"  After normalization:  {overlap_norm} matching posts")
    print(f"  Improvement: +{overlap_norm - overlap_raw} posts recovered")
    
    # Pivot LLM data: one row per post, columns for each model
    print("\n--- Creating merged dataframe ---")
    llm_pivot = llm_df.pivot_table(
        index=['post_primary_key', 'post_text', 'text_normalized'],
        columns='model_id',
        values='mirrored_text',
        aggfunc='first'
    ).reset_index()
    
    llm_pivot.columns.name = None
    
    # Rename model columns
    model_mapping = {
        'openrouter-llama-3.3-70b': 'llama_mirror',
        'openrouter-qwen3-32b': 'qwen_mirror',
        'claude-4.5-haiku': 'claude_mirror',
        'openai-gpt-4o-mini': 'gpt4o_mirror'
    }
    llm_pivot = llm_pivot.rename(columns=model_mapping)
    llm_pivot = llm_pivot.rename(columns={'post_text': 'original_text'})
    
    print(f"  LLM pivoted data: {len(llm_pivot)} rows")
    
    # Prepare human data - use 'Cleaned Text' for the human mirror
    # Group by normalized text to handle duplicates
    human_grouped = human_df.groupby('text_normalized').agg({
        'Cleaned Text': 'first'
    }).reset_index()
    human_grouped = human_grouped.rename(columns={'Cleaned Text': 'human_mirror'})
    
    # Remove empty normalized text rows
    human_grouped = human_grouped[human_grouped['text_normalized'] != '']
    print(f"  Human grouped data: {len(human_grouped)} rows")
    
    # Merge on normalized text
    merged = llm_pivot.merge(
        human_grouped,
        on='text_normalized',
        how='left'
    )
    
    # Drop the normalized column from final output
    merged = merged.drop(columns=['text_normalized'])
    
    print(f"\n--- Final merged data ---")
    print(f"  Total rows: {len(merged)}")
    
    # Check for missing data
    missing_human = merged['human_mirror'].isna().sum()
    print(f"  Posts with human mirror: {len(merged) - missing_human}")
    print(f"  Posts missing human mirror: {missing_human}")
    
    for col in ['llama_mirror', 'qwen_mirror', 'claude_mirror', 'gpt4o_mirror']:
        if col in merged.columns:
            missing = merged[col].isna().sum()
            if missing > 0:
                print(f"  Posts missing {col}: {missing}")
    
    # Reorder columns
    final_columns = [
        'post_primary_key',
        'original_text',
        'human_mirror',
        'llama_mirror',
        'qwen_mirror', 
        'claude_mirror',
        'gpt4o_mirror'
    ]
    final_columns = [c for c in final_columns if c in merged.columns]
    merged = merged[final_columns]
    
    # Save
    merged.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved merged data to {OUTPUT_CSV}")
    
    # Show sample
    print("\n--- Sample of merged data ---")
    sample = merged.head(2)
    for idx, row in sample.iterrows():
        print(f"\nPost {idx+1}:")
        print(f"  Original: {row['original_text'][:100]}...")
        if pd.notna(row.get('human_mirror')):
            print(f"  Human: {str(row['human_mirror'])[:100]}...")
        for model in ['llama_mirror', 'qwen_mirror', 'claude_mirror', 'gpt4o_mirror']:
            if model in row and pd.notna(row[model]):
                print(f"  {model.replace('_mirror','')}: {str(row[model])[:80]}...")


if __name__ == "__main__":
    main()
