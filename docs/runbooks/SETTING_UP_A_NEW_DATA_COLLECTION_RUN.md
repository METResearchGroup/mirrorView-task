# Setting up a new data collection run

1. Define a config in `jobs/config` so that we know what configs we wanted to define.
2. Ask Cursor to replace the values in the relevant .js files with the values in the YAML file.
3. Re-deploy.

We're doing it in this way as the original design of this hardcoded a lot of values and we're working with those existing constraints.
