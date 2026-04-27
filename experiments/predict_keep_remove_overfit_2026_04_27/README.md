# Problem scope

We have a dataset in `experiments/mirrors_content_analysis_2026-04-24/mirrorview_pilot_data_2026-04-15.csv` with initial keep/remove data for our Mirrorview project.

First, read `docs/runbooks/WHAT_IS_MIRRORVIEW.md` for what the project is.

Then, the goal here is to create a model to overfit on our initial pilot data. We want to see what it would look like (in terms of problem setup, loss, etc.) to train a model to predict the keep/remove decisions. By creating a v1 that's overfit on our initial pilot data, we can make informed decisions about how much data we need, how to design the problem, etc.

Use Wandb to track your experiments. Call the project "Mirrorview initial model training, 2026-04-27".

API keys can be accessed via `lib/load_env_vars.py`.
