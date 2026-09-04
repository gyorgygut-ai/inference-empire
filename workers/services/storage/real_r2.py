import os

import boto3

from workers.services.storage.storage import Storage


class RealR2Storage(Storage):
    def __init__(self):
        endpoint = os.environ["R2_ENDPOINT"]
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        )
        self.bucket = os.environ.get("R2_BUCKET", "generated-media")

    def put(self, key, body):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)

    def presigned_url(self, key, expires=3600):
        return self.s3.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
        )

    def has(self, key):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    def fetch(self, key):
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def __reduce__(self):
        # Remote task args must stay JSON/pickle-safe (boto3 clients don't
        # serialize). Rebuild from the REMOTE env on unpickle — no secrets
        # cross the wire; the remote container carries them as secrets.
        return (RealR2Storage, ())


def require_storage(storage):
    """Live path: build RealR2Storage from the remote env when the caller
    passes None (remote task args must stay serializable, so live runners
    never ship a storage object). Local path: R2 env is absent, so the
    original ValueError stands — fake behavior unchanged."""
    if storage is not None:
        return storage
    if "R2_ENDPOINT" in os.environ:
        return RealR2Storage()
    raise ValueError("storage is required")
