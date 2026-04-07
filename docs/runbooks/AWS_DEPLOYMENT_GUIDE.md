# AWS Deployment Guide for jsPsych Scrolling Experiment

## Overview

This guide covers deploying the AWS infrastructure for the scrolling social media feed experiment.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws` on your PATH; same credentials used for uploads and verification)
- [uv](https://docs.astral.sh/uv/) installed (Python 3.12 project env at repo root; see `pyproject.toml`)

## When do you need to read this?

This section is a quick guide for deciding what needs to be redeployed after a change.

### When to redeploy the Lambda

Rerun Terraform whenever either Lambda source file changes:

- `lambda-get-post-assignments.mjs`
- `lambda-save-jspsych-data.mjs`

This repo packages those files directly into the deployed Lambda functions, so changing either file means you should run `terraform plan` and `terraform apply` again to update AWS.

You should also rerun Terraform if you change infrastructure-related settings in `infra/main.tf`, such as API Gateway configuration, IAM permissions, bucket settings, or Lambda environment variables.

Useful AWS CLI checks:

```bash
aws lambda get-function-configuration \
  --region us-east-2 \
  --function-name jspsych-scroll-get-post-assignments \
  --query '{function_name:FunctionName,last_modified:LastModified,assignment_lambda_name:Environment.Variables.ASSIGNMENT_LAMBDA_NAME}' \
  --output table

aws lambda get-function-configuration \
  --region us-east-2 \
  --function-name jspsych-scroll-save-data \
  --query '{function_name:FunctionName,last_modified:LastModified}' \
  --output table
```

### When to redeploy `public/`

Re-upload `public/` to S3 whenever any browser-served asset changes, including:

- `public/config.js`
- `public/index.html`
- `public/main.js`
- CSS, survey files, plugin files, library files, or images under `public/`

This does not require rerunning Terraform unless the infrastructure itself changed. For frontend-only updates, publish the current `public/` tree to the S3 bucket using the upload toolchain (file-by-file `aws s3 cp` to the bucket root; no bucket-wide sync and no deletes).

Keep `public/config.js` up to date with the deployed API Gateway URLs. In particular, `POST_ASSIGNMENTS_URL` and `SAVE_DATA_URL` must match the currently deployed `jspsych-scroll-api` stage URLs. The upload scripts validate this against the live API before uploading.

Useful AWS CLI checks:

```bash
aws apigatewayv2 get-apis \
  --region us-east-2 \
  --query "Items[?Name=='jspsych-scroll-api'].ApiEndpoint" \
  --output text
```

If that command returns `https://abc123.execute-api.us-east-2.amazonaws.com`, then the values in `public/config.js` should be:

```javascript
POST_ASSIGNMENTS_URL: 'https://abc123.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments'
SAVE_DATA_URL: 'https://abc123.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data'
```

## Automated Deployment (Preferred)

Use `infra/main.tf` to provision the AWS infrastructure:

- S3 bucket for static hosting and experiment data
- Lambda functions and IAM roles
- HTTP API Gateway routes and CORS
- CloudWatch log groups

### What Terraform Manages

- S3 bucket creation
- Static website hosting configuration
- Public bucket policy for website assets
- Lambda creation and permissions
- API Gateway creation, routes, integrations, and `prod` stage

### What Still Requires Manual Steps

- Updating `public/config.js` from Terraform outputs, if you are not generating it automatically
- Uploading files from `public/` to S3 (use `scripts/upload_to_s3/`; see below)
- Validating the deployed experiment end to end

### Upload public assets to S3 (preferred)

From the **repository root**:

1. Ensure `public/config.js` matches the deployed API (the scripts query `jspsych-scroll-api` in `us-east-2` and compare exact URLs).
2. Stage locally, then print intended S3 keys without uploading:

   ```bash
   uv python install 3.12
   uv sync
   PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
   ```

3. Inspect the staged directory: expect `index.html`, `config.js`, `main.js`, survey JS/CSS, `jspsych/`, `plugins/`, `lib/`, and `img/` when those exist under `public/`.

4. **Full deploy** (upload then verify manifest + critical keys in S3):

   ```bash
   bash scripts/upload_to_s3/run_upload.sh
   ```

   Or run the Python steps yourself:

   ```bash
   PYTHONPATH=. uv run python scripts/upload_to_s3/stage_public_for_s3.py
   PYTHONPATH=. uv run python scripts/upload_to_s3/upload_public_to_s3.py
   PYTHONPATH=. uv run python scripts/upload_to_s3/verify_s3_upload.py
   ```

5. **Verify a specific staged release** (optional):

   ```bash
   PYTHONPATH=. uv run python scripts/upload_to_s3/verify_s3_upload.py
   ```

Behavior notes:

