#!/usr/bin/env python3
"""
Merge human and LLM mirror data into a single CSV.

Takes ONE human mirror per post (randomly selected if multiple valid mirrors exist).
Each post appears once in the output with 1 human mirror + 4 LLM mirrors.

Output columns:
- post_primary_key: unique identifier for the original post
- post_number: easier to reference (1-3 digit number)
- human_mirror_id: unique identifier for the selected human mirror row
- original_text: the original post text
- human_mirror: the human-written mirror (one per post)
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
HUMAN_CSV = "public/img/human_mirrors_valid_or_relaxed.csv"
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


def main():
    # Load LLM mirrors
    print("Loading LLM mirrors...")
    llm_df = pd.read_csv(LLM_CSV)
    print(f"  LLM data: {len(llm_df)} rows")
    print(f"  Models: {llm_df['model_id'].unique().tolist()}")
    
    # Load human mirrors (new format - already has proper header, no metadata to skip)
    print("\nLoading human mirrors...")
    human_df = pd.read_csv(HUMAN_CSV, encoding='utf-8')
    print(f"  Human data: {len(human_df)} rows")
    
    # Filter to only valid human mirrors (LLM_labels_valid_check == TRUE)
    if 'LLM_labels_valid_check' in human_df.columns:
        valid_human_df = human_df[human_df['LLM_labels_valid_check'].astype(str).str.upper() == 'TRUE'].copy()
        print(f"  Valid human mirrors: {len(valid_human_df)} rows")
        
        # Show distribution of valid mirrors per post
        valid_counts = valid_human_df.groupby('original_text').size()
        print(f"\n--- Valid mirrors per post distribution ---")
        print(f"  Posts with 1 valid mirror:  {(valid_counts == 1).sum()}")
        print(f"  Posts with 2 valid mirrors: {(valid_counts == 2).sum()}")
        print(f"  Posts with 3 valid mirrors: {(valid_counts == 3).sum()}")
        print(f"  Posts with 4+ valid mirrors: {(valid_counts >= 4).sum()}")
        print(f"  Total unique posts with valid mirrors: {len(valid_counts)}")
    else:
        print("  WARNING: 'LLM_labels_valid_check' column not found!")
        print(f"  Available columns: {human_df.columns.tolist()}")
        valid_human_df = human_df.copy()
    
    # Create normalized text columns for matching
    print("\nNormalizing text for matching...")
    llm_df['text_normalized'] = llm_df['post_text'].apply(normalize_text)
    valid_human_df['text_normalized'] = valid_human_df['original_text'].apply(normalize_text)
    
    # Check overlap BEFORE normalization (for comparison)
    llm_originals_raw = set(llm_df['post_text'].unique())
    human_originals_raw = set(valid_human_df['original_text'].dropna().unique())
    overlap_raw = len(llm_originals_raw.intersection(human_originals_raw))
    
    # Check overlap AFTER normalization
    llm_originals_norm = set(llm_df['text_normalized'].unique())
    human_originals_norm = set(valid_human_df['text_normalized'].dropna().unique())
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
    
    print(f"  LLM pivoted data: {len(llm_pivot)} unique posts")
    
    # Prepare human data - take FIRST valid mirror per post (not all)
    # Group by normalized text to handle duplicates, take first of each
    human_prepared = valid_human_df[['id', 'post_number', 'text_normalized', 'Cleaned Text']].copy()
    human_prepared = human_prepared.rename(columns={
        'id': 'human_mirror_id',
        'Cleaned Text': 'human_mirror'
    })
    
    # Remove empty normalized text rows and empty mirrors
    human_prepared = human_prepared[human_prepared['text_normalized'] != '']
    human_prepared = human_prepared[human_prepared['human_mirror'].notna()]
    human_prepared = human_prepared[human_prepared['human_mirror'].str.strip() != '']
    
    # GROUP BY text_normalized and take ONE random mirror per post
    human_grouped = human_prepared.groupby('text_normalized', group_keys=False).apply(
        lambda x: x.sample(1)
    ).reset_index(drop=True)
    
    print(f"  Human grouped data (one per post): {len(human_grouped)} rows")
    
    # Merge: One row per post with LLM data
    merged = human_grouped.merge(
        llm_pivot,
        on='text_normalized',
        how='inner'  # Only keep rows where we have both human AND LLM data
    )
    
    # Drop the normalized column from final output
    merged = merged.drop(columns=['text_normalized'])
    
    # Convert post_number to integer (remove .0)
    merged['post_number'] = merged['post_number'].astype(int)
    
    print(f"\n--- Final merged data ---")
    print(f"  Total rows (one per post): {len(merged)}")
    
    # Check for missing data
    for col in ['human_mirror', 'llama_mirror', 'qwen_mirror', 'claude_mirror', 'gpt4o_mirror']:
        if col in merged.columns:
            missing = merged[col].isna().sum()
            if missing > 0:
                print(f"  Rows missing {col}: {missing}")
    
    # Reorder columns
    final_columns = [
        'post_primary_key',
        'post_number',  # Easier to reference (1-3 digit number)
        'human_mirror_id',
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
        print(f"\nRow {idx+1}:")
        print(f"  Post Key: {row['post_primary_key']}")
        print(f"  Human Mirror ID: {row['human_mirror_id']}")
        print(f"  Original: {row['original_text'][:80]}...")
        if pd.notna(row.get('human_mirror')):
            print(f"  Human: {str(row['human_mirror'])[:80]}...")
        for model in ['llama_mirror', 'qwen_mirror', 'claude_mirror', 'gpt4o_mirror']:
            if model in row and pd.notna(row[model]):
                print(f"  {model.replace('_mirror','')}: {str(row[model])[:60]}...")


if __name__ == "__main__":
    main()
