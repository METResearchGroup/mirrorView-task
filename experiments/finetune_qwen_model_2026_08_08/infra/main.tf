# SageMaker IAM for Qwen LoRA fine-tune (us-east-2).
#
# Creates:
# 1) Execution role mirrorview-qwen-finetune-sm-exec (S3 + ECR + logs)
# 2) Inline user policy on mark_iam_credentials (PassRole + SageMaker APIs)
#
# Apply from this directory with credentials that can write IAM:
#   unset AWS_SESSION_TOKEN
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export AWS_DEFAULT_REGION=us-east-2
#   terraform init && terraform apply -auto-approve

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
  account_id = data.aws_caller_identity.current.account_id
  aws_region = "us-east-2"

  execution_role_name = "mirrorview-qwen-finetune-sm-exec"
  launcher_user_name  = "mark_iam_credentials"
  launcher_user_policy_name = "pass-mirrorview-qwen-finetune-sm-exec"

  s3_bucket = "mirrorview-experimental-artifacts"
  s3_prefixes = [
    "mirrorview-finetune_qwen_model_2026_08_08",
    "mirrorview-larger_finetune_qwen_model_2026_08_08",
  ]
  ecr_repos = [
    "mirrorview-finetune_qwen_model_2026_08_08",
    "mirrorview-larger_finetune_qwen_model_2026_08_08",
  ]

  # Also allow PassRole to the legacy ModernBERT role (optional reuse).
  modernbert_execution_role_arn = "arn:aws:iam::${local.account_id}:role/modernbert-sagemaker-execution"
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "qwen_sagemaker_execution" {
  name = local.execution_role_name

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
    Name       = local.execution_role_name
    Project    = "mirrorview"
    Experiment = "finetune_qwen_model_2026_08_08"
    ManagedBy  = "terraform"
  }
}

resource "aws_iam_role_policy" "qwen_sagemaker_execution" {
  name = local.execution_role_name
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
            "s3:prefix" = flatten([
              for prefix in local.s3_prefixes : [
                prefix,
                "${prefix}/*",
              ]
            ])
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
        Resource = [for prefix in local.s3_prefixes : "arn:aws:s3:::${local.s3_bucket}/${prefix}/*"]
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
          for repo in local.ecr_repos :
          "arn:aws:ecr:${local.aws_region}:${local.account_id}:repository/${repo}"
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

resource "aws_iam_user_policy" "mark_pass_qwen_sagemaker_role" {
  name = local.launcher_user_policy_name
  user = local.launcher_user_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PassSageMakerExecutionRoles"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.qwen_sagemaker_execution.arn,
          local.modernbert_execution_role_arn,
        ]
        Condition = {
          StringEquals = {
            "iam:PassedToService" = "sagemaker.amazonaws.com"
          }
        }
      },
      {
        Sid    = "SageMakerTrainingJobs"
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
  description = "Set SAGEMAKER_ROLE_ARN to this value for Qwen SageMaker jobs."
  value       = aws_iam_role.qwen_sagemaker_execution.arn
}

output "launcher_user_policy_name" {
  description = "Inline policy name attached to mark_iam_credentials."
  value       = local.launcher_user_policy_name
}
