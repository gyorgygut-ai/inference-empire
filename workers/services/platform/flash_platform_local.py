"""Flash local platform: fresh dict session over its own fake."""

from __future__ import annotations

from workers.mock_server.flash import fake as _fake


class LocalFlashPlatform:
    def deploy(self):
        _fake.clear()

    def undeploy(self):
        _fake.clear()
