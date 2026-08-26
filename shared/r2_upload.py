import os
import uuid

import boto3
from pydantic import BaseModel, ConfigDict


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    url: str
    key: str
    size: int


def upload_to_r2(
    data: bytes,
    *,
    prefix: str,
    extension: str,
    content_type: str,
    bucket: str | None = None,
) -> Artifact:
    bucket = bucket or os.environ.get("R2_BUCKET", "generated-media")
    endpoint = os.environ.get("R2_ENDPOINT")
    access_key = os.environ.get("R2_ACCESS_KEY")
    secret_key = os.environ.get("R2_SECRET_KEY")

    if not endpoint or not access_key or not secret_key:
        raise RuntimeError(
            "R2_ENDPOINT, R2_ACCESS_KEY, and R2_SECRET_KEY must all be set"
        )

    key = f"{prefix}_{uuid.uuid4()}.{extension}"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    url = f"{endpoint.rstrip('/')}/{bucket}/{key}"
    return Artifact(url=url, key=key, size=len(data))
