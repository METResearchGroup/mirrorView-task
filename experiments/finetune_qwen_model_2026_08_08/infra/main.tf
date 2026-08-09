# SageMaker execution role for Qwen LoRA fine-tune (us-east-2).
# Scoped to s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/*
# and ECR repo mirrorview-finetune_qwen_model_2026_08_08.
#
# Apply (from this directory) after configuring AWS credentials with IAM write access:
#   terraform init && terraform apply

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
  role_name  = "mirrorview-qwen-finetune-sm-exec"
  s3_bucket  = "mirrorview-experimental-artifacts"
  s3_prefix  = "mirrorview-finetune_qwen_model_2026_08_08"
  ecr_repo   = "mirrorview-finetune_qwen_model_2026_08_08"
  aws_region = "us-east-2"
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "qwen_sagemaker_execution" {
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
    Name       = local.role_name
    Project    = "mirrorview"
    Experiment = "finetune_qwen_model_2026_08_08"
    ManagedBy  = "terraform"
  }
}

resource "aws_iam_role_policy" "qwen_sagemaker_execution" {
  name = local.role_name
  role = aws_iam_role.qwen_sagemaker_execution.id

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
        Sid    = "ECRPullCustomTrainingImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        Resource = [
          "arn:aws:ecr:${local.aws_region}:${local.account_id}:repository/${local.ecr_repo}",
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

# PassRole for the lab IAM user that launches jobs from Cloud Agent.
resource "aws_iam_user_policy" "mark_pass_qwen_sagemaker_role" {
  name = "pass-mirrorview-qwen-finetune-sm-exec"
  user = "mark_iam_credentials"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "PassQwenSageMakerExecutionRole"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = aws_iam_role.qwen_sagemaker_execution.arn
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "sagemaker.amazonaws.com"
          }
        }
      },
      {
        Sid    = "CreateSageMakerTrainingJobs"
        Effect = "Allow"
        Action = [
          "sagemaker:CreateTrainingJob",
          "sagemaker:DescribeTrainingJob",
          "sagemaker:StopTrainingJob",
          "sagemaker:ListTrainingJobs",
          "sagemaker:AddTags",
        ]
        Resource = "*"
      },
    ]
  })
}

output "sagemaker_execution_role_arn" {
  description = "IAM role ARN for Qwen SageMaker jobs; set SAGEMAKER_ROLE_ARN to this value."
  value       = aws_iam_role.qwen_sagemaker_execution.arn
}
