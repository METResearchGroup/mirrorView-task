"""Minimal DynamoDB client wrapper for embedding pointer rows."""

from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

_serializer = TypeSerializer()


def _serialize_row(item: dict[str, Any]) -> dict[str, Any]:
    return {k: _serializer.serialize(v) for k, v in item.items()}


def _deserialize_row(item: dict[str, Any]) -> dict[str, Any]:
    d = TypeDeserializer()
    return {k: d.deserialize(v) for k, v in item.items()}


class DynamoDBEmbeddingIndex:
    """Single-table accessor: partition key ``embedding_id`` (String)."""

    def __init__(self, table_name: str, *, region_name: str | None = None) -> None:
        kwargs: dict[str, Any] = {}
        if region_name is not None:
            kwargs["region_name"] = region_name
        self._table_name = table_name
        self._client: Any = boto3.client("dynamodb", **kwargs)

    @property
    def table_name(self) -> str:
        return self._table_name

    def ensure_table_exists(self, *, billing_mode: str = "PAY_PER_REQUEST") -> None:
        """Create the table if missing (on-demand billing by default).

        IAM once: dynamodb:CreateTable, DescribeTable, plus runtime GetItem/PutItem.
        """
        try:
            self._client.describe_table(TableName=self._table_name)
            return
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
                raise
        if billing_mode != "PAY_PER_REQUEST":
            raise ValueError(
                f"Only PAY_PER_REQUEST is implemented; got {billing_mode!r}"
            )
        self._client.create_table(
            TableName=self._table_name,
            BillingMode=billing_mode,
            KeySchema=[{"AttributeName": "embedding_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "embedding_id", "AttributeType": "S"},
            ],
        )
        waiter = self._client.get_waiter("table_exists")
        waiter.wait(TableName=self._table_name)

    def get_item(self, embedding_id: str) -> dict[str, Any] | None:
        resp = self._client.get_item(
            TableName=self._table_name,
            Key={"embedding_id": {"S": embedding_id}},
            ConsistentRead=True,
        )
        raw = resp.get("Item")
        if not raw:
            return None
        return _deserialize_row(raw)

    def put_item(self, item: dict[str, Any]) -> None:
        self._client.put_item(
            TableName=self._table_name,
            Item=_serialize_row(item),
        )
