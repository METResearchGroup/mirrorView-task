# Testing

## Distribution assignment invariants

Adding some testing to make sure that certain assumptions about how the data will flow ends up being consistent.

Case 1: Number of participants

- Should be N participants, N//2 per condition. For 1,000 participants, assign 500 per condition.
- Stimuli randomization: control vs. training_assisted.

Every 20 posts:

- 5 low toxicity
- 5 high toxicity
- 10 middle toxicity

For toxicity, also split by left/right

- For low toxicity (5 posts): left 3 / right 2
- For high toxicity (5 posts): alternates 3/2 vs 2/3
- For middle toxicity (10 posts): split 5/5

Per-participant distribution with current logic:

- Toxicity: always ~5 / 5 / 10 (low/high/middle)
- Ideology: usually 10/10 or 11/9 (left/right), due to slight catalog asymmetry in right-low plus tie rotation.

Selection prioritizes: Unseen posts in that condition; so full coverage is achieved before repeats.

Assignments are first written to pending_assignments; they are committed to the main JSON trackers only after successful data save (to avoid including participant dropouts in image sorting).
