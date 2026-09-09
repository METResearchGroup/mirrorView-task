"""Create jspsych-mirror-view-2026-09-09 and point save-data at it.

Do not run terraform apply in webapp/infra after this script. That apply would
set save-data BUCKET_NAME back to jspsych-mirror-view-4.

Assignment Lambda reads still need
https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17
applied in the other repo.

Run from the repo root:

    PYTHONPATH=. uv run python scripts/provision_jspsych_mirror_view_2026_09_09.py
"""

from __future__ import annotations

import json
import sys

import boto3
from botocore.exceptions import ClientError

AWS_REGION = "us-east-2"
BUCKET_NAME = "jspsych-mirror-view-2026-09-09"
SAVE_DATA_FUNCTION = "jspsych-scroll-save-data"
SAVE_DATA_ROLE_NAME = "jspsych-scroll-save-data-role"
SAVE_DATA_EXTRA_POLICY_NAME = "jspsych-mirror-view-2026-09-09-put-data"
DATA_PREFIX = "data/*"
INDEX_DOCUMENT = "index.html"
PUBLIC_GET_SID = "PublicReadGetObject"
POLICY_VERSION = "2012-10-17"
NOT_FOUND_STATUS = 404
BUCKET_ARN = f"arn:aws:s3:::{BUCKET_NAME}"
OBJECT_ARN = f"{BUCKET_ARN}/*"
DATA_ARN = f"{BUCKET_ARN}/{DATA_PREFIX}"
LOCATION_CONSTRAINT = {"LocationConstraint": AWS_REGION}
WEBSITE_CONFIG = {"IndexDocument": {"Suffix": INDEX_DOCUMENT}}
PUBLIC_ACCESS_BLOCK = {
    "BlockPublicAcls": False,
    "IgnorePublicAcls": False,
    "BlockPublicPolicy": False,
    "RestrictPublicBuckets": False,
}
PUBLIC_READ_POLICY = {
    "Version": POLICY_VERSION,
    "Statement": [
        {
            "Sid": PUBLIC_GET_SID,
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": OBJECT_ARN,
        }
    ],
}
SAVE_DATA_PUT_POLICY = {
    "Version": POLICY_VERSION,
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": DATA_ARN,
        }
    ],
}


def main() -> int:
    """Create the September study bucket and point save-data at it."""
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    iam_client = boto3.client("iam")
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    ensure_bucket(s3_client)
    configure_website(s3_client)
    save_data_bucket_name = point_save_data(iam_client, lambda_client)
    print(f"bucket={BUCKET_NAME}")
    print(f"save_data_bucket_name={save_data_bucket_name}")
    return 0


def ensure_bucket(s3_client) -> None:
    """Create the bucket in us-east-2 when it does not already exist."""
    if _bucket_exists(s3_client):
        return
    s3_client.create_bucket(
        Bucket=BUCKET_NAME, CreateBucketConfiguration=LOCATION_CONSTRAINT
    )


def configure_website(s3_client) -> None:
    """Turn on static website hosting and public object reads."""
    s3_client.put_bucket_website(Bucket=BUCKET_NAME, WebsiteConfiguration=WEBSITE_CONFIG)
    s3_client.put_public_access_block(
        Bucket=BUCKET_NAME, PublicAccessBlockConfiguration=PUBLIC_ACCESS_BLOCK
    )
    s3_client.put_bucket_policy(
        Bucket=BUCKET_NAME, Policy=json.dumps(PUBLIC_READ_POLICY)
    )


def point_save_data(iam_client, lambda_client) -> str:
    """Add a September PutObject policy and set save-data BUCKET_NAME."""
    iam_client.put_role_policy(
        RoleName=SAVE_DATA_ROLE_NAME,
        PolicyName=SAVE_DATA_EXTRA_POLICY_NAME,
        PolicyDocument=json.dumps(SAVE_DATA_PUT_POLICY),
    )
    return _update_save_data_bucket(lambda_client)


def _bucket_exists(s3_client) -> bool:
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except ClientError as error:
        if _status_code(error) == NOT_FOUND_STATUS:
            return False
        raise
    return True


def _update_save_data_bucket(lambda_client) -> str:
    current = lambda_client.get_function_configuration(FunctionName=SAVE_DATA_FUNCTION)
    variables = dict(current["Environment"]["Variables"])
    variables["BUCKET_NAME"] = BUCKET_NAME
    lambda_client.update_function_configuration(
        FunctionName=SAVE_DATA_FUNCTION, Environment={"Variables": variables}
    )
    return variables["BUCKET_NAME"]


def _status_code(error: ClientError) -> int:
    return int(error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))


if __name__ == "__main__":
    sys.exit(main())
