terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-2"
}

variable "bucket_name" {
  description = "S3 bucket name for static hosting and data writes."
  type        = string
  default     = "jspsych-mirror-view-3"
}

variable "assignment_lambda_name" {
  description = "Downstream Lambda invoked by the get-post-assignments Lambda. Defaults to the function name used by study_participant_assignment_interface."
  type        = string
  default     = "get_study_assignment"
}

variable "tags" {
  description = "Optional tags applied to all managed resources."
  type        = map(string)
  default     = {}
}

locals {
  project                   = "jspsych-scroll"
  get_post_assignments_name = "jspsych-scroll-get-post-assignments"
  save_data_name            = "jspsych-scroll-save-data"
  api_name                  = "jspsych-scroll-api"
  lambda_runtime            = "nodejs20.x"

  common_tags = merge(
    {
      Project   = local.project
      ManagedBy = "Terraform"
    },
    var.tags
  )
}

data "archive_file" "get_post_assignments_zip" {
  type        = "zip"
  output_path = "${path.module}/get-post-assignments.zip"

  source {
    content  = file("${path.module}/../lambda-get-post-assignments.mjs")
    filename = "index.mjs"
  }
}

data "archive_file" "save_data_zip" {
  type        = "zip"
  output_path = "${path.module}/save-jspsych-data.zip"

  source {
    content  = file("${path.module}/../lambda-save-jspsych-data.mjs")
    filename = "index.mjs"
  }
}

resource "aws_s3_bucket" "site" {
  bucket = var.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_website_configuration" "site" {
  bucket = aws_s3_bucket.site.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket = aws_s3_bucket.site.id

  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "site_public_read" {
  statement {
    sid    = "PublicReadGetObject"
    effect = "Allow"

    actions = ["s3:GetObject"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = ["${aws_s3_bucket.site.arn}/*"]
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site_public_read.json

  depends_on = [aws_s3_bucket_public_access_block.site]
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "get_post_assignments" {
  name               = "${local.get_post_assignments_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role" "save_data" {
  name               = "${local.save_data_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "get_post_assignments_basic" {
  role       = aws_iam_role.get_post_assignments.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "save_data_basic" {
  role       = aws_iam_role.save_data.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "get_post_assignments_invoke" {
  statement {
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.assignment_lambda_name}",
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.assignment_lambda_name}:*"
    ]
  }
}

resource "aws_iam_role_policy" "get_post_assignments_invoke" {
  name   = "${local.get_post_assignments_name}-invoke-assignment"
  role   = aws_iam_role.get_post_assignments.id
  policy = data.aws_iam_policy_document.get_post_assignments_invoke.json
}

data "aws_iam_policy_document" "save_data_s3" {
  statement {
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${aws_s3_bucket.site.arn}/data/*"]
  }
}

resource "aws_iam_role_policy" "save_data_s3" {
  name   = "${local.save_data_name}-write-s3"
  role   = aws_iam_role.save_data.id
  policy = data.aws_iam_policy_document.save_data_s3.json
}

resource "aws_cloudwatch_log_group" "get_post_assignments" {
  name              = "/aws/lambda/${local.get_post_assignments_name}"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "save_data" {
  name              = "/aws/lambda/${local.save_data_name}"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_lambda_function" "get_post_assignments" {
  function_name = local.get_post_assignments_name
  role          = aws_iam_role.get_post_assignments.arn
  runtime       = local.lambda_runtime
  handler       = "index.handler"
  architectures = ["x86_64"]

  filename         = data.archive_file.get_post_assignments_zip.output_path
  source_code_hash = data.archive_file.get_post_assignments_zip.output_base64sha256

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      ASSIGNMENT_LAMBDA_NAME = var.assignment_lambda_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.get_post_assignments]
  tags       = local.common_tags
}

resource "aws_lambda_function" "save_data" {
  function_name = local.save_data_name
  role          = aws_iam_role.save_data.arn
  runtime       = local.lambda_runtime
  handler       = "index.handler"
  architectures = ["x86_64"]

  filename         = data.archive_file.save_data_zip.output_path
  source_code_hash = data.archive_file.save_data_zip.output_base64sha256

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }

  depends_on = [aws_cloudwatch_log_group.save_data]
  tags       = local.common_tags
}

resource "aws_apigatewayv2_api" "http" {
  name          = local.api_name
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_headers = ["*"]
    allow_methods = ["POST", "OPTIONS"]
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_integration" "get_post_assignments" {
  api_id = aws_apigatewayv2_api.http.id

  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_post_assignments.invoke_arn
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "save_data" {
  api_id = aws_apigatewayv2_api.http.id

  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.save_data.invoke_arn
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "get_post_assignments" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /get-post-assignments"
  target    = "integrations/${aws_apigatewayv2_integration.get_post_assignments.id}"
}

resource "aws_apigatewayv2_route" "save_data" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /save-jspsych-data"
  target    = "integrations/${aws_apigatewayv2_integration.save_data.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "prod"
  auto_deploy = true
  tags        = local.common_tags
}

resource "aws_lambda_permission" "allow_api_get_post_assignments" {
  statement_id  = "AllowExecutionFromHttpApiGetPostAssignments"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_post_assignments.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_api_save_data" {
  statement_id  = "AllowExecutionFromHttpApiSaveData"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.save_data.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

output "bucket_name" {
  value = aws_s3_bucket.site.bucket
}

output "website_endpoint" {
  value = aws_s3_bucket_website_configuration.site.website_endpoint
}

output "api_base_url" {
  value = "${aws_apigatewayv2_api.http.api_endpoint}/${aws_apigatewayv2_stage.prod.name}"
}

output "post_assignments_url" {
  value = "${aws_apigatewayv2_api.http.api_endpoint}/${aws_apigatewayv2_stage.prod.name}/get-post-assignments"
}

output "save_data_url" {
  value = "${aws_apigatewayv2_api.http.api_endpoint}/${aws_apigatewayv2_stage.prod.name}/save-jspsych-data"
}
