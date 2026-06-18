# Setting up a new data collection run

## TL;DR

1. Define a config in `jobs/config` so that we know what configs we wanted to define.
2. Ask Cursor to replace the values in the relevant .js files with the values in the YAML file. Prompt is something like "look at the values in  @jobs/config/mirrorview_scaled_2026_06_18.yaml and list out the files and what values have to be replaced, based on what's in the config."
3. Re-deploy.

We're doing it in this way as the original design of this hardcoded a lot of values and we're working with those existing constraints.

## Actual steps
