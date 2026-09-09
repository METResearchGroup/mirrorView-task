# Provision jspsych-mirror-view-2026-09-09

Create the September 2026 study bucket with the one-off script. Leave
`jspsych-mirror-view-4` in Terraform state.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python scripts/provision_jspsych_mirror_view_2026_09_09.py
```

After this script, do not run `terraform apply` in
`/Users/mark/src/work/mirrorView-task/webapp/infra` with a new `bucket_name`, and
do not apply the June tfvars either, because that apply would set save-data
`BUCKET_NAME` back to `jspsych-mirror-view-4`.

Assignment reads still need
[issue 17](https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17)
applied in the other repo.