- Only website-owned keys under the bucket root are written; nothing under the `data/` prefix is uploaded or deleted.
- Objects are uploaded one file at a time (`aws s3 cp`); existing keys are overwritten; no `aws s3 sync --delete` or other delete operations.

The legacy script `prepare_for_aws.py` is deprecated; use the commands above instead.

### Terraform Setup

Before running the automated deployment, make sure Terraform is installed and AWS credentials are available in your shell environment.

1. Install Terraform locally if it is not already installed.
2. Authenticate to AWS using your preferred method, such as configured AWS CLI credentials or environment variables.
3. From the repository root, change into the Terraform directory:
   - `cd infra`
4. Initialize the Terraform working directory:
   - `terraform init`
5. Review the default variables in `infra/main.tf`, especially:
   - `aws_region`
   - `bucket_name`
   - `assignment_lambda_name`
6. If you need to override defaults, provide values with a `terraform.tfvars` file or `-var` arguments when running `terraform plan` and `terraform apply`.

### Suggested Terraform Workflow

1. Review `infra/main.tf`
2. Run `terraform plan`
3. Run `terraform apply`
4. Capture the outputs for:
   - S3 website endpoint
   - API base URL
   - `post_assignments_url`
   - `save_data_url`
5. Update `public/config.js`
6. Upload the `public/` assets to S3 (`bash scripts/upload_to_s3/run_upload.sh` or the `uv run` commands in [Upload public assets to S3](#upload-public-assets-to-s3-preferred))
7. Test the experiment flow

### Debugging

#### What happens if you get a `ResourceAlreadyExistsException` error?

You might get an error like, e.g.,

```bash
│ Error: creating S3 Bucket (jspsych-mirror-view-3): operation error S3: CreateBucket, https response error StatusCode: 409, RequestID: S7C8JH49PQC1R512, HostID: dgia+8ppT5Y5VsXat7a+JNRYu/Y4fMkNc+WwblMxJtEme9fZ7q73nnCt183umbuYivwi83iir0wIaAY7ygnPN1HD+HtEdZjU, BucketAlreadyOwnedByYou: 
│ 
│   with aws_s3_bucket.site,
│   on main.tf line 81, in resource "aws_s3_bucket" "site":
│   81: resource "aws_s3_bucket" "site" {
│ 
╵
╷
│ Error: creating CloudWatch Logs Log Group (/aws/lambda/jspsych-scroll-save-data): operation error CloudWatch Logs: CreateLogGroup, https response error StatusCode: 400, RequestID: 8b0a8532-7d65-4712-bc79-44e0ad85809f, ResourceAlreadyExistsException: The specified log group already exists
│ 
│   with aws_cloudwatch_log_group.save_data,
│   on main.tf line 204, in resource "aws_cloudwatch_log_group" "save_data":
│  204: resource "aws_cloudwatch_log_group" "save_data" {
│ 
╵
```

To resolve this, import the related resource:

```bash
terraform import aws_s3_bucket.site jspsych-mirror-view-3

terraform import aws_cloudwatch_log_group.save_data /aws/lambda/jspsych-scroll-save-data
```

### Verification

After `terraform apply`, verify the automated deployment before uploading the frontend assets:

1. Confirm Terraform outputs were produced for:
   - `bucket_name`
   - `website_endpoint`
   - `api_base_url`
   - `post_assignments_url`
   - `save_data_url`
2. In AWS, confirm the S3 bucket exists in `us-east-2` and has static website hosting enabled with `index.html` as the index document.
3. Confirm the Lambda functions `jspsych-scroll-get-post-assignments` and `jspsych-scroll-save-data` exist and show successful deployments.
4. Confirm the `jspsych-scroll-get-post-assignments` Lambda has the `ASSIGNMENT_LAMBDA_NAME` environment variable set to `get_study_assignment`.
5. Confirm the HTTP API exists with a `prod` stage and routes for:
   - `POST /get-post-assignments`
   - `POST /save-jspsych-data`
6. Confirm both API routes are integrated with the expected Lambda functions and that CORS allows `POST` and `OPTIONS`.
7. After updating `public/config.js`, make sure the two endpoint URLs match the Terraform outputs exactly.
8. After uploading the frontend assets, open the S3 website endpoint and walk through the experiment flow.
9. Check CloudWatch logs for both Lambda functions while testing, and verify that submitted CSV data is written under the bucket's `data/` prefix.

## Manual Deployment

Use this section only if you are not provisioning infrastructure with Terraform.

### Step 1: Create S3 Bucket

#### Via AWS Console

1. Go to AWS S3 Console
2. Click "Create bucket"
3. **Bucket name**: `jspsych-scroll`
4. **Region**: `us-east-2` (Ohio)
5. **Block Public Access**: Keep default settings
6. Click "Create bucket"

#### Set up bucket structure

S3 does not require you to pre-create folders, but you may choose to organize assets as:

- `data/` (for experiment data)
- `img/` (for images - upload your image folders here)

### Step 2: Create Lambda Functions

#### Function 1: get-post-assignments

1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. **Function name**: `jspsych-scroll-get-post-assignments`
5. **Runtime**: Node.js 20.x
6. **Architecture**: x86_64
7. Click "Create function"

**Code**: Use the contents from `lambda-get-post-assignments.mjs`

**Permissions**: Configure the `ASSIGNMENT_LAMBDA_NAME` environment variable needed by `lambda-get-post-assignments.mjs` and grant any permissions required by the downstream assignment Lambda it invokes. `STUDY_ID` and `STUDY_ITERATION_ID` are now sent by the public client request rather than read from Lambda env vars.
If your deployment still relies on S3-backed helpers elsewhere, add the relevant S3 policy to the execution role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::jspsych-scroll/*"
            ]
        }
    ]
}
```

#### Function 2: save-jspsych-data

1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. **Function name**: `jspsych-scroll-save-data`
5. **Runtime**: Node.js 20.x
6. **Architecture**: x86_64
7. Click "Create function"

**Code**: Use the contents from `lambda-save-jspsych-data.mjs`

**Permissions**: Same S3 policy as above.

### Step 3: Create API Gateway

1. Go to AWS API Gateway Console
2. Click "Create API"
3. Choose "HTTP API" → "Build"
4. **API name**: `jspsych-scroll-api`
5. Click "Next" and keep default settings
6. Click "Create"

#### Add Routes

##### Route 1: POST /get-post-assignments

1. Click "Routes" in the left sidebar
2. Click "Create"
3. **Method**: POST
4. **Resource path**: `/get-post-assignments`
5. Click "Create"
6. Click on the route → "Attach integration"
7. **Integration type**: Lambda function
8. **Lambda function**: `jspsych-scroll-get-post-assignments`
9. Click "Attach integration"

##### Route 2: POST /save-jspsych-data

1. Click "Create" (new route)
2. **Method**: POST
3. **Resource path**: `/save-jspsych-data`
4. Click "Create"
5. Click on the route → "Attach integration"
6. **Integration type**: Lambda function
7. **Lambda function**: `jspsych-scroll-save-data`
8. Click "Attach integration"

#### Configure CORS

1. Go to "CORS" in the left sidebar
2. Click "Configure"
3. **Access-Control-Allow-Origin**: `*`
4. **Access-Control-Allow-Headers**: `*`
5. **Access-Control-Allow-Methods**: `POST, OPTIONS`
6. Click "Save"

#### Deploy the API

1. Click "Deploy" → "Deploy to stage"
2. **Stage name**: `prod`
3. Click "Deploy"
4. **Note the Invoke URL** - you'll need this for the next step!

### Step 4: Update `public/config.js` with API URLs

Your API Gateway invoke URL will look like:

`https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/prod`

You'll need to update the URLs in `public/config.js`:

```javascript
const config = {
  POST_ASSIGNMENTS_URL: 'https://YOUR-API-ID.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments',
  SAVE_DATA_URL: 'https://YOUR-API-ID.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data',
  STUDY_ID: 'your-study-id',
  STUDY_ITERATION_ID: 'your-study-iteration-id',
};
```

### Step 5: Upload Files to S3

Upload the full `public/` tree to your S3 bucket root using the same toolchain as the Terraform workflow: `bash scripts/upload_to_s3/run_upload.sh` from the repo root (after `uv sync`), or follow the `uv run python scripts/upload_to_s3/...` commands in [Upload public assets to S3](#upload-public-assets-to-s3-preferred). Do not use a sync mode that deletes remote objects; experiment data under `data/` must remain untouched.

### Step 6: Enable Static Website Hosting

1. Go to your S3 bucket
2. Click "Properties" tab
3. Scroll to "Static website hosting"
4. Click "Edit"
5. **Static website hosting**: Enable
6. **Index document**: `index.html`
7. Click "Save changes"

**Note the website endpoint URL** - this is where your experiment will be hosted!

### Step 7: Set Bucket Policy for Public Access

You'll need to make the bucket publicly readable. In the bucket permissions, add this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::jspsych-scroll/*"
        }
    ]
}
```

### Testing

1. Visit your S3 static website URL
2. Test the experiment flow
3. Check CloudWatch logs for any Lambda function errors
4. Verify data is being saved to the `data/` folder in S3

### URLs You'll Need for Prolific

- **Experiment URL**: Your S3 static website URL
- **Completion redirect**: The experiment will handle this automatically

### Troubleshooting

- Check Lambda function logs in CloudWatch
- Verify S3 permissions and bucket policy
- Ensure API Gateway CORS is configured correctly
- Make sure Lambda functions have the correct S3 permissions
