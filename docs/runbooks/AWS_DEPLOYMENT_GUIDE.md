# AWS Deployment Guide for jsPsych Scrolling Experiment

## Overview

This guide covers deploying the AWS infrastructure for the scrolling social media feed experiment.
Use Terraform for infrastructure provisioning whenever possible. The older AWS Console flow is kept below for manual deployment and troubleshooting.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (optional)

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
- Uploading files from `public/` to S3
- Validating the deployed experiment end to end

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
6. Upload the `public/` assets to S3
7. Test the experiment flow

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

Upload all files from the `public/` folder to your S3 bucket root:

- `index.html`
- `config.js` (with updated API URLs)
- `main.js`
- `consent.js`
- `pre_surveys.js`
- `post_surveys.js`
- `preload.js`
- `slide_numbers.js`
- `meriel.css`
- `jspsych/` folder
- `plugins/` folder
- `lib/` folder
- `img/` folder (all your image directories)

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
