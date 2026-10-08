class Artifacts:
    def put(self, key: str, body: bytes) -> None:
        raise NotImplementedError
    def presigned_url(self, key: str, expires: int = 3600) -> str:
        raise NotImplementedError
    def has(self, key: str) -> bool:
        raise NotImplementedError
    def fetch(self, key: str) -> bytes:
        raise NotImplementedError
