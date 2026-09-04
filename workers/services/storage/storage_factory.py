from workers.services.storage.fake_r2 import FakeR2Storage


def storage_factory(target):
    """Target-only storage factory. No `if target` anywhere else.

    Live returns None deliberately: remote workers rebuild RealR2Storage
    from the remote env via require_storage(None) (boto3 clients don't
    serialize), and eager construction here would demand R2_* env at
    collection time. _LiveProxy ignores storage entirely.
    """
    if target == "fake":
        return FakeR2Storage()
    if target == "live":
        return None
    raise ValueError(f"unknown target: {target!r}")
