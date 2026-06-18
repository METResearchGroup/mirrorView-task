# Terraform variables for mirrorview_scaled_2026_06_18 job.
# Apply with: terraform apply -var-file=../jobs/terraform/mirrorview_scaled_2026_06_18.tfvars

aws_region             = "us-east-2"
bucket_name            = "jspsych-mirror-view-4"
assignment_lambda_name = "get_study_assignment"

tags = {
  Job = "mirrorview_scaled_2026_06_18"
}
