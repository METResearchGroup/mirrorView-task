# Filter posts used for stimulus dataset

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

For the next study, we want to figure out what posts will be in our stimulus dataset.

We have a dataset of ~55,000 posts, from `experiments/combine_data_into_stimulus_set_2026_09_08`. We'll now filter this down to 10,000 posts.

Some rules for us to consider:

- An even 1:1:1 split across all 3 toxicity classes
- An even 1:1 split across political parties.

Cleanup steps:

- Drop posts that have the same ID
- Drop posts that have the same text.

Once done with cleanup, we can sample so we have ~even distributions across all toxicity classes and political parties (ideally each cell would be equivalent).

We need to do this in conjunction with our previous stimuli dataset, as we eventually want a full 20,000 post x 5 labels per post = 100,000 total labels. So, we need 10,000 total labels. Let's aim for 10,200 so as to have an even ~1,700 labels per cell in the political party x toxicity split.

We need the following files:

- load_raw_candidate_dataset.py: to load the candidate ~55,000 post dataset.
- cleanup_raw_candidate_dataset.py
- sample_raw_candidate_dataset.py
- upload_filtered_candidate_dataset.py: uploads the candidate dataset to S3, using the `mirrorview-experimental-artifacts` bucket and `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/` S3 prefix.
