# SageMaker training execution role for ModernBERT Experiment 2.
# Scoped to s3://jspsych-mirror-view-4/modernbert-training/* in us-east-2.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

locals {
  role_name  = "modernbert-sagemaker-execution"
  s3_bucket  = "jspsych-mirror-view-4"
  s3_prefix  = "modernbert-training"
  aws_region = "us-east-2"
  # Amazon Deep Learning Containers (Hugging Face / PyTorch SageMaker images)
  dlc_account_id = "763104351884"
}

resource "aws_iam_role" "modernbert_sagemaker_execution" {
  name = local.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = local.role_name
    Project     = "mirrorview"
    Experiment  = "predict_keep_remove_2026_07_01"
    Component   = "modernbert"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "modernbert_sagemaker_execution" {
  name = local.role_name
  role = aws_iam_role.modernbert_sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ListBucketPrefix"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = "arn:aws:s3:::${local.s3_bucket}"
        Condition = {
          StringLike = {
            "s3:prefix" = [
              local.s3_prefix,
              "${local.s3_prefix}/*",
            ]
          }
        }
      },
      {
        Sid    = "S3ObjectReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload",
          "s3:ListMultipartUploadParts",
        ]
        Resource = "arn:aws:s3:::${local.s3_bucket}/${local.s3_prefix}/*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:GetLogEvents",
        ]
        Resource = [
          "arn:aws:logs:${local.aws_region}:*:log-group:/aws/sagemaker/*",
          "arn:aws:logs:${local.aws_region}:*:log-group:/aws/sagemaker/*:log-stream:*",
        ]
      },
      {
        Sid      = "ECRAuthorizationToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPullAmazonManagedTrainingImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        # Amazon-managed DLC / Hugging Face / PyTorch training containers
        Resource = [
          "arn:aws:ecr:${local.aws_region}:${local.dlc_account_id}:repository/*",
        ]
      },
      {
        Sid      = "CloudWatchMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "aws/sagemaker/TrainingJobs"
          }
        }
      },
    ]
  })
}

output "sagemaker_execution_role_arn" {
  description = "IAM role ARN for SageMaker ModernBERT training jobs"
  value       = aws_iam_role.modernbert_sagemaker_execution.arn
}

output "sagemaker_execution_role_name" {
  description = "IAM role name for SageMaker ModernBERT training jobs"
  value       = aws_iam_role.modernbert_sagemaker_execution.name
}
