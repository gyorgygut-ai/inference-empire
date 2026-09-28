from packages.storage.storage import Storage


class FakeR2Storage(Storage):
    def __init__(self):
        self._store = {}

    def put(self, key, body):
        self._store[key] = body

    def presigned_url(self, key, expires=3600):
        return f"https://fake-bucket.r2.cloudflarestorage.com/{key}"

    def has(self, key):
        return key in self._store

    def fetch(self, key):
        return self._store[key]
