# Bedrock path findings

The model is `us.amazon.nova-micro-v1:0`.

The region is `us-east-2`.

Credentials are the environment AWS keys. Copy `LAB_AWS_ACCESS_KEY_ID` onto `AWS_ACCESS_KEY_ID` when needed, and copy `LAB_AWS_ACCESS_KEY_SECRET` onto `AWS_SECRET_ACCESS_KEY` the same way.

No IAM service role was created.

## Converse

The probe text is "The Federal Reserve raised interest rates by 25 basis points today."


The model text is "news".

The input token count is 31.

The output token count is 2.

The stop reason is end_turn.

## Prices (US East Ohio, AWS Price List 2026-09-01)

- On-demand prices are $0.035 per million input tokens, and $0.14 per million output tokens.
- Batch prices are $0.0175 per million input tokens, and $0.07 per million output tokens.

## Native batch jobs

Listing jobs succeeded, and the listed job count was 0.

CreateModelInvocationJob failed when the role ARN was missing, which is the outcome we expected.

Error code: `AccessDeniedException`

Error message: User: arn:aws:iam::517478598677:user/mark_iam_credentials is not authorized to perform: iam:PassRole on resource: arn:aws:iam::517478598677:role/does-not-exist because no identity-based policy allows the iam:PassRole action

The labeling in this experiment uses Converse on-demand. Native batch jobs need the `iam:PassRole` permission and a Bedrock service role. This work must not create that role.
