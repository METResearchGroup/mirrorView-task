# Mirrors content analysis

Set of basic exploratory analyses for the mirrors.

## Steps

1. Run `dataloader.py`. Get the latest `mirrorview_pilot_trial_data_{timestamp}.csv` file, processing the latest pilot data into a curated form.
2. Run the analyses.

## Analysis 1: Basic length measures

- Characters
- Words
- Sentences
- Average sentence length
- Puncutation density

### Questions to answer

- Aggregate analysis: are mirrored texts systematically longer, shorter, or denser?
- Pairwise analysis: basic stats (ratio, absolute difference)
- Keep/remove decision: test whether longer or more compressed mirrors are more likely to be removed
