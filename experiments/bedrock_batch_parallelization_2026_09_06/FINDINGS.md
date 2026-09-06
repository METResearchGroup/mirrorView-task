# Bedrock path findings

Model: `us.amazon.nova-micro-v1:0`

Region: `us-east-2`

Credentials: environment AWS keys (`LAB_AWS_ACCESS_KEY_ID` copied onto `AWS_ACCESS_KEY_ID` when needed).

No IAM service role was created.

## Converse

Probe text: The Federal Reserve raised interest rates by 25 basis points today.

Model text: news

Input tokens: 31

Output tokens: 2

Stop reason: end_turn

## Prices (US East Ohio, AWS Price List 2026-09-01)

- On-demand. $0.035 per million input tokens, and $0.14 per million output tokens.
- Batch. $0.0175 per million input tokens, and $0.07 per million output tokens.

## Native batch jobs

List jobs succeeded: True. Listed job count: 0.

CreateModelInvocationJob with a missing role ARN failed as expected.

Error code: `AccessDeniedException`

Error message: User: arn:aws:iam::517478598677:user/mark_iam_credentials is not authorized to perform: iam:PassRole on resource: arn:aws:iam::517478598677:role/does-not-exist because no identity-based policy allows the iam:PassRole action

The live labeling path is Converse on-demand. Native batch jobs need `iam:PassRole` and a Bedrock service role, which this work must not create.
