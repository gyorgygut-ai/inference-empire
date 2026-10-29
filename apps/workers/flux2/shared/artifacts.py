import os

import boto3
from botocore.config import Config


class Artifacts:
    def put(self, key, body):
        raise NotImplementedError
    def presigned_url(self, key, expires=3600):
        raise NotImplementedError
    def has(self, key):
        raise NotImplementedError
    def fetch(self, key):
        raise NotImplementedError

class R2Artifacts(Artifacts):
    def __init__(self):
        endpoint = os.environ["R2_ENDPOINT"]
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name="auto",
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
            config=Config(signature_version="s3v4"),
        )
        self.bucket = os.environ.get("R2_BUCKET", "generated-media")
    def put(self, key, body):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
    def presigned_url(self, key, expires=3600):
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires)
    def has(self, key):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False
    def fetch(self, key):
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()
    def __reduce__(self):
        return (R2Artifacts, ())
