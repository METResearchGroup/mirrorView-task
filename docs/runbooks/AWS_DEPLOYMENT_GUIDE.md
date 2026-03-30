# AWS Deployment Guide for jsPsych Scrolling Experiment

## Overview
This guide walks you through setting up the AWS infrastructure for the scrolling social media feed experiment.

## Prerequisites
- AWS Account with appropriate permissions
- AWS CLI configured (optional)

## Step 1: Create S3 Bucket

### Via AWS Console:
1. Go to AWS S3 Console
2. Click "Create bucket"
3. **Bucket name**: `jspsych-scroll`
4. **Region**: `us-east-2` (Ohio)
5. **Block Public Access**: Keep default settings
6. Click "Create bucket"

### Set up bucket structure:
After creating the bucket, create these folders:
- `data/` (for experiment data and participant assignments)
- `img/` (for images - you'll need to upload your image folders here)

## Step 2: Create Lambda Functions

### Function 1: get-participant-id

1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. **Function name**: `jspsych-scroll-get-participant-id`
5. **Runtime**: Node.js 20.x
6. **Architecture**: x86_64
7. Click "Create function"

**Code**: Use the contents from `lambda-get-participant-id.mjs`

**Permissions**: The function needs S3 permissions. Add this policy to the execution role:
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

### Function 2: save-jspsych-data

1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. **Function name**: `jspsych-scroll-save-data`
5. **Runtime**: Node.js 20.x
6. **Architecture**: x86_64
7. Click "Create function"

**Code**: Use the contents from `lambda-save-jspsych-data.mjs`

**Permissions**: Same S3 policy as above.

## Step 3: Create API Gateway

1. Go to AWS API Gateway Console
2. Click "Create API"
3. Choose "HTTP API" → "Build"
4. **API name**: `jspsych-scroll-api`
5. Click "Next" and keep default settings
6. Click "Create"

### Add Routes:

#### Route 1: GET /get-participant-id
1. Click "Routes" in the left sidebar
2. Click "Create"
3. **Method**: GET
4. **Resource path**: `/get-participant-id`
5. Click "Create"
6. Click on the route → "Attach integration"
7. **Integration type**: Lambda function
8. **Lambda function**: `jspsych-scroll-get-participant-id`
9. Click "Attach integration"

#### Route 2: POST /save-jspsych-data
1. Click "Create" (new route)
2. **Method**: POST
3. **Resource path**: `/save-jspsych-data`
4. Click "Create"
5. Click on the route → "Attach integration"
6. **Integration type**: Lambda function
7. **Lambda function**: `jspsych-scroll-save-data`
8. Click "Attach integration"

### Configure CORS:
1. Go to "CORS" in the left sidebar
2. Click "Configure"
3. **Access-Control-Allow-Origin**: `*`
4. **Access-Control-Allow-Headers**: `*`
5. **Access-Control-Allow-Methods**: `GET, POST, OPTIONS, DELETE`
6. Click "Save"

### Deploy the API:
1. Click "Deploy" → "Deploy to stage"
2. **Stage name**: `prod`
3. Click "Deploy"
4. **Note the Invoke URL** - you'll need this for the next step!

## Step 4: Update main.js with API URLs

Your API Gateway invoke URL will look like:
`https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/prod`

You'll need to update the URLs in `public/main.js`:
```javascript
const GET_PARTICIPANT_ID_URL = 'https://YOUR-API-ID.execute-api.us-east-2.amazonaws.com/prod/get-participant-id';
const SAVE_DATA_URL = 'https://YOUR-API-ID.execute-api.us-east-2.amazonaws.com/prod/save-jspsych-data';
```

## Step 5: Upload Files to S3

Upload all files from the `public/` folder to your S3 bucket root:
- `index.html`
- `main.js` (with updated API URLs)
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

## Step 6: Enable Static Website Hosting

1. Go to your S3 bucket
2. Click "Properties" tab
3. Scroll to "Static website hosting"
4. Click "Edit"
5. **Static website hosting**: Enable
6. **Index document**: `index.html`
7. Click "Save changes"

**Note the website endpoint URL** - this is where your experiment will be hosted!

## Step 7: Set Bucket Policy for Public Access

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

## Testing

1. Visit your S3 static website URL
2. Test the experiment flow
3. Check CloudWatch logs for any Lambda function errors
4. Verify data is being saved to the `data/` folder in S3

## URLs You'll Need for Prolific

- **Experiment URL**: Your S3 static website URL
- **Completion redirect**: The experiment will handle this automatically

## Troubleshooting

- Check Lambda function logs in CloudWatch
- Verify S3 permissions and bucket policy
- Ensure API Gateway CORS is configured correctly
- Make sure Lambda functions have the correct S3 permissions
